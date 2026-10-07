import os
import tempfile
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

PASTA_SILVER = PASTA_DADOS / "silver"
PASTA_GOLD = PASTA_DADOS / "gold"
PASTA_METADATA = PASTA_GOLD / "_metadata"

DUCKDB_THREADS = max(
    1,
    int(
        os.getenv(
            "PI_DUCKDB_THREADS",
            "1"
        )
    )
)

DUCKDB_MEMORY_LIMIT = os.getenv(
    "PI_DUCKDB_MEMORY_LIMIT",
    "4GB"
)

DEFAULT_DUCKDB_TEMP_DIR = (
    Path(tempfile.gettempdir()) /
    "inteligencia_analitica_viagens_duckdb"
)

PASTA_TEMP = Path(
    os.getenv(
        "PI_DUCKDB_TEMP_DIR",
        str(DEFAULT_DUCKDB_TEMP_DIR)
    )
).expanduser().resolve()

PASTA_METADATA.mkdir(
    parents=True,
    exist_ok=True
)

PASTA_TEMP.mkdir(
    parents=True,
    exist_ok=True
)

VIAGEM_S = PASTA_SILVER / "viagem.parquet"
TRECHO_S = PASTA_SILVER / "trecho.parquet"
PASSAGEM_S = PASTA_SILVER / "passagem.parquet"
PAGAMENTO_S = PASTA_SILVER / "pagamento.parquet"

DIM_PROCESSO = PASTA_GOLD / "dim_processo.parquet"
DIM_DATA = PASTA_GOLD / "dim_data.parquet"
DIM_ORG = PASTA_GOLD / "dim_organizacao.parquet"
DIM_LOCAL = PASTA_GOLD / "dim_localidade.parquet"
DIM_MODAL = PASTA_GOLD / "dim_modal.parquet"
DIM_TIPO_PAG = PASTA_GOLD / "dim_tipo_pagamento.parquet"

BRIDGE_VIAJANTE = PASTA_GOLD / "bridge_processo_viajante.parquet"

FATO_PROCESSO = PASTA_GOLD / "fato_processo_viagem.parquet"
FATO_PAGAMENTO = PASTA_GOLD / "fato_pagamento.parquet"
FATO_PASSAGEM = PASTA_GOLD / "fato_passagem.parquet"
FATO_TRECHO = PASTA_GOLD / "fato_trecho.parquet"


# FUNÇÕES

def sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def salvar_csv(nome, cabecalho, linhas):

    destino = PASTA_METADATA / nome

    with destino.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.writer(
            f,
            delimiter=";"
        )

        writer.writerow(cabecalho)
        writer.writerows(linhas)

    print(f"✓ {nome}")


# CONEXÃO

con = duckdb.connect()

con.execute(
    f"SET threads = {DUCKDB_THREADS}"
)

con.execute(
    "SET preserve_insertion_order = false"
)

con.execute(
    f"SET memory_limit = '{DUCKDB_MEMORY_LIMIT}'"
)

con.execute(
    f"SET temp_directory = "
    f"'{sql_path(PASTA_TEMP)}'"
)


# PRÉ-REQUISITOS

print("=" * 72)
print("VALIDAÇÃO FINAL DA CAMADA GOLD")
print("=" * 72)

arquivos = [
    DIM_PROCESSO,
    DIM_DATA,
    DIM_ORG,
    DIM_LOCAL,
    DIM_MODAL,
    DIM_TIPO_PAG,
    BRIDGE_VIAJANTE,
    FATO_PROCESSO,
    FATO_PAGAMENTO,
    FATO_PASSAGEM,
    FATO_TRECHO,
]

for arquivo in arquivos:

    if not arquivo.exists():
        raise FileNotFoundError(
            f"Arquivo ausente: {arquivo}"
        )


# 1. CHAVES PRIMÁRIAS / UNICIDADE

print("\n[1/8] Validando chaves principais...")


checks_pk = [
    (
        "dim_processo",
        DIM_PROCESSO,
        "sk_processo"
    ),
    (
        "dim_data",
        DIM_DATA,
        "sk_data"
    ),
    (
        "dim_organizacao",
        DIM_ORG,
        "sk_organizacao"
    ),
    (
        "dim_localidade",
        DIM_LOCAL,
        "sk_localidade"
    ),
    (
        "dim_modal",
        DIM_MODAL,
        "sk_modal"
    ),
    (
        "dim_tipo_pagamento",
        DIM_TIPO_PAG,
        "sk_tipo_pagamento"
    ),
    (
        "fato_processo_viagem",
        FATO_PROCESSO,
        "sk_processo"
    ),
    (
        "fato_pagamento",
        FATO_PAGAMENTO,
        "sk_pagamento"
    ),
    (
        "fato_passagem",
        FATO_PASSAGEM,
        "sk_passagem"
    ),
    (
        "fato_trecho",
        FATO_TRECHO,
        "sk_trecho"
    ),
]

