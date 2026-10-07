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

PASTA_GOLD.mkdir(
    parents=True,
    exist_ok=True
)

PASTA_METADATA.mkdir(
    parents=True,
    exist_ok=True
)

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

PASTA_DUCKDB_TEMP = Path(
    os.getenv(
        "PI_DUCKDB_TEMP_DIR",
        str(DEFAULT_DUCKDB_TEMP_DIR)
    )
).expanduser().resolve()

PASTA_DUCKDB_TEMP.mkdir(
    parents=True,
    exist_ok=True
)


VIAGEM = PASTA_SILVER / "viagem.parquet"
TRECHO = PASTA_SILVER / "trecho.parquet"
PASSAGEM = PASTA_SILVER / "passagem.parquet"
PAGAMENTO = PASTA_SILVER / "pagamento.parquet"


# FUNÇÕES AUXILIARES

def sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def caminho_gold(nome: str) -> Path:
    return PASTA_GOLD / f"{nome}.parquet"


def remover_se_existir(path: Path):
    if path.exists():
        path.unlink()


def copiar_para_parquet(
    con,
    nome,
    consulta
):

    destino = caminho_gold(nome)

    remover_se_existir(destino)

    print(
        f"\nConstruindo: {nome}.parquet"
    )

    con.execute(
        f"""
        COPY (
            {consulta}
        )
        TO '{sql_path(destino)}'
        (
            FORMAT PARQUET,
            COMPRESSION ZSTD
        )
        """
    )

    total = con.execute(
        f"""
        SELECT COUNT(*)
        FROM read_parquet(
            '{sql_path(destino)}'
        )
        """
    ).fetchone()[0]

    print(
        f"✓ {nome}.parquet: "
        f"{total:,} registros"
    )

    return total


def hash_org(
    tipo,
    codigo,
    nome
):

    return f"""
        CASE
            WHEN {codigo} IS NULL
             AND {nome} IS NULL
            THEN NULL

            ELSE MD5(
                '{tipo}'
                || '|'
                || COALESCE(
                    UPPER(TRIM({codigo})),
                    ''
                )
                || '|'
                || COALESCE(
                    UPPER(TRIM({nome})),
                    ''
                )
            )
        END
    """.strip()


def hash_localidade(
    pais,
    uf,
    cidade
):

    return f"""
        CASE
            WHEN {pais} IS NULL
             AND {uf} IS NULL
             AND {cidade} IS NULL
            THEN NULL

            ELSE MD5(
                COALESCE(
                    UPPER(TRIM({pais})),
                    ''
                )
                || '|'
                || COALESCE(
                    UPPER(TRIM({uf})),
                    ''
                )
                || '|'
                || COALESCE(
                    UPPER(TRIM({cidade})),
                    ''
                )
            )
        END
    """.strip()


def hash_modal(coluna):

    return f"""
        CASE
            WHEN {coluna} IS NULL
            THEN NULL

            ELSE MD5(
                UPPER(
                    TRIM({coluna})
                )
            )
        END
    """.strip()


def hash_tipo_pagamento(coluna):

    return f"""
        CASE
            WHEN {coluna} IS NULL
            THEN NULL

            ELSE MD5(
                UPPER(
                    TRIM({coluna})
                )
            )
        END
    """.strip()


def chave_data(coluna):

    return f"""
        CASE
            WHEN {coluna} IS NULL
            THEN NULL

            ELSE CAST(
                STRFTIME(
                    {coluna},
                    '%Y%m%d'
                )
                AS INTEGER
            )
        END
    """.strip()


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
    f"'{sql_path(PASTA_DUCKDB_TEMP)}'"
)


# 1. DIM_PROCESSO

print("\n" + "=" * 72)
print("1. DIMENSÃO PROCESSO")
print("=" * 72)


copiar_para_parquet(
    con,
    "dim_processo",
    f"""
    SELECT
        sk_processo,

        ano_fonte,

        MIN(
            identificador_processo_viagem
        )
            AS identificador_processo_viagem,

        CASE
            WHEN COUNT(
                DISTINCT numero_pcdp
            ) <= 1
            THEN MIN(numero_pcdp)

            ELSE NULL
        END
            AS numero_pcdp,

        COUNT(
            DISTINCT numero_pcdp
        )
            AS qtd_pcdp_distintos,

        COUNT(*)
            AS qtd_registros_viagem_fonte

    FROM read_parquet(
        '{sql_path(VIAGEM)}'
    )

    GROUP BY
        sk_processo,
        ano_fonte
    """
)


# 2. DIM_TIPO_PAGAMENTO

print("\n" + "=" * 72)
print("2. DIMENSÃO TIPO DE PAGAMENTO")
print("=" * 72)


