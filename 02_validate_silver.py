import os
from pathlib import Path
import csv
import duckdb


# CONFIGURAÇÃO

PROJECT_DIR = Path(
    __file__
).resolve().parent

DEFAULT_DATA_ROOT = (
    PROJECT_DIR /
    "data"
)

PASTA_DADOS = Path(
    os.getenv(
        "PI_DATA_ROOT",
        str(DEFAULT_DATA_ROOT)
    )
).expanduser().resolve()

PASTA_BRONZE = PASTA_DADOS / "parquet"
PASTA_SILVER = PASTA_DADOS / "silver"

PASTA_METADATA = (
    PASTA_SILVER /
    "_metadata"
)

PASTA_METADATA.mkdir(
    parents=True,
    exist_ok=True
)

ANOS = [
    2022,
    2023,
    2024,
    2025
]

TABELAS = [
    "Viagem",
    "Trecho",
    "Passagem",
    "Pagamento"
]


# FUNÇÕES

def sql_path(path):
    return path.as_posix().replace(
        "'",
        "''"
    )


def salvar_csv(
    nome,
    cabecalho,
    linhas
):

    arquivo = (
        PASTA_METADATA /
        nome
    )

    with arquivo.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.writer(
            f,
            delimiter=";"
        )

        writer.writerow(
            cabecalho
        )

        writer.writerows(
            linhas
        )

    print(
        f"✓ {arquivo.name}"
    )


# 1. VALIDAÇÃO DE CONTAGEM

def validar_contagens(con):

    resultados = []

    problema = False

    for tabela in TABELAS:

        silver = (
            PASTA_SILVER /
            f"{tabela.lower()}.parquet"
        )

        for ano in ANOS:

            bronze = (
                PASTA_BRONZE /
                f"{ano}_{tabela}.parquet"
            )

            qtd_bronze = con.execute(
                f"""
                SELECT COUNT(*)
                FROM read_parquet(
                    '{sql_path(bronze)}'
                )
                """
            ).fetchone()[0]

            qtd_silver = con.execute(
                f"""
                SELECT COUNT(*)
                FROM read_parquet(
                    '{sql_path(silver)}'
                )
                WHERE ano_fonte = {ano}
                """
            ).fetchone()[0]

            diferenca = (
                qtd_silver -
                qtd_bronze
            )

            status = (
                "OK"
                if diferenca == 0
                else "ERRO"
            )

            if status == "ERRO":
                problema = True

            resultados.append([
                ano,
                tabela,
                qtd_bronze,
                qtd_silver,
                diferenca,
                status
            ])

    salvar_csv(
        "02_validacao_contagens.csv",
        [
            "ano",
            "tabela",
            "registros_bronze",
            "registros_silver",
            "diferenca",
            "status"
        ],
        resultados
    )

    return not problema


# 2. CHAVES

def validar_chaves(con):

    resultados = []

    problema = False

    for tabela in TABELAS:

        arquivo = (
            PASTA_SILVER /
            f"{tabela.lower()}.parquet"
        )

        dados = con.execute(
            f"""
            SELECT
                ano_fonte,

                COUNT(*) AS registros,

                COUNT(*) FILTER (
                    WHERE sk_processo IS NULL
                )
                    AS sk_processo_nula,

                COUNT(*) FILTER (
                    WHERE sk_registro IS NULL
                )
                    AS sk_registro_nula,

                COUNT(DISTINCT sk_registro)
                    AS sk_registro_distintas

            FROM read_parquet(
                '{sql_path(arquivo)}'
            )

            GROUP BY ano_fonte
            ORDER BY ano_fonte
            """
        ).fetchall()

        for linha in dados:

            ano = linha[0]
            total = linha[1]
            proc_null = linha[2]
            registro_null = linha[3]
            distintas = linha[4]

            unica = (
                distintas == total
            )

            status = (
                "OK"
                if (
                    proc_null == 0
                    and registro_null == 0
                    and unica
                )
                else "ERRO"
            )

            if status == "ERRO":
                problema = True

            resultados.append([
                ano,
                tabela,
                total,
                proc_null,
                registro_null,
                distintas,
                status
            ])

    salvar_csv(
        "03_validacao_chaves.csv",
        [
            "ano",
            "tabela",
            "registros",
            "sk_processo_nulas",
            "sk_registro_nulas",
            "sk_registro_distintas",
            "status"
        ],
        resultados
    )

    return not problema