linhas = []

for tabela, arquivo, chave in checks_pk:

    resultado = con.execute(
        f"""
        SELECT
            COUNT(*) AS total,

            COUNT("{chave}")
                AS preenchidas,

            COUNT(DISTINCT "{chave}")
                AS distintas

        FROM read_parquet(
            '{sql_path(arquivo)}'
        )
        """
    ).fetchone()

    total, preenchidas, distintas = resultado

    nulas = total - preenchidas
    duplicadas = total - distintas

    status = (
        "OK"
        if nulas == 0
        and duplicadas == 0
        else "ERRO"
    )

    linhas.append([
        tabela,
        chave,
        total,
        nulas,
        distintas,
        duplicadas,
        status
    ])


salvar_csv(
    "03_validacao_chaves_gold.csv",
    [
        "tabela",
        "chave",
        "total",
        "chaves_nulas",
        "chaves_distintas",
        "duplicidades_chave",
        "status"
    ],
    linhas
)


# 2. INTEGRIDADE DIM_PROCESSO

print("\n[2/8] Validando relacionamento com DimProcesso...")


linhas = []

for tabela, fato in [
    ("fato_pagamento", FATO_PAGAMENTO),
    ("fato_passagem", FATO_PASSAGEM),
    ("fato_trecho", FATO_TRECHO),
]:

    resultado = con.execute(
        f"""
        SELECT
            COUNT(*) AS registros,

            COUNT(*) FILTER (
                WHERE d.sk_processo
                IS NULL
            ) AS orfaos

        FROM read_parquet(
            '{sql_path(fato)}'
        ) f

        LEFT JOIN read_parquet(
            '{sql_path(DIM_PROCESSO)}'
        ) d
            ON f.sk_processo
             = d.sk_processo
        """
    ).fetchone()

    linhas.append([
        tabela,
        resultado[0],
        resultado[1],
        (
            "OK"
            if resultado[1] == 0
            else "ERRO"
        )
    ])


salvar_csv(
    "04_integridade_dim_processo.csv",
    [
        "tabela",
        "registros",
        "processos_orfaos",
        "status"
    ],
    linhas
)


# 3. INTEGRIDADE DAS OUTRAS DIMENSÕES

print("\n[3/8] Validando demais dimensões...")


relacionamentos = [
    (
        "fato_pagamento",
        FATO_PAGAMENTO,
        "sk_tipo_pagamento",
        DIM_TIPO_PAG,
        "sk_tipo_pagamento"
    ),

    (
        "fato_pagamento",
        FATO_PAGAMENTO,
        "sk_orgao_superior",
        DIM_ORG,
        "sk_organizacao"
    ),

    (
        "fato_pagamento",
        FATO_PAGAMENTO,
        "sk_orgao_pagador",
        DIM_ORG,
        "sk_organizacao"
    ),

    (
        "fato_pagamento",
        FATO_PAGAMENTO,
        "sk_unidade_gestora_pagadora",
        DIM_ORG,
        "sk_organizacao"
    ),

    (
        "fato_passagem",
        FATO_PASSAGEM,
        "sk_modal",
        DIM_MODAL,
        "sk_modal"
    ),

    (
        "fato_passagem",
        FATO_PASSAGEM,
        "sk_localidade_origem_ida",
        DIM_LOCAL,
        "sk_localidade"
    ),

    (
        "fato_passagem",
        FATO_PASSAGEM,
        "sk_localidade_destino_ida",
        DIM_LOCAL,
        "sk_localidade"
    ),

    (
        "fato_passagem",
        FATO_PASSAGEM,
        "sk_localidade_origem_volta",
        DIM_LOCAL,
        "sk_localidade"
    ),

    (
        "fato_passagem",
        FATO_PASSAGEM,
        "sk_localidade_destino_volta",
        DIM_LOCAL,
        "sk_localidade"
    ),

    (
        "fato_trecho",
        FATO_TRECHO,
        "sk_modal",
        DIM_MODAL,
        "sk_modal"
    ),

    (
        "fato_trecho",
        FATO_TRECHO,
        "sk_localidade_origem",
        DIM_LOCAL,
        "sk_localidade"
    ),

    (
        "fato_trecho",
        FATO_TRECHO,
        "sk_localidade_destino",
        DIM_LOCAL,
        "sk_localidade"
    ),

    (
        "fato_processo_viagem",
        FATO_PROCESSO,
        "sk_orgao_superior",
        DIM_ORG,
        "sk_organizacao"
    ),

    (
        "fato_processo_viagem",
        FATO_PROCESSO,
        "sk_orgao_solicitante",
        DIM_ORG,
        "sk_organizacao"
    ),

    (
        "fato_processo_viagem",
        FATO_PROCESSO,
        "sk_data_inicio",
        DIM_DATA,
        "sk_data"
    ),

    (
        "fato_processo_viagem",
        FATO_PROCESSO,
        "sk_data_fim",
        DIM_DATA,
        "sk_data"
    ),

    (
        "fato_passagem",
        FATO_PASSAGEM,
        "sk_data_emissao",
        DIM_DATA,
        "sk_data"
    ),

    (
        "fato_trecho",
        FATO_TRECHO,
        "sk_data_origem",
        DIM_DATA,
        "sk_data"
    ),

    (
        "fato_trecho",
        FATO_TRECHO,
        "sk_data_destino",
        DIM_DATA,
        "sk_data"
    ),
]


