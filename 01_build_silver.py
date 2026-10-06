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
PASTA_METADATA = PASTA_SILVER / "_metadata"

PASTA_SILVER.mkdir(parents=True, exist_ok=True)
PASTA_METADATA.mkdir(parents=True, exist_ok=True)

ANOS = [2022, 2023, 2024, 2025]


# SCHEMAS

SCHEMAS = {
    "Viagem": [
        "Identificador do processo de viagem",
        "Número da Proposta (PCDP)",
        "Situação",
        "Viagem Urgente",
        "Justificativa Urgência Viagem",
        "Código do órgão superior",
        "Nome do órgão superior",
        "Código órgão solicitante",
        "Nome órgão solicitante",
        "CPF viajante",
        "Nome",
        "Cargo",
        "Função",
        "Descrição Função",
        "Período - Data de início",
        "Período - Data de fim",
        "Destinos",
        "Motivo",
        "Valor diárias",
        "Valor passagens",
        "Valor devolução",
        "Valor outros gastos",
    ],

    "Trecho": [
        "Identificador do processo de viagem",
        "Número da Proposta (PCDP)",
        "Sequência Trecho",
        "Origem - Data",
        "Origem - País",
        "Origem - UF",
        "Origem - Cidade",
        "Destino - Data",
        "Destino - País",
        "Destino - UF",
        "Destino - Cidade",
        "Meio de transporte",
        "Número Diárias",
        "Missao?",
    ],

    "Passagem": [
        "Identificador do processo de viagem",
        "Número da Proposta (PCDP)",
        "Meio de transporte",
        "País - Origem ida",
        "UF - Origem ida",
        "Cidade - Origem ida",
        "País - Destino ida",
        "UF - Destino ida",
        "Cidade - Destino ida",
        "País - Origem volta",
        "UF - Origem volta",
        "Cidade - Origem volta",
        "Pais - Destino volta",
        "UF - Destino volta",
        "Cidade - Destino volta",
        "Valor da passagem",
        "Taxa de serviço",
        "Data da emissão/compra",
        "Hora da emissão/compra",
    ],

    "Pagamento": [
        "Identificador do processo de viagem",
        "Número da Proposta (PCDP)",
        "Código do órgão superior",
        "Nome do órgão superior",
        "Codigo do órgão pagador",
        "Nome do órgao pagador",
        "Código da unidade gestora pagadora",
        "Nome da unidade gestora pagadora",
        "Tipo de pagamento",
        "Valor",
    ],
}


# FUNÇÕES SQL AUXILIARES

def qi(nome):
    return '"' + nome.replace('"', '""') + '"'


def sql_path(path):
    return path.as_posix().replace("'", "''")


def txt(nome):
    coluna = qi(nome)

    return f"""
        NULLIF(TRIM(CAST({coluna} AS VARCHAR)), '')
    """.strip()


def status_texto(nome):
    valor = txt(nome)

    return f"""
        CASE
            WHEN {valor} IS NULL
                THEN 'AUSENTE'

            WHEN UPPER({valor}) LIKE 'SEM INFORMA%'
                THEN 'NAO_INFORMADO'

            WHEN UPPER({valor}) IN ('SIGILOSO', 'SIGILOSA')
                THEN 'SIGILOSO'

            WHEN {valor} IN ('-1', '-11')
                THEN 'CODIGO_ESPECIAL_FONTE'

            ELSE 'INFORMADO'
        END
    """.strip()


def decimal_br(nome, precisao="18,2"):

    valor = txt(nome)

    return f"""
        CASE
            WHEN {valor} IS NULL THEN NULL

            WHEN POSITION(',' IN {valor}) > 0 THEN
                TRY_CAST(
                    REPLACE(
                        REPLACE({valor}, '.', ''),
                        ',',
                        '.'
                    )
                    AS DECIMAL({precisao})
                )

            ELSE
                TRY_CAST(
                    {valor}
                    AS DECIMAL({precisao})
                )
        END
    """.strip()


def inteiro(nome):
    valor = txt(nome)

    return f"""
        TRY_CAST({valor} AS INTEGER)
    """.strip()


def data_br(nome):
    valor = txt(nome)

    return f"""
        COALESCE(
            TRY_CAST({valor} AS DATE),

            CAST(
                TRY_STRPTIME(
                    {valor},
                    '%d/%m/%Y'
                )
                AS DATE
            ),

            CAST(
                TRY_STRPTIME(
                    {valor},
                    '%d/%m/%Y %H:%M:%S'
                )
                AS DATE
            )
        )
    """.strip()