# 3. ERROS DE PARSE

def validar_parses(con):

    resultados = []

    for tabela in TABELAS:

        arquivo = (
            PASTA_SILVER /
            f"{tabela.lower()}.parquet"
        )

        schema = con.execute(
            f"""
            DESCRIBE
            SELECT *
            FROM read_parquet(
                '{sql_path(arquivo)}'
            )
            """
        ).fetchall()

        colunas_erro = [
            linha[0]
            for linha in schema
            if linha[0].startswith(
                "erro_parse_"
            )
        ]

        for coluna in colunas_erro:

            dados = con.execute(
                f"""
                SELECT
                    ano_fonte,

                    SUM(
                        CASE
                            WHEN "{coluna}"
                            THEN 1
                            ELSE 0
                        END
                    ) AS erros

                FROM read_parquet(
                    '{sql_path(arquivo)}'
                )

                GROUP BY ano_fonte
                ORDER BY ano_fonte
                """
            ).fetchall()

            for ano, erros in dados:

                resultados.append([
                    ano,
                    tabela,
                    coluna,
                    erros
                ])

    salvar_csv(
        "04_erros_parse.csv",
        [
            "ano",
            "tabela",
            "campo_validacao",
            "quantidade_erros"
        ],
        resultados
    )


# 4. MULTIPLICIDADE

def validar_multiplicidade(con):

    resultados = []

    for tabela in TABELAS:

        arquivo = (
            PASTA_SILVER /
            f"{tabela.lower()}.parquet"
        )

        dados = con.execute(
            f"""
            SELECT
                ano_fonte,

                COUNT(*) AS registros,

                COUNT(
                    DISTINCT hash_observacao
                )
                    AS observacoes_distintas,

                COUNT(*) -
                COUNT(
                    DISTINCT hash_observacao
                )
                    AS repeticoes_exatas

            FROM read_parquet(
                '{sql_path(arquivo)}'
            )

            GROUP BY ano_fonte
            ORDER BY ano_fonte
            """
        ).fetchall()

        for linha in dados:

            resultados.append([
                tabela,
                linha[0],
                linha[1],
                linha[2],
                linha[3]
            ])

    salvar_csv(
        "05_multiplicidade_silver.csv",
        [
            "tabela",
            "ano",
            "registros",
            "observacoes_distintas",
            "repeticoes_exatas"
        ],
        resultados
    )


# 5. CATEGORIAS

def gerar_perfil_categorias(con):

    consultas = [
        (
            "Pagamento",
            "tipo_pagamento_normalizado"
        ),
        (
            "Passagem",
            "meio_transporte_normalizado"
        ),
        (
            "Trecho",
            "meio_transporte_normalizado"
        ),
        (
            "Viagem",
            "situacao_normalizada"
        )
    ]

    resultados = []

    for tabela, coluna in consultas:

        arquivo = (
            PASTA_SILVER /
            f"{tabela.lower()}.parquet"
        )

        dados = con.execute(
            f"""
            SELECT
                ano_fonte,
                "{coluna}",
                COUNT(*)

            FROM read_parquet(
                '{sql_path(arquivo)}'
            )

            GROUP BY
                ano_fonte,
                "{coluna}"

            ORDER BY
                ano_fonte,
                COUNT(*) DESC
            """
        ).fetchall()

        for ano, categoria, quantidade in dados:

            resultados.append([
                tabela,
                ano,
                coluna,
                categoria,
                quantidade
            ])

    salvar_csv(
        "06_categorias_silver.csv",
        [
            "tabela",
            "ano",
            "campo",
            "categoria",
            "quantidade"
        ],
        resultados
    )


# 6. CONTROLE FINANCEIRO