linhas = []

for (
    tabela,
    fato,
    fk,
    dimensao,
    pk
) in relacionamentos:

    resultado = con.execute(
        f"""
        SELECT
            COUNT(*) AS total,

            COUNT(*) FILTER (
                WHERE f."{fk}" IS NULL
            ) AS fk_nula,

            COUNT(*) FILTER (
                WHERE f."{fk}" IS NOT NULL
                  AND d."{pk}" IS NULL
            ) AS orfaos

        FROM read_parquet(
            '{sql_path(fato)}'
        ) f

        LEFT JOIN read_parquet(
            '{sql_path(dimensao)}'
        ) d
            ON f."{fk}" = d."{pk}"
        """
    ).fetchone()

    total, nulas, orfaos = resultado

    status = (
        "OK"
        if orfaos == 0
        else "ERRO"
    )

    linhas.append([
        tabela,
        fk,
        dimensao.stem,
        total,
        nulas,
        orfaos,
        status
    ])


salvar_csv(
    "05_integridade_dimensoes_gold.csv",
    [
        "tabela_fato",
        "chave_estrangeira",
        "dimensao",
        "registros",
        "fk_nulas",
        "fk_orfas",
        "status"
    ],
    linhas
)


# 4. RECONCILIAÇÃO FINANCEIRA

print("\n[4/8] Reconciliando valores financeiros...")


linhas = []


# Pagamento Silver x Gold

silver_pag = con.execute(
    f"""
    SELECT
        ano_fonte,
        tipo_pagamento_normalizado,
        SUM(valor)

    FROM read_parquet(
        '{sql_path(PAGAMENTO_S)}'
    )

    GROUP BY
        ano_fonte,
        tipo_pagamento_normalizado

    ORDER BY
        ano_fonte,
        tipo_pagamento_normalizado
    """
).fetchall()


gold_pag = con.execute(
    f"""
    SELECT
        ano_fonte,
        tipo_pagamento_normalizado,
        SUM(valor)

    FROM read_parquet(
        '{sql_path(FATO_PAGAMENTO)}'
    )

    GROUP BY
        ano_fonte,
        tipo_pagamento_normalizado

    ORDER BY
        ano_fonte,
        tipo_pagamento_normalizado
    """
).fetchall()


silver_dict = {
    (ano, tipo): valor
    for ano, tipo, valor
    in silver_pag
}

gold_dict = {
    (ano, tipo): valor
    for ano, tipo, valor
    in gold_pag
}


for chave in sorted(
    set(silver_dict)
    | set(gold_dict)
):

    valor_silver = silver_dict.get(
        chave,
        0
    )

    valor_gold = gold_dict.get(
        chave,
        0
    )

    diferenca = (
        valor_gold
        -
        valor_silver
    )

    linhas.append([
        chave[0],
        "PAGAMENTO",
        chave[1],
        valor_silver,
        valor_gold,
        diferenca,
        (
            "OK"
            if abs(diferenca) <= 0.01
            else "ERRO"
        )
    ])


# Passagem Silver x Gold

silver_pass = con.execute(
    f"""
    SELECT
        ano_fonte,
        SUM(custo_total_passagem)

    FROM read_parquet(
        '{sql_path(PASSAGEM_S)}'
    )

    GROUP BY ano_fonte
    ORDER BY ano_fonte
    """
).fetchall()


gold_pass = con.execute(
    f"""
    SELECT
        ano_fonte,
        SUM(custo_total_passagem)

    FROM read_parquet(
        '{sql_path(FATO_PASSAGEM)}'
    )

    GROUP BY ano_fonte
    ORDER BY ano_fonte
    """
).fetchall()