copiar_para_parquet(
    con,
    "dim_tipo_pagamento",
    f"""
    SELECT
        MD5(
            tipo_pagamento_normalizado
        )
            AS sk_tipo_pagamento,

        tipo_pagamento_normalizado
            AS codigo_tipo_pagamento,

        CASE
            WHEN tipo_pagamento_normalizado
                = 'DIARIAS'
            THEN 'Diárias'

            WHEN tipo_pagamento_normalizado
                = 'PASSAGEM'
            THEN 'Passagem'

            WHEN tipo_pagamento_normalizado
                = 'RESTITUICAO'
            THEN 'Restituição'

            WHEN tipo_pagamento_normalizado
                = 'SEGURO'
            THEN 'Serviço correlato: seguro'

            ELSE tipo_pagamento_normalizado
        END
            AS descricao_tipo_pagamento

    FROM (
        SELECT DISTINCT
            tipo_pagamento_normalizado

        FROM read_parquet(
            '{sql_path(PAGAMENTO)}'
        )

        WHERE tipo_pagamento_normalizado
            IS NOT NULL
    )

    ORDER BY
        codigo_tipo_pagamento
    """
)


# 3. DIM_MODAL

print("\n" + "=" * 72)
print("3. DIMENSÃO MODAL")
print("=" * 72)


copiar_para_parquet(
    con,
    "dim_modal",
    f"""
    WITH base AS (

        SELECT
            meio_transporte_normalizado
                AS modal,
            'TRECHO'
                AS origem

        FROM read_parquet(
            '{sql_path(TRECHO)}'
        )

        WHERE meio_transporte_normalizado
            IS NOT NULL

        UNION ALL

        SELECT
            meio_transporte_normalizado
                AS modal,
            'PASSAGEM'
                AS origem

        FROM read_parquet(
            '{sql_path(PASSAGEM)}'
        )

        WHERE meio_transporte_normalizado
            IS NOT NULL
    )

    SELECT
        MD5(modal)
            AS sk_modal,

        modal
            AS modal,

        CASE
            WHEN modal = 'INVÁLIDO'
            THEN FALSE
            ELSE TRUE
        END
            AS flag_modal_valido,

        MAX(
            CASE
                WHEN origem = 'TRECHO'
                THEN 1
                ELSE 0
            END
        ) = 1
            AS flag_presente_trecho,

        MAX(
            CASE
                WHEN origem = 'PASSAGEM'
                THEN 1
                ELSE 0
            END
        ) = 1
            AS flag_presente_passagem

    FROM base

    GROUP BY modal

    ORDER BY modal
    """
)


# 4. DIM_ORGANIZACAO

print("\n" + "=" * 72)
print("4. DIMENSÃO ORGANIZAÇÃO")
print("=" * 72)


copiar_para_parquet(
    con,
    "dim_organizacao",
    f"""
    WITH base AS (

        SELECT
            'ORGAO_SUPERIOR'
                AS tipo_organizacao,

            codigo_orgao_superior
                AS codigo,

            nome_orgao_superior
                AS nome

        FROM read_parquet(
            '{sql_path(VIAGEM)}'
        )


        UNION ALL


        SELECT
            'ORGAO_SOLICITANTE',

            codigo_orgao_solicitante,

            nome_orgao_solicitante

        FROM read_parquet(
            '{sql_path(VIAGEM)}'
        )


        UNION ALL


        SELECT
            'ORGAO_SUPERIOR',

            codigo_orgao_superior,

            nome_orgao_superior

        FROM read_parquet(
            '{sql_path(PAGAMENTO)}'
        )


        UNION ALL


        SELECT
            'ORGAO_PAGADOR',

            codigo_orgao_pagador,

            nome_orgao_pagador

        FROM read_parquet(
            '{sql_path(PAGAMENTO)}'
        )


        UNION ALL


        SELECT
            'UNIDADE_GESTORA_PAGADORA',

            codigo_unidade_gestora_pagadora,

            nome_unidade_gestora_pagadora

        FROM read_parquet(
            '{sql_path(PAGAMENTO)}'
        )
    ),

    normalizado AS (

        SELECT
            tipo_organizacao,

            NULLIF(
                TRIM(codigo),
                ''
            )
                AS codigo,

            NULLIF(
                TRIM(nome),
                ''
            )
                AS nome

        FROM base
    ),

    agrupado AS (

        SELECT
            tipo_organizacao,

            UPPER(
                COALESCE(
                    codigo,
                    ''
                )
            )
                AS codigo_normalizado,

            UPPER(
                COALESCE(
                    nome,
                    ''
                )
            )
                AS nome_normalizado,

            MIN(codigo)
                AS codigo,

            MIN(nome)
                AS nome

        FROM normalizado

        WHERE
            codigo IS NOT NULL
            OR nome IS NOT NULL

        GROUP BY
            tipo_organizacao,
            codigo_normalizado,
            nome_normalizado
    )

    SELECT
        MD5(
            tipo_organizacao
            || '|'
            || codigo_normalizado
            || '|'
            || nome_normalizado
        )
            AS sk_organizacao,

        tipo_organizacao,

        codigo,

        nome,

        codigo_normalizado,

        nome_normalizado

    FROM agrupado

    ORDER BY
        tipo_organizacao,
        nome
    """
)