def validar_financeiro(con):

    pagamento = (
        PASTA_SILVER /
        "pagamento.parquet"
    )

    passagem = (
        PASTA_SILVER /
        "passagem.parquet"
    )

    viagem = (
        PASTA_SILVER /
        "viagem.parquet"
    )

    resultados = []


    # PAGAMENTO

    dados = con.execute(
        f"""
        SELECT
            ano_fonte,
            tipo_pagamento_normalizado,
            SUM(valor)

        FROM read_parquet(
            '{sql_path(pagamento)}'
        )

        GROUP BY
            ano_fonte,
            tipo_pagamento_normalizado

        ORDER BY
            ano_fonte,
            tipo_pagamento_normalizado
        """
    ).fetchall()

    for ano, tipo, valor in dados:

        resultados.append([
            ano,
            "Pagamento",
            tipo,
            valor
        ])


    # PASSAGEM

    dados = con.execute(
        f"""
        SELECT
            ano_fonte,

            SUM(valor_passagem)
                AS tarifa,

            SUM(taxa_servico)
                AS taxa,

            SUM(custo_total_passagem)
                AS total

        FROM read_parquet(
            '{sql_path(passagem)}'
        )

        GROUP BY ano_fonte
        ORDER BY ano_fonte
        """
    ).fetchall()

    for ano, tarifa, taxa, total in dados:

        resultados.extend([
            [
                ano,
                "Passagem",
                "VALOR_PASSAGEM",
                tarifa
            ],
            [
                ano,
                "Passagem",
                "TAXA_SERVICO",
                taxa
            ],
            [
                ano,
                "Passagem",
                "CUSTO_TOTAL_PASSAGEM",
                total
            ]
        ])


    # VIAGEM

    dados = con.execute(
        f"""
        SELECT
            ano_fonte,
            SUM(valor_diarias),
            SUM(valor_passagens),
            SUM(valor_devolucao),
            SUM(valor_outros_gastos)

        FROM read_parquet(
            '{sql_path(viagem)}'
        )

        GROUP BY ano_fonte
        ORDER BY ano_fonte
        """
    ).fetchall()

    for (
        ano,
        diarias,
        passagens,
        devolucao,
        outros
    ) in dados:

        resultados.extend([
            [
                ano,
                "Viagem",
                "VALOR_DIARIAS",
                diarias
            ],
            [
                ano,
                "Viagem",
                "VALOR_PASSAGENS",
                passagens
            ],
            [
                ano,
                "Viagem",
                "VALOR_DEVOLUCAO",
                devolucao
            ],
            [
                ano,
                "Viagem",
                "VALOR_OUTROS_GASTOS",
                outros
            ]
        ])

    salvar_csv(
        "07_totais_financeiros_silver.csv",
        [
            "ano",
            "fonte",
            "metrica",
            "valor"
        ],
        resultados
    )


# EXECUÇÃO

def main():

    con = duckdb.connect()

    try:

        print("\n[1/6] Validando contagens...")
        contagens_ok = validar_contagens(
            con
        )

        print("\n[2/6] Validando chaves...")
        chaves_ok = validar_chaves(
            con
        )

        print("\n[3/6] Validando parse...")
        validar_parses(
            con
        )

        print("\n[4/6] Validando multiplicidade...")
        validar_multiplicidade(
            con
        )

        print("\n[5/6] Perfilando categorias...")
        gerar_perfil_categorias(
            con
        )

        print("\n[6/6] Auditando totais financeiros...")
        validar_financeiro(
            con
        )

        print("\n" + "=" * 70)

        if (
            contagens_ok
            and chaves_ok
        ):

            print(
                "VALIDAÇÃO ESTRUTURAL DA SILVER: OK"
            )

        else:

            print(
                "ATENÇÃO: FORAM ENCONTRADOS "
                "PROBLEMAS ESTRUTURAIS"
            )

        print("=" * 70)

        print(
            "\nRelatórios disponíveis em:"
        )

        print(
            PASTA_METADATA
        )

    finally:
        con.close()


if __name__ == "__main__":
    main()