for (
    s,
    g
) in zip(
    silver_pass,
    gold_pass
):

    diferenca = g[1] - s[1]

    linhas.append([
        s[0],
        "PASSAGEM",
        "CUSTO_TOTAL_PASSAGEM",
        s[1],
        g[1],
        diferenca,
        (
            "OK"
            if abs(diferenca) <= 0.01
            else "ERRO"
        )
    ])


salvar_csv(
    "06_reconciliacao_financeira_gold.csv",
    [
        "ano",
        "fonte",
        "metrica",
        "valor_silver",
        "valor_gold",
        "diferenca",
        "status"
    ],
    linhas
)


# 5. ANTECEDÊNCIA

print("\n[5/8] Auditando antecedência...")


linhas = con.execute(
    f"""
    SELECT
        ano_fonte,

        faixa_antecedencia,

        COUNT(*) AS registros,

        SUM(custo_total_passagem)
            AS custo_total,

        AVG(custo_total_passagem)
            AS custo_medio,

        MEDIAN(custo_total_passagem)
            AS custo_mediano,

        AVG(antecedencia_dias)
            AS antecedencia_media,

        MEDIAN(antecedencia_dias)
            AS antecedencia_mediana

    FROM read_parquet(
        '{sql_path(FATO_PASSAGEM)}'
    )

    GROUP BY
        ano_fonte,
        faixa_antecedencia

    ORDER BY
        ano_fonte,
        faixa_antecedencia
    """
).fetchall()


salvar_csv(
    "07_perfil_antecedencia_gold.csv",
    [
        "ano",
        "faixa_antecedencia",
        "registros",
        "custo_total",
        "custo_medio",
        "custo_mediano",
        "antecedencia_media",
        "antecedencia_mediana"
    ],
    linhas
)


# 6. PROCESSOS REPETIDOS

print("\n[6/8] Auditando processos repetidos...")


linhas = con.execute(
    f"""
    SELECT
        fp.ano_fonte,

        dp.identificador_processo_viagem,

        fp.sk_processo,

        fp.qtd_registros_viagem,

        fp.qtd_pcdp_distintos,

        fp.qtd_situacoes_distintas,

        fp.qtd_datas_inicio_distintas,

        fp.qtd_datas_fim_distintas,

        fp.qtd_destinos_textuais_distintos,

        fp.qtd_motivos_distintos,

        fp.qtd_valor_diarias_distintos,

        fp.qtd_valor_passagens_distintos,

        fp.qtd_valor_devolucao_distintos,

        fp.qtd_valor_outros_distintos,

        fp.qtd_viajantes_identificados,

        fp.flag_financeiro_multivalorado

    FROM read_parquet(
        '{sql_path(FATO_PROCESSO)}'
    ) fp

    INNER JOIN read_parquet(
        '{sql_path(DIM_PROCESSO)}'
    ) dp
        ON fp.sk_processo
         = dp.sk_processo

    WHERE
        fp.flag_processo_repetido_fonte

    ORDER BY
        fp.ano_fonte,
        dp.identificador_processo_viagem
    """
).fetchall()


salvar_csv(
    "08_processos_repetidos_gold.csv",
    [
        "ano",
        "identificador_processo_viagem",
        "sk_processo",
        "qtd_registros_viagem",
        "qtd_pcdp_distintos",
        "qtd_situacoes_distintas",
        "qtd_datas_inicio_distintas",
        "qtd_datas_fim_distintas",
        "qtd_destinos_textuais_distintos",
        "qtd_motivos_distintos",
        "qtd_valor_diarias_distintos",
        "qtd_valor_passagens_distintos",
        "qtd_valor_devolucao_distintos",
        "qtd_valor_outros_distintos",
        "qtd_viajantes_identificados",
        "flag_financeiro_multivalorado"
    ],
    linhas
)


# 7. DETALHE DOS PROCESSOS FINANCEIROS MULTIVALORADOS

print(
    "\n[7/8] Extraindo processos financeiros multivalorados..."
)


linhas = con.execute(
    f"""
    WITH processos AS (

        SELECT sk_processo

        FROM read_parquet(
            '{sql_path(FATO_PROCESSO)}'
        )

        WHERE flag_financeiro_multivalorado
    )

    SELECT
        v.ano_fonte,

        v.identificador_processo_viagem,

        v.sk_processo,

        v.numero_pcdp,

        v.valor_diarias,

        v.valor_passagens,

        v.valor_devolucao,

        v.valor_outros_gastos,

        v.data_inicio,

        v.data_fim,

        v.destinos,

        v.arquivo_origem,

        v.ordem_registro_arquivo

    FROM read_parquet(
        '{sql_path(VIAGEM_S)}'
    ) v

    INNER JOIN processos p
        ON v.sk_processo
         = p.sk_processo

    ORDER BY
        v.ano_fonte,
        v.identificador_processo_viagem,
        v.ordem_registro_arquivo
    """
).fetchall()