# 5. DIM_LOCALIDADE

print("\n" + "=" * 72)
print("5. DIMENSÃO LOCALIDADE")
print("=" * 72)


copiar_para_parquet(
    con,
    "dim_localidade",
    f"""
    WITH base AS (

        -- TRECHO: ORIGEM

        SELECT
            pais_origem
                AS pais,

            uf_origem
                AS uf,

            cidade_origem
                AS cidade

        FROM read_parquet(
            '{sql_path(TRECHO)}'
        )


        UNION ALL


        -- TRECHO: DESTINO

        SELECT
            pais_destino,
            uf_destino,
            cidade_destino

        FROM read_parquet(
            '{sql_path(TRECHO)}'
        )


        UNION ALL


        -- PASSAGEM: IDA - ORIGEM

        SELECT
            pais_origem_ida,
            uf_origem_ida,
            cidade_origem_ida

        FROM read_parquet(
            '{sql_path(PASSAGEM)}'
        )


        UNION ALL


        -- PASSAGEM: IDA - DESTINO

        SELECT
            pais_destino_ida,
            uf_destino_ida,
            cidade_destino_ida

        FROM read_parquet(
            '{sql_path(PASSAGEM)}'
        )


        UNION ALL


        -- PASSAGEM: VOLTA - ORIGEM

        SELECT
            pais_origem_volta,
            uf_origem_volta,
            cidade_origem_volta

        FROM read_parquet(
            '{sql_path(PASSAGEM)}'
        )


        UNION ALL


        -- PASSAGEM: VOLTA - DESTINO

        SELECT
            pais_destino_volta,
            uf_destino_volta,
            cidade_destino_volta

        FROM read_parquet(
            '{sql_path(PASSAGEM)}'
        )
    ),

    normalizado AS (

        SELECT
            NULLIF(
                TRIM(pais),
                ''
            )
                AS pais,

            NULLIF(
                TRIM(uf),
                ''
            )
                AS uf,

            NULLIF(
                TRIM(cidade),
                ''
            )
                AS cidade

        FROM base
    ),

    agrupado AS (

        SELECT
            UPPER(
                COALESCE(
                    pais,
                    ''
                )
            )
                AS pais_normalizado,

            UPPER(
                COALESCE(
                    uf,
                    ''
                )
            )
                AS uf_normalizada,

            UPPER(
                COALESCE(
                    cidade,
                    ''
                )
            )
                AS cidade_normalizada,

            MIN(pais)
                AS pais,

            MIN(uf)
                AS uf,

            MIN(cidade)
                AS cidade

        FROM normalizado

        WHERE
            pais IS NOT NULL
            OR uf IS NOT NULL
            OR cidade IS NOT NULL

        GROUP BY
            pais_normalizado,
            uf_normalizada,
            cidade_normalizada
    )

    SELECT
        MD5(
            pais_normalizado
            || '|'
            || uf_normalizada
            || '|'
            || cidade_normalizada
        )
            AS sk_localidade,

        pais,

        uf,

        cidade,

        pais_normalizado,

        uf_normalizada,

        cidade_normalizada,

        CASE
            WHEN UPPER(
                COALESCE(
                    pais,
                    ''
                )
            ) IN (
                'BRASIL',
                'BRAZIL'
            )
            THEN TRUE

            ELSE FALSE
        END
            AS flag_brasil

    FROM agrupado

    ORDER BY
        pais,
        uf,
        cidade
    """
)


# 6. DIM_DATA

print("\n" + "=" * 72)
print("6. DIMENSÃO DATA")
print("=" * 72)