def hora(nome):
    valor = txt(nome)

    return f"""
        COALESCE(
            TRY_CAST({valor} AS TIME),

            CAST(
                TRY_STRPTIME(
                    {valor},
                    '%H:%M'
                )
                AS TIME
            ),

            CAST(
                TRY_STRPTIME(
                    {valor},
                    '%H:%M:%S'
                )
                AS TIME
            )
        )
    """.strip()


def booleano_sim_nao(nome):
    valor = txt(nome)

    return f"""
        CASE
            WHEN UPPER({valor}) IN (
                'SIM',
                'S',
                'TRUE',
                '1'
            )
                THEN TRUE

            WHEN UPPER({valor}) IN (
                'NÃO',
                'NAO',
                'N',
                'FALSE',
                '0'
            )
                THEN FALSE

            ELSE NULL
        END
    """.strip()


def erro_parse(nome, expressao_convertida):

    return f"""
        CASE
            WHEN {status_texto(nome)} = 'INFORMADO'
             AND ({expressao_convertida}) IS NULL
                THEN TRUE

            ELSE FALSE
        END
    """.strip()


def hash_observacao(colunas):

    partes = [
        "CAST(ano_fonte AS VARCHAR)"
    ]

    for coluna in colunas:
        partes.append(
            f"COALESCE(CAST({qi(coluna)} AS VARCHAR), '<NULL>')"
        )

    concatenado = " || '¦' || ".join(partes)

    return f"MD5({concatenado})"


# NORMALIZAÇÕES DE CATEGORIAS

def tipo_pagamento_normalizado():
    c = txt("Tipo de pagamento")

    return f"""
        CASE
            WHEN UPPER({c}) IN (
                'DIÁRIAS',
                'DIARIAS'
            )
                THEN 'DIARIAS'

            WHEN UPPER({c}) = 'PASSAGEM'
                THEN 'PASSAGEM'

            WHEN UPPER({c}) IN (
                'RESTITUIÇÃO',
                'RESTITUICAO'
            )
                THEN 'RESTITUICAO'

            WHEN UPPER({c}) LIKE '%SEGURO%'
                THEN 'SEGURO'

            ELSE UPPER({c})
        END
    """.strip()


def categoria_normalizada(nome):
    return f"UPPER({txt(nome)})"


# VALIDAÇÃO DO SCHEMA

def validar_schema(con, arquivo, esperado):

    descricao = con.execute(
        f"""
        DESCRIBE
        SELECT *
        FROM read_parquet(
            '{sql_path(arquivo)}'
        )
        """
    ).fetchall()

    encontrado = [
        linha[0]
        for linha in descricao
    ]

    if encontrado != esperado:

        print("\nERRO DE SCHEMA")
        print(f"Arquivo: {arquivo.name}")

        print("\nEsperado:")
        for x in esperado:
            print("  ", x)

        print("\nEncontrado:")
        for x in encontrado:
            print("  ", x)

        raise RuntimeError(
            f"Schema incompatível em {arquivo.name}"
        )


# UNION DOS QUATRO ANOS

def gerar_union(con, tabela):

    partes = []

    for ano in ANOS:

        arquivo = (
            PASTA_BRONZE /
            f"{ano}_{tabela}.parquet"
        )

        if not arquivo.exists():
            raise FileNotFoundError(
                f"Arquivo não encontrado: {arquivo}"
            )

        validar_schema(
            con,
            arquivo,
            SCHEMAS[tabela]
        )

        partes.append(
            f"""
            SELECT
                CAST({ano} AS SMALLINT)
                    AS ano_fonte,

                '{arquivo.name}'
                    AS arquivo_origem,

                ROW_NUMBER() OVER ()
                    AS ordem_registro_arquivo,

                *
            FROM read_parquet(
                '{sql_path(arquivo)}'
            )
            """
        )

    return "\nUNION ALL\n".join(partes)


# SELECTS SILVER