salvar_csv(
    "09_detalhe_financeiro_multivalorado.csv",
    [
        "ano",
        "identificador_processo_viagem",
        "sk_processo",
        "numero_pcdp",
        "valor_diarias",
        "valor_passagens",
        "valor_devolucao",
        "valor_outros_gastos",
        "data_inicio",
        "data_fim",
        "destinos",
        "arquivo_origem",
        "ordem_registro_arquivo"
    ],
    linhas
)


# 8. COBERTURA E LIMITES TEMPORAIS

print("\n[8/8] Auditando cobertura e datas...")


linhas_cobertura = con.execute(
    f"""
    SELECT
        fp.ano_fonte,

        COUNT(*)
            AS processos,

        COUNT(*) FILTER (
            WHERE fp.sk_orgao_superior
            IS NOT NULL
        )
            AS processos_com_orgao_superior,

        COUNT(*) FILTER (
            WHERE fp.sk_orgao_solicitante
            IS NOT NULL
        )
            AS processos_com_orgao_solicitante,

        COUNT(*) FILTER (
            WHERE fp.sk_data_inicio
            IS NOT NULL
        )
            AS processos_com_data_inicio,

        COUNT(*) FILTER (
            WHERE fp.sk_data_fim
            IS NOT NULL
        )
            AS processos_com_data_fim,

        COUNT(*) FILTER (
            WHERE fp.qtd_viajantes_identificados > 0
        )
            AS processos_com_viajante_identificado

    FROM read_parquet(
        '{sql_path(FATO_PROCESSO)}'
    ) fp

    GROUP BY fp.ano_fonte
    ORDER BY fp.ano_fonte
    """
).fetchall()


salvar_csv(
    "10_cobertura_processo_gold.csv",
    [
        "ano",
        "processos",
        "com_orgao_superior",
        "com_orgao_solicitante",
        "com_data_inicio",
        "com_data_fim",
        "com_viajante_identificado"
    ],
    linhas_cobertura
)


datas = con.execute(
    f"""
    SELECT
        MIN(data),
        MAX(data),
        COUNT(*)

    FROM read_parquet(
        '{sql_path(DIM_DATA)}'
    )
    """
).fetchall()


salvar_csv(
    "11_intervalo_dim_data.csv",
    [
        "data_minima",
        "data_maxima",
        "quantidade_dias"
    ],
    datas
)


# RESUMO AUTOMÁTICO

print("\n" + "=" * 72)
print("RESUMO")
print("=" * 72)


erros_chaves = con.execute(
    f"""
    SELECT
        COUNT(*)
        -
        COUNT(
            DISTINCT sk_processo
        )

    FROM read_parquet(
        '{sql_path(FATO_PROCESSO)}'
    )
    """
).fetchone()[0]


financeiros_multivalorados = con.execute(
    f"""
    SELECT COUNT(*)

    FROM read_parquet(
        '{sql_path(FATO_PROCESSO)}'
    )

    WHERE flag_financeiro_multivalorado
    """
).fetchone()[0]


passagens_sem_antecedencia = con.execute(
    f"""
    SELECT COUNT(*)

    FROM read_parquet(
        '{sql_path(FATO_PASSAGEM)}'
    )

    WHERE antecedencia_dias IS NULL
    """
).fetchone()[0]


passagens_apos_inicio = con.execute(
    f"""
    SELECT COUNT(*)

    FROM read_parquet(
        '{sql_path(FATO_PASSAGEM)}'
    )

    WHERE antecedencia_dias < 0
    """
).fetchone()[0]


print(
    "Duplicidades de SK_Processo na FatoProcesso:",
    erros_chaves
)

print(
    "Processos financeiros multivalorados:",
    financeiros_multivalorados
)

print(
    "Passagens sem cálculo de antecedência:",
    f"{passagens_sem_antecedencia:,}"
)

print(
    "Registros com emissão após início:",
    f"{passagens_apos_inicio:,}"
)


con.close()


print("\n" + "=" * 72)
print("VALIDAÇÃO GOLD CONCLUÍDA")
print("=" * 72)

print(
    "\nRelatórios disponíveis em:"
)

print(
    PASTA_METADATA
)