copiar_para_parquet(
    con,
    "dim_data",
    f"""
    WITH datas AS (

        SELECT data_inicio AS data
        FROM read_parquet(
            '{sql_path(VIAGEM)}'
        )

        UNION ALL

        SELECT data_fim
        FROM read_parquet(
            '{sql_path(VIAGEM)}'
        )

        UNION ALL

        SELECT data_origem
        FROM read_parquet(
            '{sql_path(TRECHO)}'
        )

        UNION ALL

        SELECT data_destino
        FROM read_parquet(
            '{sql_path(TRECHO)}'
        )

        UNION ALL

        SELECT data_emissao
        FROM read_parquet(
            '{sql_path(PASSAGEM)}'
        )
    ),

    limites AS (

        SELECT
            MIN(data)
                AS data_min,

            MAX(data)
                AS data_max

        FROM datas

        WHERE data IS NOT NULL
    ),

    calendario AS (

        SELECT
            CAST(gs AS DATE)
                AS data

        FROM limites,

        GENERATE_SERIES(
            data_min,
            data_max,
            INTERVAL 1 DAY
        )
            AS t(gs)
    )

    SELECT
        CAST(
            STRFTIME(
                data,
                '%Y%m%d'
            )
            AS INTEGER
        )
            AS sk_data,

        data,

        YEAR(data)
            AS ano,

        MONTH(data)
            AS mes,

        CASE MONTH(data)
            WHEN 1 THEN 'Janeiro'
            WHEN 2 THEN 'Fevereiro'
            WHEN 3 THEN 'Março'
            WHEN 4 THEN 'Abril'
            WHEN 5 THEN 'Maio'
            WHEN 6 THEN 'Junho'
            WHEN 7 THEN 'Julho'
            WHEN 8 THEN 'Agosto'
            WHEN 9 THEN 'Setembro'
            WHEN 10 THEN 'Outubro'
            WHEN 11 THEN 'Novembro'
            WHEN 12 THEN 'Dezembro'
        END
            AS nome_mes,

        CAST(
            EXTRACT(
                QUARTER FROM data
            )
            AS TINYINT
        )
            AS trimestre,

        CASE
            WHEN MONTH(data) <= 6
            THEN 1
            ELSE 2
        END
            AS semestre,

        DAY(data)
            AS dia_mes,

        CAST(
            STRFTIME(
                data,
                '%u'
            )
            AS TINYINT
        )
            AS dia_semana_iso,

        CASE
            CAST(
                STRFTIME(
                    data,
                    '%u'
                )
                AS INTEGER
            )

            WHEN 1 THEN 'Segunda-feira'
            WHEN 2 THEN 'Terça-feira'
            WHEN 3 THEN 'Quarta-feira'
            WHEN 4 THEN 'Quinta-feira'
            WHEN 5 THEN 'Sexta-feira'
            WHEN 6 THEN 'Sábado'
            WHEN 7 THEN 'Domingo'
        END
            AS nome_dia_semana,

        CASE
            WHEN CAST(
                STRFTIME(
                    data,
                    '%u'
                )
                AS INTEGER
            ) IN (6, 7)
            THEN TRUE

            ELSE FALSE
        END
            AS flag_fim_semana

    FROM calendario

    ORDER BY data
    """
)


# 7. BRIDGE_PROCESSO_VIAJANTE

print("\n" + "=" * 72)
print("7. BRIDGE PROCESSO × VIAJANTE")
print("=" * 72)


copiar_para_parquet(
    con,
    "bridge_processo_viajante",
    f"""
    WITH base AS (

        SELECT
            sk_processo,

            ano_fonte,

            id_viajante_hash,

            nome_viajante,

            status_cpf_viajante,

            CASE
                WHEN id_viajante_hash
                    IS NOT NULL

                THEN MD5(
                    'CPF_HASH|'
                    || id_viajante_hash
                )

                WHEN nome_viajante IS NOT NULL
                 AND UPPER(
                    TRIM(nome_viajante)
                 ) NOT LIKE 'SEM INFORMA%'
                 AND UPPER(
                    TRIM(nome_viajante)
                 ) NOT IN (
                    'SIGILOSO',
                    'SIGILOSA'
                 )

                THEN MD5(
                    'NOME_HASH|'
                    || UPPER(
                        TRIM(nome_viajante)
                    )
                )

                ELSE NULL
            END
                AS sk_viajante,

            CASE
                WHEN id_viajante_hash
                    IS NOT NULL
                THEN 'CPF_HASH'

                WHEN nome_viajante
                    IS NOT NULL
                THEN 'NOME_HASH'

                ELSE 'NAO_IDENTIFICADO'
            END
                AS metodo_identificacao

        FROM read_parquet(
            '{sql_path(VIAGEM)}'
        )
    )

    SELECT
        sk_processo,

        ano_fonte,

        sk_viajante,

        MIN(
            metodo_identificacao
        )
            AS metodo_identificacao,

        COUNT(*)
            AS qtd_registros_fonte

    FROM base

    WHERE sk_viajante
        IS NOT NULL

    GROUP BY
        sk_processo,
        ano_fonte,
        sk_viajante
    """
)


# 8. FATO_PROCESSO_VIAGEM

print("\n" + "=" * 72)
print("8. FATO PROCESSO VIAGEM")
print("=" * 72)