def select_viagem():

    data_inicio = data_br(
        "Período - Data de início"
    )

    data_fim = data_br(
        "Período - Data de fim"
    )

    valor_diarias = decimal_br(
        "Valor diárias"
    )

    valor_passagens = decimal_br(
        "Valor passagens"
    )

    valor_devolucao = decimal_br(
        "Valor devolução"
    )

    valor_outros = decimal_br(
        "Valor outros gastos"
    )

    return f"""
        {txt("Identificador do processo de viagem")}
            AS identificador_processo_viagem,

        {txt("Número da Proposta (PCDP)")}
            AS numero_pcdp,

        {txt("Situação")}
            AS situacao_original,

        {categoria_normalizada("Situação")}
            AS situacao_normalizada,

        {txt("Viagem Urgente")}
            AS viagem_urgente_original,

        {booleano_sim_nao("Viagem Urgente")}
            AS viagem_urgente_flag,

        {txt("Justificativa Urgência Viagem")}
            AS justificativa_urgencia,

        {status_texto("Justificativa Urgência Viagem")}
            AS status_justificativa_urgencia,

        {txt("Código do órgão superior")}
            AS codigo_orgao_superior,

        {txt("Nome do órgão superior")}
            AS nome_orgao_superior,

        {txt("Código órgão solicitante")}
            AS codigo_orgao_solicitante,

        {txt("Nome órgão solicitante")}
            AS nome_orgao_solicitante,

        {txt("CPF viajante")}
            AS cpf_viajante,

        {status_texto("CPF viajante")}
            AS status_cpf_viajante,

        CASE
            WHEN {status_texto("CPF viajante")}
                = 'INFORMADO'
            THEN MD5({txt("CPF viajante")})
            ELSE NULL
        END
            AS id_viajante_hash,

        {txt("Nome")}
            AS nome_viajante,

        {txt("Cargo")}
            AS cargo,

        {status_texto("Cargo")}
            AS status_cargo,

        {txt("Função")}
            AS funcao,

        {txt("Descrição Função")}
            AS descricao_funcao,

        {txt("Período - Data de início")}
            AS data_inicio_raw,

        {data_inicio}
            AS data_inicio,

        {erro_parse("Período - Data de início", data_inicio)}
            AS erro_parse_data_inicio,

        {txt("Período - Data de fim")}
            AS data_fim_raw,

        {data_fim}
            AS data_fim,

        {erro_parse("Período - Data de fim", data_fim)}
            AS erro_parse_data_fim,

        {txt("Destinos")}
            AS destinos,

        {txt("Motivo")}
            AS motivo,

        {txt("Valor diárias")}
            AS valor_diarias_raw,

        {valor_diarias}
            AS valor_diarias,

        {erro_parse("Valor diárias", valor_diarias)}
            AS erro_parse_valor_diarias,

        {txt("Valor passagens")}
            AS valor_passagens_raw,

        {valor_passagens}
            AS valor_passagens,

        {erro_parse("Valor passagens", valor_passagens)}
            AS erro_parse_valor_passagens,

        {txt("Valor devolução")}
            AS valor_devolucao_raw,

        {valor_devolucao}
            AS valor_devolucao,

        {erro_parse("Valor devolução", valor_devolucao)}
            AS erro_parse_valor_devolucao,

        {txt("Valor outros gastos")}
            AS valor_outros_gastos_raw,

        {valor_outros}
            AS valor_outros_gastos,

        {erro_parse("Valor outros gastos", valor_outros)}
            AS erro_parse_valor_outros_gastos
    """


def select_trecho():

    sequencia = inteiro(
        "Sequência Trecho"
    )

    data_origem = data_br(
        "Origem - Data"
    )

    data_destino = data_br(
        "Destino - Data"
    )

    numero_diarias = decimal_br(
        "Número Diárias",
        "12,2"
    )

    return f"""
        {txt("Identificador do processo de viagem")}
            AS identificador_processo_viagem,

        {txt("Número da Proposta (PCDP)")}
            AS numero_pcdp,

        {txt("Sequência Trecho")}
            AS sequencia_trecho_raw,

        {sequencia}
            AS sequencia_trecho,

        {erro_parse("Sequência Trecho", sequencia)}
            AS erro_parse_sequencia_trecho,

        {txt("Origem - Data")}
            AS data_origem_raw,

        {data_origem}
            AS data_origem,

        {erro_parse("Origem - Data", data_origem)}
            AS erro_parse_data_origem,

        {txt("Origem - País")}
            AS pais_origem,

        {txt("Origem - UF")}
            AS uf_origem,

        {txt("Origem - Cidade")}
            AS cidade_origem,

        {txt("Destino - Data")}
            AS data_destino_raw,

        {data_destino}
            AS data_destino,

        {erro_parse("Destino - Data", data_destino)}
            AS erro_parse_data_destino,

        {txt("Destino - País")}
            AS pais_destino,

        {txt("Destino - UF")}
            AS uf_destino,

        {txt("Destino - Cidade")}
            AS cidade_destino,

        {txt("Meio de transporte")}
            AS meio_transporte_original,

        {categoria_normalizada("Meio de transporte")}
            AS meio_transporte_normalizado,

        {txt("Número Diárias")}
            AS numero_diarias_raw,

        {numero_diarias}
            AS numero_diarias,

        {erro_parse("Número Diárias", numero_diarias)}
            AS erro_parse_numero_diarias,

        {txt("Missao?")}
            AS missao_original,

        {booleano_sim_nao("Missao?")}
            AS missao_flag
    """