fato_processo_query = f"""
WITH base AS (

    SELECT
        sk_processo,

        ano_fonte,

        COUNT(*)
            AS qtd_registros_viagem,

        COUNT(
            DISTINCT numero_pcdp
        )
            AS qtd_pcdp_distintos,

        CASE
            WHEN COUNT(
                DISTINCT numero_pcdp
            ) <= 1
            THEN MIN(numero_pcdp)
            ELSE NULL
        END
            AS numero_pcdp,

        COUNT(
            DISTINCT situacao_normalizada
        )
            AS qtd_situacoes_distintas,

        CASE
            WHEN COUNT(
                DISTINCT situacao_normalizada
            ) <= 1
            THEN MIN(
                situacao_normalizada
            )
            ELSE 'MULTIPLA'
        END
            AS situacao_processo,

        COUNT(
            DISTINCT viagem_urgente_flag
        )
            AS qtd_flags_urgencia_distintas,

        CASE
            WHEN COUNT(
                DISTINCT viagem_urgente_flag
            ) <= 1
            THEN MAX(
                viagem_urgente_flag
            )
            ELSE NULL
        END
            AS viagem_urgente_flag,

        COUNT(
            DISTINCT data_inicio
        )
            AS qtd_datas_inicio_distintas,

        MIN(data_inicio)
            AS data_inicio_min,

        MAX(data_inicio)
            AS data_inicio_max,

        CASE
            WHEN COUNT(
                DISTINCT data_inicio
            ) <= 1
            THEN MIN(data_inicio)
            ELSE NULL
        END
            AS data_inicio_referencia,

        COUNT(
            DISTINCT data_fim
        )
            AS qtd_datas_fim_distintas,

        MIN(data_fim)
            AS data_fim_min,

        MAX(data_fim)
            AS data_fim_max,

        CASE
            WHEN COUNT(
                DISTINCT data_fim
            ) <= 1
            THEN MIN(data_fim)
            ELSE NULL
        END
            AS data_fim_referencia,

        COUNT(
            DISTINCT destinos
        )
            AS qtd_destinos_textuais_distintos,

        CASE
            WHEN COUNT(
                DISTINCT destinos
            ) <= 1
            THEN MIN(destinos)
            ELSE NULL
        END
            AS destinos_textuais_ref,

        COUNT(
            DISTINCT motivo
        )
            AS qtd_motivos_distintos,

        CASE
            WHEN COUNT(
                DISTINCT motivo
            ) <= 1
            THEN MIN(motivo)
            ELSE NULL
        END
            AS motivo_ref,

        COUNT(
            DISTINCT valor_diarias
        )
            AS qtd_valor_diarias_distintos,

        CASE
            WHEN COUNT(
                DISTINCT valor_diarias
            ) <= 1
            THEN MAX(valor_diarias)
            ELSE NULL
        END
            AS valor_diarias_processo,

        COUNT(
            DISTINCT valor_passagens
        )
            AS qtd_valor_passagens_distintos,

        CASE
            WHEN COUNT(
                DISTINCT valor_passagens
            ) <= 1
            THEN MAX(valor_passagens)
            ELSE NULL
        END
            AS valor_passagens_processo,

        COUNT(
            DISTINCT valor_devolucao
        )
            AS qtd_valor_devolucao_distintos,

        CASE
            WHEN COUNT(
                DISTINCT valor_devolucao
            ) <= 1
            THEN MAX(valor_devolucao)
            ELSE NULL
        END
            AS valor_devolucao_processo,

        COUNT(
            DISTINCT valor_outros_gastos
        )
            AS qtd_valor_outros_distintos,

        CASE
            WHEN COUNT(
                DISTINCT valor_outros_gastos
            ) <= 1
            THEN MAX(
                valor_outros_gastos
            )
            ELSE NULL
        END
            AS valor_outros_gastos_processo,

        COUNT(
            DISTINCT (
                COALESCE(
                    codigo_orgao_superior,
                    ''
                )
                || '|'
                || COALESCE(
                    nome_orgao_superior,
                    ''
                )
            )
        )
            AS qtd_orgao_superior_distintos,

        MIN(
            codigo_orgao_superior
        )
            AS codigo_orgao_superior_ref,

        MIN(
            nome_orgao_superior
        )
            AS nome_orgao_superior_ref,

        COUNT(
            DISTINCT (
                COALESCE(
                    codigo_orgao_solicitante,
                    ''
                )
                || '|'
                || COALESCE(
                    nome_orgao_solicitante,
                    ''
                )
            )
        )
            AS qtd_orgao_solicitante_distintos,

        MIN(
            codigo_orgao_solicitante
        )
            AS codigo_orgao_solicitante_ref,

        MIN(
            nome_orgao_solicitante
        )
            AS nome_orgao_solicitante_ref

    FROM read_parquet(
        '{sql_path(VIAGEM)}'
    )

    GROUP BY
        sk_processo,
        ano_fonte
),

viajantes AS (

    SELECT
        sk_processo,

        COUNT(
            DISTINCT sk_viajante
        )
            AS qtd_viajantes_identificados

    FROM read_parquet(
        '{sql_path(caminho_gold("bridge_processo_viajante"))}'
    )

    GROUP BY sk_processo
)

SELECT
    b.sk_processo,

    b.ano_fonte,

    b.numero_pcdp,

    b.qtd_registros_viagem,

    b.qtd_pcdp_distintos,

    b.situacao_processo,

    b.qtd_situacoes_distintas,

    b.viagem_urgente_flag,

    b.qtd_flags_urgencia_distintas,

    b.data_inicio_referencia,

    b.data_inicio_min,

    b.data_inicio_max,

    b.qtd_datas_inicio_distintas,

    {chave_data("b.data_inicio_referencia")}
        AS sk_data_inicio,

    b.data_fim_referencia,

    b.data_fim_min,

    b.data_fim_max,

    b.qtd_datas_fim_distintas,

    {chave_data("b.data_fim_referencia")}
        AS sk_data_fim,

    b.destinos_textuais_ref,

    b.qtd_destinos_textuais_distintos,

    b.motivo_ref,

    b.qtd_motivos_distintos,

    b.valor_diarias_processo,

    b.qtd_valor_diarias_distintos,

    b.valor_passagens_processo,

    b.qtd_valor_passagens_distintos,

    b.valor_devolucao_processo,

    b.qtd_valor_devolucao_distintos,

    b.valor_outros_gastos_processo,

    b.qtd_valor_outros_distintos,

    CASE
        WHEN b.qtd_valor_diarias_distintos > 1
          OR b.qtd_valor_passagens_distintos > 1
          OR b.qtd_valor_devolucao_distintos > 1
          OR b.qtd_valor_outros_distintos > 1
        THEN TRUE
        ELSE FALSE
    END
        AS flag_financeiro_multivalorado,

    CASE
        WHEN b.qtd_registros_viagem > 1
        THEN TRUE
        ELSE FALSE
    END
        AS flag_processo_repetido_fonte,

    CASE
        WHEN b.qtd_orgao_superior_distintos <= 1
        THEN
            {hash_org(
                "ORGAO_SUPERIOR",
                "b.codigo_orgao_superior_ref",
                "b.nome_orgao_superior_ref"
            )}
        ELSE NULL
    END
        AS sk_orgao_superior,

    CASE
        WHEN b.qtd_orgao_solicitante_distintos <= 1
        THEN
            {hash_org(
                "ORGAO_SOLICITANTE",
                "b.codigo_orgao_solicitante_ref",
                "b.nome_orgao_solicitante_ref"
            )}
        ELSE NULL
    END
        AS sk_orgao_solicitante,

    COALESCE(
        v.qtd_viajantes_identificados,
        0
    )
        AS qtd_viajantes_identificados

FROM base b

LEFT JOIN viajantes v
    ON b.sk_processo = v.sk_processo
"""


copiar_para_parquet(
    con,
    "fato_processo_viagem",
    fato_processo_query
)


# 9. FATO_PAGAMENTO

print("\n" + "=" * 72)
print("9. FATO PAGAMENTO")
print("=" * 72)


copiar_para_parquet(
    con,
    "fato_pagamento",
    f"""
    SELECT
        sk_registro
            AS sk_pagamento,

        sk_processo,

        ano_fonte,

        numero_pcdp,

        {hash_tipo_pagamento(
            "tipo_pagamento_normalizado"
        )}
            AS sk_tipo_pagamento,

        tipo_pagamento_normalizado,

        valor,

        {hash_org(
            "ORGAO_SUPERIOR",
            "codigo_orgao_superior",
            "nome_orgao_superior"
        )}
            AS sk_orgao_superior,

        {hash_org(
            "ORGAO_PAGADOR",
            "codigo_orgao_pagador",
            "nome_orgao_pagador"
        )}
            AS sk_orgao_pagador,

        {hash_org(
            "UNIDADE_GESTORA_PAGADORA",
            "codigo_unidade_gestora_pagadora",
            "nome_unidade_gestora_pagadora"
        )}
            AS sk_unidade_gestora_pagadora,

        hash_observacao,

        ordinal_ocorrencia,

        arquivo_origem,

        ordem_registro_arquivo

    FROM read_parquet(
        '{sql_path(PAGAMENTO)}'
    )
    """
)


# 10. FATO_PASSAGEM

print("\n" + "=" * 72)
print("10. FATO PASSAGEM")
print("=" * 72)