def select_passagem():

    valor_passagem = decimal_br(
        "Valor da passagem"
    )

    taxa_servico = decimal_br(
        "Taxa de serviço"
    )

    data_emissao = data_br(
        "Data da emissão/compra"
    )

    hora_emissao = hora(
        "Hora da emissão/compra"
    )

    return f"""
        {txt("Identificador do processo de viagem")}
            AS identificador_processo_viagem,

        {txt("Número da Proposta (PCDP)")}
            AS numero_pcdp,

        {txt("Meio de transporte")}
            AS meio_transporte_original,

        {categoria_normalizada("Meio de transporte")}
            AS meio_transporte_normalizado,

        {txt("País - Origem ida")}
            AS pais_origem_ida,

        {txt("UF - Origem ida")}
            AS uf_origem_ida,

        {txt("Cidade - Origem ida")}
            AS cidade_origem_ida,

        {txt("País - Destino ida")}
            AS pais_destino_ida,

        {txt("UF - Destino ida")}
            AS uf_destino_ida,

        {txt("Cidade - Destino ida")}
            AS cidade_destino_ida,

        {txt("País - Origem volta")}
            AS pais_origem_volta,

        {txt("UF - Origem volta")}
            AS uf_origem_volta,

        {txt("Cidade - Origem volta")}
            AS cidade_origem_volta,

        {txt("Pais - Destino volta")}
            AS pais_destino_volta,

        {txt("UF - Destino volta")}
            AS uf_destino_volta,

        {txt("Cidade - Destino volta")}
            AS cidade_destino_volta,

        {txt("Valor da passagem")}
            AS valor_passagem_raw,

        {valor_passagem}
            AS valor_passagem,

        {erro_parse("Valor da passagem", valor_passagem)}
            AS erro_parse_valor_passagem,

        {txt("Taxa de serviço")}
            AS taxa_servico_raw,

        {taxa_servico}
            AS taxa_servico,

        {erro_parse("Taxa de serviço", taxa_servico)}
            AS erro_parse_taxa_servico,

        (
            COALESCE({valor_passagem}, 0)
            +
            COALESCE({taxa_servico}, 0)
        )
            AS custo_total_passagem,

        {txt("Data da emissão/compra")}
            AS data_emissao_raw,

        {data_emissao}
            AS data_emissao,

        {erro_parse("Data da emissão/compra", data_emissao)}
            AS erro_parse_data_emissao,

        {txt("Hora da emissão/compra")}
            AS hora_emissao_raw,

        {hora_emissao}
            AS hora_emissao,

        {erro_parse("Hora da emissão/compra", hora_emissao)}
            AS erro_parse_hora_emissao
    """


def select_pagamento():

    valor = decimal_br(
        "Valor"
    )

    return f"""
        {txt("Identificador do processo de viagem")}
            AS identificador_processo_viagem,

        {txt("Número da Proposta (PCDP)")}
            AS numero_pcdp,

        {txt("Código do órgão superior")}
            AS codigo_orgao_superior,

        {txt("Nome do órgão superior")}
            AS nome_orgao_superior,

        {txt("Codigo do órgão pagador")}
            AS codigo_orgao_pagador,

        {txt("Nome do órgao pagador")}
            AS nome_orgao_pagador,

        {txt("Código da unidade gestora pagadora")}
            AS codigo_unidade_gestora_pagadora,

        {txt("Nome da unidade gestora pagadora")}
            AS nome_unidade_gestora_pagadora,

        {txt("Tipo de pagamento")}
            AS tipo_pagamento_original,

        {tipo_pagamento_normalizado()}
            AS tipo_pagamento_normalizado,

        {txt("Valor")}
            AS valor_raw,

        {valor}
            AS valor,

        {erro_parse("Valor", valor)}
            AS erro_parse_valor
    """


# CONSTRUÇÃO SILVER

def construir_tabela(
    con,
    tabela,
    select_transformacao
):

    print("\n" + "=" * 70)
    print(f"Construindo Silver: {tabela}")
    print("=" * 70)

    union_sql = gerar_union(
        con,
        tabela
    )

    hash_sql = hash_observacao(
        SCHEMAS[tabela]
    )

    destino = (
        PASTA_SILVER /
        f"{tabela.lower()}.parquet"
    )

    if destino.exists():
        destino.unlink()

    sql = f"""
        COPY (

            WITH fonte AS (

                {union_sql}

            ),

            transformado AS (

                SELECT
                    ano_fonte,
                    arquivo_origem,
                    ordem_registro_arquivo,

                    MD5(
                        CAST(ano_fonte AS VARCHAR)
                        || '|'
                        || COALESCE(
                            TRIM(
                                CAST(
                                    "Identificador do processo de viagem"
                                    AS VARCHAR
                                )
                            ),
                            ''
                        )
                    )
                        AS sk_processo,

                    {hash_sql}
                        AS hash_observacao,

                    {select_transformacao}

                FROM fonte
            ),

            numerado AS (

                SELECT
                    *,

                    ROW_NUMBER() OVER (
                        PARTITION BY
                            ano_fonte,
                            hash_observacao

                        ORDER BY
                            ordem_registro_arquivo
                    )
                        AS ordinal_ocorrencia

                FROM transformado
            )

            SELECT

                MD5(
                    LOWER('{tabela}')
                    || '|'
                    || CAST(ano_fonte AS VARCHAR)
                    || '|'
                    || hash_observacao
                    || '|'
                    || CAST(
                        ordinal_ocorrencia
                        AS VARCHAR
                    )
                )
                    AS sk_registro,

                *

            FROM numerado

        )

        TO '{sql_path(destino)}'

        (
            FORMAT PARQUET,
            COMPRESSION ZSTD
        );
    """

    con.execute(sql)

    total = con.execute(
        f"""
        SELECT COUNT(*)
        FROM read_parquet(
            '{sql_path(destino)}'
        )
        """
    ).fetchone()[0]

    print(
        f"✓ {destino.name}: "
        f"{total:,} registros"
    )

    return total


# MANIFESTO DA SILVER

def gerar_manifesto(con):

    linhas = []

    for tabela in [
        "viagem",
        "trecho",
        "passagem",
        "pagamento"
    ]:

        arquivo = (
            PASTA_SILVER /
            f"{tabela}.parquet"
        )

        resultado = con.execute(
            f"""
            SELECT
                ano_fonte,
                COUNT(*) AS registros,
                COUNT(DISTINCT sk_processo)
                    AS processos,
                COUNT(DISTINCT sk_registro)
                    AS registros_tecnicos

            FROM read_parquet(
                '{sql_path(arquivo)}'
            )

            GROUP BY ano_fonte
            ORDER BY ano_fonte
            """
        ).fetchall()

        for linha in resultado:

            linhas.append([
                tabela,
                linha[0],
                linha[1],
                linha[2],
                linha[3]
            ])

    destino = (
        PASTA_METADATA /
        "01_manifesto_silver.csv"
    )

    with destino.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.writer(
            f,
            delimiter=";"
        )

        writer.writerow([
            "tabela",
            "ano",
            "registros",
            "processos_distintos",
            "sk_registro_distintas"
        ])

        writer.writerows(linhas)

    print(
        f"\n✓ Manifesto criado: {destino}"
    )


# EXECUÇÃO

def main():

    con = duckdb.connect()

    try:

        construir_tabela(
            con,
            "Viagem",
            select_viagem()
        )

        construir_tabela(
            con,
            "Trecho",
            select_trecho()
        )

        construir_tabela(
            con,
            "Passagem",
            select_passagem()
        )

        construir_tabela(
            con,
            "Pagamento",
            select_pagamento()
        )

        gerar_manifesto(con)

        print("\n" + "=" * 70)
        print("CAMADA SILVER CONSTRUÍDA COM SUCESSO")
        print("=" * 70)

        print("\nArquivos gerados:")

        print(
            PASTA_SILVER /
            "viagem.parquet"
        )

        print(
            PASTA_SILVER /
            "trecho.parquet"
        )

        print(
            PASTA_SILVER /
            "passagem.parquet"
        )

        print(
            PASTA_SILVER /
            "pagamento.parquet"
        )

    finally:
        con.close()


if __name__ == "__main__":
    main()