fato_passagem_query = f"""
WITH base AS (

    SELECT
        p.sk_registro
            AS sk_passagem,

        p.sk_processo,

        p.ano_fonte,

        p.numero_pcdp,

        {hash_modal(
            "p.meio_transporte_normalizado"
        )}
            AS sk_modal,

        p.meio_transporte_normalizado,

        {hash_localidade(
            "p.pais_origem_ida",
            "p.uf_origem_ida",
            "p.cidade_origem_ida"
        )}
            AS sk_localidade_origem_ida,

        {hash_localidade(
            "p.pais_destino_ida",
            "p.uf_destino_ida",
            "p.cidade_destino_ida"
        )}
            AS sk_localidade_destino_ida,

        {hash_localidade(
            "p.pais_origem_volta",
            "p.uf_origem_volta",
            "p.cidade_origem_volta"
        )}
            AS sk_localidade_origem_volta,

        {hash_localidade(
            "p.pais_destino_volta",
            "p.uf_destino_volta",
            "p.cidade_destino_volta"
        )}
            AS sk_localidade_destino_volta,

        p.data_emissao,

        {chave_data("p.data_emissao")}
            AS sk_data_emissao,

        p.hora_emissao,

        p.valor_passagem,

        p.taxa_servico,

        p.custo_total_passagem,

        fp.data_inicio_referencia,

        fp.qtd_datas_inicio_distintas,

        CASE
            WHEN p.data_emissao
                IS NOT NULL

             AND fp.data_inicio_referencia
                IS NOT NULL

             AND fp.qtd_datas_inicio_distintas <= 1

            THEN DATE_DIFF(
                'day',
                p.data_emissao,
                fp.data_inicio_referencia
            )

            ELSE NULL
        END
            AS antecedencia_dias,

        p.hash_observacao,

        p.ordinal_ocorrencia,

        p.arquivo_origem,

        p.ordem_registro_arquivo

    FROM read_parquet(
        '{sql_path(PASSAGEM)}'
    )
        p

    LEFT JOIN read_parquet(
        '{sql_path(caminho_gold("fato_processo_viagem"))}'
    )
        fp

        ON p.sk_processo
         = fp.sk_processo
)

SELECT
    *,

    CASE
        WHEN antecedencia_dias IS NULL
        THEN 'SEM_INFORMACAO'

        WHEN antecedencia_dias < 0
        THEN 'EMISSAO_APOS_INICIO'

        WHEN antecedencia_dias <= 3
        THEN '0_A_3_DIAS'

        WHEN antecedencia_dias <= 7
        THEN '4_A_7_DIAS'

        WHEN antecedencia_dias <= 14
        THEN '8_A_14_DIAS'

        WHEN antecedencia_dias <= 30
        THEN '15_A_30_DIAS'

        ELSE 'MAIS_DE_30_DIAS'
    END
        AS faixa_antecedencia,

    CASE
        WHEN antecedencia_dias < 0
        THEN TRUE

        ELSE FALSE
    END
        AS flag_emissao_apos_inicio,

    CASE
        WHEN data_emissao IS NOT NULL
        THEN TRUE
        ELSE FALSE
    END
        AS flag_data_emissao_disponivel

FROM base
"""


copiar_para_parquet(
    con,
    "fato_passagem",
    fato_passagem_query
)


# 11. FATO_TRECHO

print("\n" + "=" * 72)
print("11. FATO TRECHO")
print("=" * 72)


copiar_para_parquet(
    con,
    "fato_trecho",
    f"""
    SELECT
        sk_registro
            AS sk_trecho,

        sk_processo,

        ano_fonte,

        numero_pcdp,

        sequencia_trecho,

        data_origem,

        {chave_data("data_origem")}
            AS sk_data_origem,

        data_destino,

        {chave_data("data_destino")}
            AS sk_data_destino,

        {hash_localidade(
            "pais_origem",
            "uf_origem",
            "cidade_origem"
        )}
            AS sk_localidade_origem,

        {hash_localidade(
            "pais_destino",
            "uf_destino",
            "cidade_destino"
        )}
            AS sk_localidade_destino,

        {hash_modal(
            "meio_transporte_normalizado"
        )}
            AS sk_modal,

        meio_transporte_normalizado,

        numero_diarias,

        missao_flag,

        CASE
            WHEN meio_transporte_normalizado
                = 'INVÁLIDO'
            THEN TRUE
            ELSE FALSE
        END
            AS flag_modal_invalido,

        hash_observacao,

        ordinal_ocorrencia,

        arquivo_origem,

        ordem_registro_arquivo

    FROM read_parquet(
        '{sql_path(TRECHO)}'
    )
    """
)


# 12. MANIFESTO GOLD

print("\n" + "=" * 72)
print("12. GERANDO MANIFESTO GOLD")
print("=" * 72)


ARQUIVOS_GOLD = [
    "dim_processo",
    "dim_tipo_pagamento",
    "dim_modal",
    "dim_organizacao",
    "dim_localidade",
    "dim_data",
    "bridge_processo_viajante",
    "fato_processo_viagem",
    "fato_pagamento",
    "fato_passagem",
    "fato_trecho",
]


linhas_manifesto = []

for nome in ARQUIVOS_GOLD:

    arquivo = caminho_gold(nome)

    total = con.execute(
        f"""
        SELECT COUNT(*)
        FROM read_parquet(
            '{sql_path(arquivo)}'
        )
        """
    ).fetchone()[0]

    colunas = con.execute(
        f"""
        DESCRIBE
        SELECT *
        FROM read_parquet(
            '{sql_path(arquivo)}'
        )
        """
    ).fetchall()

    linhas_manifesto.append([
        nome,
        total,
        len(colunas),
        arquivo.stat().st_size
    ])


manifesto = (
    PASTA_METADATA /
    "01_manifesto_gold.csv"
)

with manifesto.open(
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
        "registros",
        "colunas",
        "tamanho_bytes"
    ])

    writer.writerows(
        linhas_manifesto
    )

print(
    f"✓ {manifesto.name}"
)


# 13. VALIDAÇÕES RÁPIDAS

print("\n" + "=" * 72)
print("13. VALIDAÇÕES RÁPIDAS")
print("=" * 72)


problemas = []


qtd_processos_silver = con.execute(
    f"""
    SELECT COUNT(
        DISTINCT sk_processo
    )
    FROM read_parquet(
        '{sql_path(VIAGEM)}'
    )
    """
).fetchone()[0]


qtd_dim_processo = con.execute(
    f"""
    SELECT COUNT(*)
    FROM read_parquet(
        '{sql_path(caminho_gold("dim_processo"))}'
    )
    """
).fetchone()[0]


qtd_fato_processo = con.execute(
    f"""
    SELECT COUNT(*)
    FROM read_parquet(
        '{sql_path(caminho_gold("fato_processo_viagem"))}'
    )
    """
).fetchone()[0]


print(
    "Processos distintos Silver:",
    f"{qtd_processos_silver:,}"
)

print(
    "DimProcesso:",
    f"{qtd_dim_processo:,}"
)

print(
    "FatoProcessoViagem:",
    f"{qtd_fato_processo:,}"
)


if qtd_dim_processo != qtd_processos_silver:
    problemas.append(
        "DimProcesso não possui "
        "uma linha por processo."
    )


if qtd_fato_processo != qtd_processos_silver:
    problemas.append(
        "FatoProcessoViagem não possui "
        "uma linha por processo."
    )


checks_contagem = [
    (
        "Pagamento",
        PAGAMENTO,
        caminho_gold(
            "fato_pagamento"
        )
    ),
    (
        "Passagem",
        PASSAGEM,
        caminho_gold(
            "fato_passagem"
        )
    ),
    (
        "Trecho",
        TRECHO,
        caminho_gold(
            "fato_trecho"
        )
    ),
]


for nome, silver, gold in checks_contagem:

    qtd_silver = con.execute(
        f"""
        SELECT COUNT(*)
        FROM read_parquet(
            '{sql_path(silver)}'
        )
        """
    ).fetchone()[0]

    qtd_gold = con.execute(
        f"""
        SELECT COUNT(*)
        FROM read_parquet(
            '{sql_path(gold)}'
        )
        """
    ).fetchone()[0]

    print(
        f"{nome}: "
        f"Silver={qtd_silver:,} | "
        f"Gold={qtd_gold:,}"
    )

    if qtd_silver != qtd_gold:
        problemas.append(
            f"Contagem divergente em {nome}."
        )


for fato in [
    "fato_pagamento",
    "fato_passagem",
    "fato_trecho"
]:

    orfaos = con.execute(
        f"""
        SELECT COUNT(*)

        FROM read_parquet(
            '{sql_path(caminho_gold(fato))}'
        )
            f

        LEFT JOIN read_parquet(
            '{sql_path(caminho_gold("dim_processo"))}'
        )
            d

            ON f.sk_processo
             = d.sk_processo

        WHERE d.sk_processo
            IS NULL
        """
    ).fetchone()[0]

    print(
        f"Órfãos {fato}: "
        f"{orfaos:,}"
    )

    if orfaos != 0:
        problemas.append(
            f"{fato} possui "
            f"{orfaos} processos órfãos."
        )


# ENCERRAMENTO

con.close()


print("\n" + "=" * 72)

if problemas:

    print(
        "CAMADA GOLD CONSTRUÍDA, "
        "MAS HÁ PROBLEMAS DE VALIDAÇÃO"
    )

    print("=" * 72)

    for problema in problemas:
        print(
            f"⚠ {problema}"
        )

    raise RuntimeError(
        "A Gold requer revisão "
        "antes de prosseguir."
    )

else:

    print(
        "CAMADA GOLD CONSTRUÍDA "
        "E VALIDAÇÕES BÁSICAS: OK"
    )

    print("=" * 72)

    print(
        "\nArquivos disponíveis em:"
    )

    print(
        PASTA_GOLD
    )