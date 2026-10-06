import os
from pathlib import Path
import csv
import duckdb


# CONFIGURAÇÃO

PROJECT_DIR = Path(__file__).resolve().parent

DEFAULT_DATA_ROOT = PROJECT_DIR / "data"

PASTA_DADOS = Path(
    os.getenv(
        "PI_DATA_ROOT",
        str(DEFAULT_DATA_ROOT)
    )
).expanduser().resolve()

PASTA_GOLD = PASTA_DADOS / "gold"
PASTA_MARTS = PASTA_GOLD / "marts"
PASTA_METADATA = PASTA_MARTS / "_metadata"
PASTA_TEMP = PASTA_GOLD / "_duckdb_temp"

PASTA_MARTS.mkdir(parents=True, exist_ok=True)
PASTA_METADATA.mkdir(parents=True, exist_ok=True)
PASTA_TEMP.mkdir(parents=True, exist_ok=True)


DIM_PROCESSO = PASTA_GOLD / "dim_processo.parquet"
DIM_DATA = PASTA_GOLD / "dim_data.parquet"
DIM_ORG = PASTA_GOLD / "dim_organizacao.parquet"
DIM_LOCAL = PASTA_GOLD / "dim_localidade.parquet"
DIM_MODAL = PASTA_GOLD / "dim_modal.parquet"
DIM_TIPO_PAG = PASTA_GOLD / "dim_tipo_pagamento.parquet"

FATO_PROCESSO = (
    PASTA_GOLD /
    "fato_processo_viagem.parquet"
)

FATO_PAGAMENTO = (
    PASTA_GOLD /
    "fato_pagamento.parquet"
)

FATO_PASSAGEM = (
    PASTA_GOLD /
    "fato_passagem.parquet"
)

FATO_TRECHO = (
    PASTA_GOLD /
    "fato_trecho.parquet"
)


MART_EXECUTIVO = (
    PASTA_MARTS /
    "mart_executivo_anual.parquet"
)

MART_GASTOS = (
    PASTA_MARTS /
    "mart_gastos_categoria.parquet"
)

MART_ANTECEDENCIA = (
    PASTA_MARTS /
    "mart_antecedencia.parquet"
)

MART_ANTECEDENCIA_DETALHE = (
    PASTA_MARTS /
    "mart_antecedencia_detalhe.parquet"
)

MART_ORGAOS = (
    PASTA_MARTS /
    "mart_orgaos.parquet"
)

MART_ROTAS = (
    PASTA_MARTS /
    "mart_rotas.parquet"
)

MART_MODAIS = (
    PASTA_MARTS /
    "mart_modais.parquet"
)

MART_QUALIDADE = (
    PASTA_MARTS /
    "mart_qualidade_dados.parquet"
)


ANOS_SQL = "(2022, 2023, 2024, 2025)"


# FUNÇÕES AUXILIARES

def sql_path(path: Path) -> str:

    return (
        path
        .as_posix()
        .replace("'", "''")
    )


def remover_se_existir(path: Path):

    if path.exists():
        path.unlink()


def copy_parquet(
    con,
    destino,
    sql
):

    remover_se_existir(
        destino
    )

    print(
        f"\nConstruindo: "
        f"{destino.name}"
    )

    con.execute(
        f"""
        COPY (
            {sql}
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
        f"✓ {destino.name}: "
        f"{total:,} registros"
    )

    return total


def salvar_csv(
    nome,
    cabecalho,
    linhas
):

    destino = (
        PASTA_METADATA /
        nome
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

        writer.writerow(
            cabecalho
        )

        writer.writerows(
            linhas
        )

    print(
        f"✓ {nome}"
    )


# CONEXÃO

con = duckdb.connect()

con.execute(
    "SET threads = 2"
)

con.execute(
    "SET preserve_insertion_order = false"
)

con.execute(
    "SET memory_limit = '8GB'"
)

con.execute(
    f"""
    SET temp_directory =
    '{sql_path(PASTA_TEMP)}'
    """
)


# PRÉ-REQUISITOS

print(
    "=" * 76
)

print(
    "CONSTRUÇÃO DOS ANALYTICS MARTS"
)

print(
    "=" * 76
)


arquivos_necessarios = [
    DIM_PROCESSO,
    DIM_DATA,
    DIM_ORG,
    DIM_LOCAL,
    DIM_MODAL,
    DIM_TIPO_PAG,
    FATO_PROCESSO,
    FATO_PAGAMENTO,
    FATO_PASSAGEM,
    FATO_TRECHO,
]


for arquivo in arquivos_necessarios:

    if not arquivo.exists():

        raise FileNotFoundError(
            f"Arquivo necessário "
            f"não encontrado: {arquivo}"
        )


print(
    "✓ Pré-requisitos encontrados"
)


# 1. MART EXECUTIVO ANUAL

print(
    "\n" + "=" * 76
)

print(
    "1. MART EXECUTIVO ANUAL"
)

print(
    "=" * 76
)


SQL_EXECUTIVO = f"""

WITH processos AS (

    SELECT
        ano_fonte,

        COUNT(*)
            AS qtd_processos,

        COUNT(*) FILTER (
            WHERE situacao_processo
                = 'REALIZADA'
        )
            AS qtd_processos_realizados,

        COUNT(*) FILTER (
            WHERE situacao_processo
                = 'NÃO REALIZADA'
        )
            AS qtd_processos_nao_realizados,

        COUNT(*) FILTER (
            WHERE viagem_urgente_flag
                = TRUE
        )
            AS qtd_processos_urgentes,

        COUNT(*) FILTER (
            WHERE viagem_urgente_flag
                = FALSE
        )
            AS qtd_processos_nao_urgentes,

        COUNT(*) FILTER (
            WHERE viagem_urgente_flag
                IS NULL
        )
            AS qtd_urgencia_indeterminada,

        COUNT(*) FILTER (
            WHERE flag_processo_repetido_fonte
                = TRUE
        )
            AS qtd_processos_repetidos_fonte,

        COUNT(*) FILTER (
            WHERE flag_financeiro_multivalorado
                = TRUE
        )
            AS qtd_processos_financeiro_multivalorado,

        COUNT(*) FILTER (
            WHERE qtd_viajantes_identificados = 0
        )
            AS qtd_processos_sem_viajante_identificado

    FROM read_parquet(
        '{sql_path(FATO_PROCESSO)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY ano_fonte
),


pagamentos AS (

    SELECT
        ano_fonte,

        COUNT(*)
            AS qtd_registros_pagamento,

        COUNT(
            DISTINCT sk_processo
        )
            AS qtd_processos_com_pagamento,

        SUM(valor)
            AS valor_total_pagamentos,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'DIARIAS'
        )
            AS valor_pago_diarias,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'PASSAGEM'
        )
            AS valor_pago_passagens,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'RESTITUICAO'
        )
            AS valor_restituicoes,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'SEGURO'
        )
            AS valor_seguro

    FROM read_parquet(
        '{sql_path(FATO_PAGAMENTO)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY ano_fonte
),


passagens AS (

    SELECT
        ano_fonte,

        COUNT(*)
            AS qtd_registros_passagem_detalhada,

        COUNT(
            DISTINCT sk_processo
        )
            AS qtd_processos_passagem_detalhada,

        SUM(valor_passagem)
            AS valor_tarifas_detalhadas,

        SUM(taxa_servico)
            AS valor_taxas_servico,

        SUM(custo_total_passagem)
            AS custo_passagens_detalhadas,

        COUNT(*) FILTER (
            WHERE antecedencia_dias >= 0
        )
            AS qtd_antecedencia_valida,

        COUNT(*) FILTER (
            WHERE antecedencia_dias
                BETWEEN 0 AND 7
        )
            AS qtd_emissoes_ate_7_dias,

        COUNT(*) FILTER (
            WHERE antecedencia_dias < 0
        )
            AS qtd_emissoes_apos_inicio,

        COUNT(*) FILTER (
            WHERE antecedencia_dias
                IS NULL
        )
            AS qtd_sem_antecedencia,

        MEDIAN(
            antecedencia_dias
        ) FILTER (
            WHERE antecedencia_dias >= 0
        )
            AS antecedencia_mediana_dias,

        AVG(
            antecedencia_dias
        ) FILTER (
            WHERE antecedencia_dias >= 0
        )
            AS antecedencia_media_dias,

        AVG(
            custo_total_passagem
        ) FILTER (
            WHERE antecedencia_dias >= 0
        )
            AS custo_medio_passagem_valida,

        MEDIAN(
            custo_total_passagem
        ) FILTER (
            WHERE antecedencia_dias >= 0
        )
            AS custo_mediano_passagem_valida

    FROM read_parquet(
        '{sql_path(FATO_PASSAGEM)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY ano_fonte
),


base AS (

    SELECT
        pr.*,

        pg.qtd_registros_pagamento,
        pg.qtd_processos_com_pagamento,
        pg.valor_total_pagamentos,
        pg.valor_pago_diarias,
        pg.valor_pago_passagens,
        pg.valor_restituicoes,
        pg.valor_seguro,

        ps.qtd_registros_passagem_detalhada,
        ps.qtd_processos_passagem_detalhada,

        ps.valor_tarifas_detalhadas,
        ps.valor_taxas_servico,
        ps.custo_passagens_detalhadas,

        ps.qtd_antecedencia_valida,
        ps.qtd_emissoes_ate_7_dias,
        ps.qtd_emissoes_apos_inicio,
        ps.qtd_sem_antecedencia,

        ps.antecedencia_mediana_dias,
        ps.antecedencia_media_dias,

        ps.custo_medio_passagem_valida,
        ps.custo_mediano_passagem_valida,

        100.0
        * pr.qtd_processos_urgentes
        / NULLIF(
            pr.qtd_processos,
            0
        )
            AS pct_processos_urgentes,

        pg.valor_total_pagamentos
        / NULLIF(
            pg.qtd_processos_com_pagamento,
            0
        )
            AS valor_medio_pago_por_processo_com_pagamento,

        100.0
        * ps.custo_passagens_detalhadas
        / NULLIF(
            pg.valor_pago_passagens,
            0
        )
            AS pct_cobertura_valor_passagem_detalhada,

        100.0
        * ps.qtd_emissoes_ate_7_dias
        / NULLIF(
            ps.qtd_antecedencia_valida,
            0
        )
            AS pct_emissoes_ate_7_dias,

        100.0
        * ps.qtd_emissoes_apos_inicio
        / NULLIF(
            ps.qtd_registros_passagem_detalhada,
            0
        )
            AS pct_emissoes_apos_inicio,

        100.0
        * ps.qtd_sem_antecedencia
        / NULLIF(
            ps.qtd_registros_passagem_detalhada,
            0
        )
            AS pct_sem_antecedencia

    FROM processos pr

    LEFT JOIN pagamentos pg
        USING (ano_fonte)

    LEFT JOIN passagens ps
        USING (ano_fonte)
),


final AS (

    SELECT
        *,

        100.0
        * (
            qtd_processos
            -
            LAG(qtd_processos)
            OVER (
                ORDER BY ano_fonte
            )
        )
        /
        NULLIF(
            LAG(qtd_processos)
            OVER (
                ORDER BY ano_fonte
            ),
            0
        )
            AS variacao_yoy_processos_pct,

        100.0
        * (
            valor_total_pagamentos
            -
            LAG(
                valor_total_pagamentos
            )
            OVER (
                ORDER BY ano_fonte
            )
        )
        /
        NULLIF(
            LAG(
                valor_total_pagamentos
            )
            OVER (
                ORDER BY ano_fonte
            ),
            0
        )
            AS variacao_yoy_pagamentos_pct

    FROM base
)

SELECT *

FROM final

ORDER BY ano_fonte
"""


copy_parquet(
    con,
    MART_EXECUTIVO,
    SQL_EXECUTIVO
)


# 2. MART GASTOS POR CATEGORIA

print(
    "\n" + "=" * 76
)

print(
    "2. MART GASTOS POR CATEGORIA"
)

print(
    "=" * 76
)


SQL_GASTOS = f"""

WITH base AS (

    SELECT
        p.ano_fonte,

        p.sk_tipo_pagamento,

        p.tipo_pagamento_normalizado
            AS codigo_tipo_pagamento,

        d.descricao_tipo_pagamento,

        COUNT(*)
            AS qtd_registros_pagamento,

        COUNT(
            DISTINCT p.sk_processo
        )
            AS qtd_processos,

        SUM(p.valor)
            AS valor_total,

        AVG(p.valor)
            AS valor_medio_registro,

        MEDIAN(p.valor)
            AS valor_mediano_registro

    FROM read_parquet(
        '{sql_path(FATO_PAGAMENTO)}'
    ) p

    LEFT JOIN read_parquet(
        '{sql_path(DIM_TIPO_PAG)}'
    ) d

        ON p.sk_tipo_pagamento
         = d.sk_tipo_pagamento

    WHERE p.ano_fonte IN {ANOS_SQL}

    GROUP BY
        p.ano_fonte,
        p.sk_tipo_pagamento,
        p.tipo_pagamento_normalizado,
        d.descricao_tipo_pagamento
),


totais AS (

    SELECT
        ano_fonte,

        SUM(valor_total)
            AS valor_total_ano

    FROM base

    GROUP BY ano_fonte
)


SELECT
    b.*,

    100.0
    * b.valor_total
    / NULLIF(
        t.valor_total_ano,
        0
    )
        AS pct_valor_total_ano,

    100.0
    * (
        b.valor_total
        -
        LAG(
            b.valor_total
        )
        OVER (
            PARTITION BY
                b.codigo_tipo_pagamento

            ORDER BY
                b.ano_fonte
        )
    )
    /
    NULLIF(
        LAG(
            b.valor_total
        )
        OVER (
            PARTITION BY
                b.codigo_tipo_pagamento

            ORDER BY
                b.ano_fonte
        ),
        0
    )
        AS variacao_yoy_categoria_pct

FROM base b

LEFT JOIN totais t
    USING (ano_fonte)

ORDER BY
    b.ano_fonte,
    b.codigo_tipo_pagamento
"""


copy_parquet(
    con,
    MART_GASTOS,
    SQL_GASTOS
)


# 3. MART ANTECEDÊNCIA

print(
    "\n" + "=" * 76
)

print(
    "3. MART ANTECEDÊNCIA"
)

print(
    "=" * 76
)


SQL_ANTECEDENCIA = f"""

WITH base AS (

    SELECT
        p.ano_fonte,

        p.faixa_antecedencia,

        CASE
            WHEN p.faixa_antecedencia
                = 'EMISSAO_APOS_INICIO'
            THEN 0

            WHEN p.faixa_antecedencia
                = '0_A_3_DIAS'
            THEN 1

            WHEN p.faixa_antecedencia
                = '4_A_7_DIAS'
            THEN 2

            WHEN p.faixa_antecedencia
                = '8_A_14_DIAS'
            THEN 3

            WHEN p.faixa_antecedencia
                = '15_A_30_DIAS'
            THEN 4

            WHEN p.faixa_antecedencia
                = 'MAIS_DE_30_DIAS'
            THEN 5

            WHEN p.faixa_antecedencia
                = 'SEM_INFORMACAO'
            THEN 6

            ELSE 99
        END
            AS ordem_faixa,

        CASE
            WHEN fp.viagem_urgente_flag
                = TRUE
            THEN 'URGENTE'

            WHEN fp.viagem_urgente_flag
                = FALSE
            THEN 'NAO_URGENTE'

            ELSE 'INDETERMINADA'
        END
            AS categoria_urgencia,

        p.sk_modal,

        p.meio_transporte_normalizado
            AS modal,

        p.sk_processo,

        p.valor_passagem,

        p.taxa_servico,

        p.custo_total_passagem,

        p.antecedencia_dias

    FROM read_parquet(
        '{sql_path(FATO_PASSAGEM)}'
    ) p

    LEFT JOIN read_parquet(
        '{sql_path(FATO_PROCESSO)}'
    ) fp

        ON p.sk_processo
         = fp.sk_processo

    WHERE p.ano_fonte IN {ANOS_SQL}
)


SELECT
    ano_fonte,

    faixa_antecedencia,

    ordem_faixa,

    categoria_urgencia,

    sk_modal,

    modal,

    COUNT(*)
        AS qtd_registros_passagem,

    COUNT(
        DISTINCT sk_processo
    )
        AS qtd_processos,

    SUM(valor_passagem)
        AS valor_tarifas,

    SUM(taxa_servico)
        AS valor_taxas_servico,

    SUM(custo_total_passagem)
        AS custo_total_passagens,

    AVG(custo_total_passagem)
        AS custo_medio_passagem,

    MEDIAN(custo_total_passagem)
        AS custo_mediano_passagem,

    AVG(antecedencia_dias)
        AS antecedencia_media_dias,

    MEDIAN(antecedencia_dias)
        AS antecedencia_mediana_dias

FROM base

GROUP BY
    ano_fonte,
    faixa_antecedencia,
    ordem_faixa,
    categoria_urgencia,
    sk_modal,
    modal

ORDER BY
    ano_fonte,
    ordem_faixa,
    categoria_urgencia,
    modal
"""


copy_parquet(
    con,
    MART_ANTECEDENCIA,
    SQL_ANTECEDENCIA
)


# 3B. MART ANTECEDÊNCIA - DETALHE PARA CONSUMO ANALÍTICO

print(
    "\n" + "=" * 76
)

print(
    "3B. MART ANTECEDÊNCIA - DETALHE"
)

print(
    "=" * 76
)


SQL_ANTECEDENCIA_DETALHE = f"""
SELECT
    p.ano_fonte,

    p.sk_processo,

    p.meio_transporte_normalizado
        AS modal,

    p.faixa_antecedencia,

    p.antecedencia_dias,

    p.custo_total_passagem,

    CASE
        WHEN fp.viagem_urgente_flag = TRUE
        THEN 'URGENTE'

        WHEN fp.viagem_urgente_flag = FALSE
        THEN 'NAO_URGENTE'

        ELSE 'INDETERMINADA'
    END
        AS categoria_urgencia

FROM read_parquet(
    '{sql_path(FATO_PASSAGEM)}'
) p

LEFT JOIN read_parquet(
    '{sql_path(FATO_PROCESSO)}'
) fp

    ON p.sk_processo
     = fp.sk_processo

WHERE p.ano_fonte IN {ANOS_SQL}
"""


copy_parquet(
    con,
    MART_ANTECEDENCIA_DETALHE,
    SQL_ANTECEDENCIA_DETALHE
)


# 4. MART ORGANIZAÇÕES

print(
    "\n" + "=" * 76
)

print(
    "4. MART ORGANIZAÇÕES"
)

print(
    "=" * 76
)


SQL_ORGAOS = f"""

WITH org_superior AS (

    SELECT
        ano_fonte,

        'ORGAO_SUPERIOR_FINANCEIRO'
            AS perspectiva,

        sk_orgao_superior
            AS sk_organizacao,

        COUNT(*)
            AS qtd_registros,

        COUNT(
            DISTINCT sk_processo
        )
            AS qtd_processos,

        SUM(valor)
            AS valor_total,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'DIARIAS'
        )
            AS valor_diarias,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'PASSAGEM'
        )
            AS valor_passagens,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'RESTITUICAO'
        )
            AS valor_restituicao,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'SEGURO'
        )
            AS valor_seguro,

        CAST(
            NULL AS BIGINT
        )
            AS qtd_processos_urgentes

    FROM read_parquet(
        '{sql_path(FATO_PAGAMENTO)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY
        ano_fonte,
        sk_orgao_superior
),


org_pagador AS (

    SELECT
        ano_fonte,

        'ORGAO_PAGADOR_FINANCEIRO'
            AS perspectiva,

        sk_orgao_pagador
            AS sk_organizacao,

        COUNT(*)
            AS qtd_registros,

        COUNT(
            DISTINCT sk_processo
        )
            AS qtd_processos,

        SUM(valor)
            AS valor_total,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'DIARIAS'
        )
            AS valor_diarias,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'PASSAGEM'
        )
            AS valor_passagens,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'RESTITUICAO'
        )
            AS valor_restituicao,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'SEGURO'
        )
            AS valor_seguro,

        CAST(
            NULL AS BIGINT
        )
            AS qtd_processos_urgentes

    FROM read_parquet(
        '{sql_path(FATO_PAGAMENTO)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY
        ano_fonte,
        sk_orgao_pagador
),


unidade_gestora AS (

    SELECT
        ano_fonte,

        'UNIDADE_GESTORA_PAGADORA_FINANCEIRO'
            AS perspectiva,

        sk_unidade_gestora_pagadora
            AS sk_organizacao,

        COUNT(*)
            AS qtd_registros,

        COUNT(
            DISTINCT sk_processo
        )
            AS qtd_processos,

        SUM(valor)
            AS valor_total,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'DIARIAS'
        )
            AS valor_diarias,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'PASSAGEM'
        )
            AS valor_passagens,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'RESTITUICAO'
        )
            AS valor_restituicao,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'SEGURO'
        )
            AS valor_seguro,

        CAST(
            NULL AS BIGINT
        )
            AS qtd_processos_urgentes

    FROM read_parquet(
        '{sql_path(FATO_PAGAMENTO)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY
        ano_fonte,
        sk_unidade_gestora_pagadora
),


org_solicitante AS (

    SELECT
        ano_fonte,

        'ORGAO_SOLICITANTE_OPERACIONAL'
            AS perspectiva,

        sk_orgao_solicitante
            AS sk_organizacao,

        COUNT(*)
            AS qtd_registros,

        COUNT(*)
            AS qtd_processos,

        CAST(
            NULL AS DECIMAL(38,2)
        )
            AS valor_total,

        CAST(
            NULL AS DECIMAL(38,2)
        )
            AS valor_diarias,

        CAST(
            NULL AS DECIMAL(38,2)
        )
            AS valor_passagens,

        CAST(
            NULL AS DECIMAL(38,2)
        )
            AS valor_restituicao,

        CAST(
            NULL AS DECIMAL(38,2)
        )
            AS valor_seguro,

        COUNT(*) FILTER (
            WHERE viagem_urgente_flag
                = TRUE
        )
            AS qtd_processos_urgentes

    FROM read_parquet(
        '{sql_path(FATO_PROCESSO)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY
        ano_fonte,
        sk_orgao_solicitante
),


uniao AS (

    SELECT * FROM org_superior

    UNION ALL

    SELECT * FROM org_pagador

    UNION ALL

    SELECT * FROM unidade_gestora

    UNION ALL

    SELECT * FROM org_solicitante
)


SELECT
    u.ano_fonte,

    u.perspectiva,

    u.sk_organizacao,

    d.tipo_organizacao,

    d.codigo
        AS codigo_organizacao,

    d.nome
        AS nome_organizacao,

    u.qtd_registros,

    u.qtd_processos,

    u.qtd_processos_urgentes,

    CASE
        WHEN u.qtd_processos_urgentes
            IS NULL
        THEN NULL

        ELSE
            100.0
            * u.qtd_processos_urgentes
            / NULLIF(
                u.qtd_processos,
                0
            )
    END
        AS pct_processos_urgentes,

    u.valor_total,

    u.valor_diarias,

    u.valor_passagens,

    u.valor_restituicao,

    u.valor_seguro

FROM uniao u

LEFT JOIN read_parquet(
    '{sql_path(DIM_ORG)}'
) d

    ON u.sk_organizacao
     = d.sk_organizacao

ORDER BY
    u.ano_fonte,
    u.perspectiva,
    u.valor_total DESC NULLS LAST,
    u.qtd_processos DESC
"""


copy_parquet(
    con,
    MART_ORGAOS,
    SQL_ORGAOS
)


# 5. MART ROTAS

print(
    "\n" + "=" * 76
)

print(
    "5. MART ROTAS"
)

print(
    "=" * 76
)


SQL_ROTAS = f"""

WITH agregado AS (

    SELECT
        ano_fonte,

        sk_localidade_origem,

        sk_localidade_destino,

        sk_modal,

        COUNT(*)
            AS qtd_trechos,

        COUNT(
            DISTINCT sk_processo
        )
            AS qtd_processos,

        AVG(numero_diarias)
            AS media_numero_diarias,

        SUM(numero_diarias)
            AS soma_numero_diarias

    FROM read_parquet(
        '{sql_path(FATO_TRECHO)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY
        ano_fonte,
        sk_localidade_origem,
        sk_localidade_destino,
        sk_modal
)


SELECT
    a.ano_fonte,

    a.sk_localidade_origem,

    lo.pais
        AS origem_pais,

    lo.uf
        AS origem_uf,

    lo.cidade
        AS origem_cidade,

    a.sk_localidade_destino,

    ld.pais
        AS destino_pais,

    ld.uf
        AS destino_uf,

    ld.cidade
        AS destino_cidade,

    a.sk_modal,

    m.modal,

    m.flag_modal_valido,

    a.qtd_trechos,

    a.qtd_processos,

    a.media_numero_diarias,

    a.soma_numero_diarias

FROM agregado a

LEFT JOIN read_parquet(
    '{sql_path(DIM_LOCAL)}'
) lo

    ON a.sk_localidade_origem
     = lo.sk_localidade

LEFT JOIN read_parquet(
    '{sql_path(DIM_LOCAL)}'
) ld

    ON a.sk_localidade_destino
     = ld.sk_localidade

LEFT JOIN read_parquet(
    '{sql_path(DIM_MODAL)}'
) m

    ON a.sk_modal
     = m.sk_modal

ORDER BY
    a.ano_fonte,
    a.qtd_trechos DESC
"""


copy_parquet(
    con,
    MART_ROTAS,
    SQL_ROTAS
)


# 6. MART MODAIS

print(
    "\n" + "=" * 76
)

print(
    "6. MART MODAIS"
)

print(
    "=" * 76
)


SQL_MODAIS = f"""

WITH trechos AS (

    SELECT
        ano_fonte,

        sk_modal,

        meio_transporte_normalizado
            AS modal,

        COUNT(*)
            AS qtd_trechos,

        COUNT(
            DISTINCT sk_processo
        )
            AS qtd_processos_trecho

    FROM read_parquet(
        '{sql_path(FATO_TRECHO)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY
        ano_fonte,
        sk_modal,
        meio_transporte_normalizado
),


passagens AS (

    SELECT
        ano_fonte,

        sk_modal,

        meio_transporte_normalizado
            AS modal,

        COUNT(*)
            AS qtd_registros_passagem,

        COUNT(
            DISTINCT sk_processo
        )
            AS qtd_processos_passagem,

        SUM(valor_passagem)
            AS valor_tarifas,

        SUM(taxa_servico)
            AS valor_taxas_servico,

        SUM(custo_total_passagem)
            AS custo_total_passagens,

        AVG(custo_total_passagem)
            AS custo_medio_passagem,

        MEDIAN(custo_total_passagem)
            AS custo_mediano_passagem

    FROM read_parquet(
        '{sql_path(FATO_PASSAGEM)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY
        ano_fonte,
        sk_modal,
        meio_transporte_normalizado
),


base AS (

    SELECT
        COALESCE(
            t.ano_fonte,
            p.ano_fonte
        )
            AS ano_fonte,

        COALESCE(
            t.sk_modal,
            p.sk_modal
        )
            AS sk_modal,

        COALESCE(
            t.modal,
            p.modal
        )
            AS modal,

        COALESCE(
            t.qtd_trechos,
            0
        )
            AS qtd_trechos,

        COALESCE(
            t.qtd_processos_trecho,
            0
        )
            AS qtd_processos_trecho,

        COALESCE(
            p.qtd_registros_passagem,
            0
        )
            AS qtd_registros_passagem,

        COALESCE(
            p.qtd_processos_passagem,
            0
        )
            AS qtd_processos_passagem,

        p.valor_tarifas,

        p.valor_taxas_servico,

        p.custo_total_passagens,

        p.custo_medio_passagem,

        p.custo_mediano_passagem

    FROM trechos t

    FULL OUTER JOIN passagens p

        ON t.ano_fonte
         = p.ano_fonte

       AND t.sk_modal
         = p.sk_modal
)


SELECT
    b.*,

    d.flag_modal_valido,

    d.flag_presente_trecho,

    d.flag_presente_passagem

FROM base b

LEFT JOIN read_parquet(
    '{sql_path(DIM_MODAL)}'
) d

    ON b.sk_modal
     = d.sk_modal

ORDER BY
    b.ano_fonte,
    b.qtd_trechos DESC,
    b.qtd_registros_passagem DESC
"""


copy_parquet(
    con,
    MART_MODAIS,
    SQL_MODAIS
)


# 7. MART QUALIDADE DOS DADOS

print(
    "\n" + "=" * 76
)

print(
    "7. MART QUALIDADE DOS DADOS"
)

print(
    "=" * 76
)


SQL_QUALIDADE = f"""

WITH proc AS (

    SELECT
        ano_fonte,

        COUNT(*)
            AS processos,

        COUNT(*) FILTER (
            WHERE flag_processo_repetido_fonte
                = TRUE
        )
            AS processos_repetidos,

        COUNT(*) FILTER (
            WHERE flag_financeiro_multivalorado
                = TRUE
        )
            AS processos_financeiro_multivalorado,

        COUNT(*) FILTER (
            WHERE sk_data_inicio IS NULL
        )
            AS processos_sem_data_inicio,

        COUNT(*) FILTER (
            WHERE sk_data_fim IS NULL
        )
            AS processos_sem_data_fim,

        COUNT(*) FILTER (
            WHERE qtd_viajantes_identificados = 0
        )
            AS processos_sem_viajante

    FROM read_parquet(
        '{sql_path(FATO_PROCESSO)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY ano_fonte
),


pass AS (

    SELECT
        ano_fonte,

        COUNT(*)
            AS registros_passagem,

        COUNT(*) FILTER (
            WHERE data_emissao IS NULL
        )
            AS passagem_sem_data_emissao,

        COUNT(*) FILTER (
            WHERE antecedencia_dias < 0
        )
            AS passagem_emissao_apos_inicio,

        COUNT(*)
        -
        COUNT(
            DISTINCT hash_observacao
        )
            AS repeticoes_exatas_passagem,

        SUM(custo_total_passagem)
            AS custo_passagem_detalhada

    FROM read_parquet(
        '{sql_path(FATO_PASSAGEM)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY ano_fonte
),


pag AS (

    SELECT
        ano_fonte,

        COUNT(*)
            AS registros_pagamento,

        COUNT(*)
        -
        COUNT(
            DISTINCT hash_observacao
        )
            AS repeticoes_exatas_pagamento,

        SUM(valor) FILTER (
            WHERE tipo_pagamento_normalizado
                = 'PASSAGEM'
        )
            AS valor_pagamento_passagem

    FROM read_parquet(
        '{sql_path(FATO_PAGAMENTO)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY ano_fonte
),


tre AS (

    SELECT
        ano_fonte,

        COUNT(*)
            AS registros_trecho,

        COUNT(*) FILTER (
            WHERE flag_modal_invalido
                = TRUE
        )
            AS trecho_modal_invalido,

        COUNT(*)
        -
        COUNT(
            DISTINCT hash_observacao
        )
            AS repeticoes_exatas_trecho

    FROM read_parquet(
        '{sql_path(FATO_TRECHO)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

    GROUP BY ano_fonte
),


pass_proc AS (

    SELECT DISTINCT
        ano_fonte,
        sk_processo

    FROM read_parquet(
        '{sql_path(FATO_PASSAGEM)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}
),


pag_pass_proc AS (

    SELECT DISTINCT
        ano_fonte,
        sk_processo

    FROM read_parquet(
        '{sql_path(FATO_PAGAMENTO)}'
    )

    WHERE ano_fonte IN {ANOS_SQL}

      AND tipo_pagamento_normalizado
            = 'PASSAGEM'
),


cobertura_proc AS (

    SELECT
        pg.ano_fonte,

        COUNT(*)
            AS processos_pagamento_passagem,

        COUNT(*) FILTER (
            WHERE ps.sk_processo
                IS NOT NULL
        )
            AS processos_com_detalhamento

    FROM pag_pass_proc pg

    LEFT JOIN pass_proc ps

        ON pg.ano_fonte
         = ps.ano_fonte

       AND pg.sk_processo
         = ps.sk_processo

    GROUP BY pg.ano_fonte
),


base AS (

    SELECT
        pr.ano_fonte,

        pr.processos,

        pr.processos_repetidos,

        pr.processos_financeiro_multivalorado,

        pr.processos_sem_data_inicio,

        pr.processos_sem_data_fim,

        pr.processos_sem_viajante,

        ps.registros_passagem,

        ps.passagem_sem_data_emissao,

        ps.passagem_emissao_apos_inicio,

        ps.repeticoes_exatas_passagem,

        ps.custo_passagem_detalhada,

        pg.registros_pagamento,

        pg.repeticoes_exatas_pagamento,

        pg.valor_pagamento_passagem,

        tr.registros_trecho,

        tr.trecho_modal_invalido,

        tr.repeticoes_exatas_trecho,

        cp.processos_pagamento_passagem,

        cp.processos_com_detalhamento

    FROM proc pr

    LEFT JOIN pass ps
        USING (ano_fonte)

    LEFT JOIN pag pg
        USING (ano_fonte)

    LEFT JOIN tre tr
        USING (ano_fonte)

    LEFT JOIN cobertura_proc cp
        USING (ano_fonte)
)


SELECT
    ano_fonte,

    indicador,

    categoria,

    numerador,

    denominador,

    CASE
        WHEN denominador IS NULL
          OR denominador = 0
        THEN NULL

        ELSE
            100.0
            * numerador
            / denominador
    END
        AS percentual,

    observacao

FROM (

    SELECT
        ano_fonte,

        'PROCESSO_REPETIDO_FONTE'
            AS indicador,

        'ESTRUTURA'
            AS categoria,

        CAST(
            processos_repetidos
            AS DOUBLE
        )
            AS numerador,

        CAST(
            processos
            AS DOUBLE
        )
            AS denominador,

        'Processos com mais de uma linha na fonte Viagem.'
            AS observacao

    FROM base


    UNION ALL


    SELECT
        ano_fonte,

        'PROCESSO_FINANCEIRO_MULTIVALORADO',

        'ESTRUTURA',

        CAST(
            processos_financeiro_multivalorado
            AS DOUBLE
        ),

        CAST(
            processos
            AS DOUBLE
        ),

        'Mais de um valor possível em campo financeiro de Viagem.'

    FROM base


    UNION ALL


    SELECT
        ano_fonte,

        'PROCESSO_SEM_DATA_INICIO_CONSOLIDADA',

        'COMPLETUDE',

        CAST(
            processos_sem_data_inicio
            AS DOUBLE
        ),

        CAST(
            processos
            AS DOUBLE
        ),

        'Pode representar conflito entre múltiplas datas, e não ausência física na fonte.'

    FROM base


    UNION ALL


    SELECT
        ano_fonte,

        'PROCESSO_SEM_DATA_FIM_CONSOLIDADA',

        'COMPLETUDE',

        CAST(
            processos_sem_data_fim
            AS DOUBLE
        ),

        CAST(
            processos
            AS DOUBLE
        ),

        'Pode representar conflito entre múltiplas datas, e não ausência física na fonte.'

    FROM base


    UNION ALL


    SELECT
        ano_fonte,

        'PROCESSO_SEM_VIAJANTE_IDENTIFICADO',

        'COMPLETUDE',

        CAST(
            processos_sem_viajante
            AS DOUBLE
        ),

        CAST(
            processos
            AS DOUBLE
        ),

        'Viajante não identificável pela regra de pseudonimização.'

    FROM base


    UNION ALL


    SELECT
        ano_fonte,

        'PASSAGEM_SEM_DATA_EMISSAO',

        'COMPLETUDE',

        CAST(
            passagem_sem_data_emissao
            AS DOUBLE
        ),

        CAST(
            registros_passagem
            AS DOUBLE
        ),

        'Antecedência não pode ser calculada.'

    FROM base


    UNION ALL


    SELECT
        ano_fonte,

        'PASSAGEM_EMISSAO_APOS_INICIO',

        'REGRA_ANALITICA',

        CAST(
            passagem_emissao_apos_inicio
            AS DOUBLE
        ),

        CAST(
            registros_passagem
            AS DOUBLE
        ),

        'Mantida separadamente; não classificada automaticamente como erro.'

    FROM base


    UNION ALL


    SELECT
        ano_fonte,

        'TRECHO_MODAL_INVALIDO',

        'QUALIDADE_CATEGORICA',

        CAST(
            trecho_modal_invalido
            AS DOUBLE
        ),

        CAST(
            registros_trecho
            AS DOUBLE
        ),

        'Categoria INVÁLIDO preservada conforme a fonte.'

    FROM base


    UNION ALL


    SELECT
        ano_fonte,

        'REPETICAO_EXATA_OBSERVADA_PAGAMENTO',

        'MULTIPLICIDADE',

        CAST(
            repeticoes_exatas_pagamento
            AS DOUBLE
        ),

        CAST(
            registros_pagamento
            AS DOUBLE
        ),

        'Repetição exata observada; não equivale a duplicidade confirmada.'

    FROM base


    UNION ALL


    SELECT
        ano_fonte,

        'REPETICAO_EXATA_OBSERVADA_PASSAGEM',

        'MULTIPLICIDADE',

        CAST(
            repeticoes_exatas_passagem
            AS DOUBLE
        ),

        CAST(
            registros_passagem
            AS DOUBLE
        ),

        'Repetição exata observada; multiplicidade preservada.'

    FROM base


    UNION ALL


    SELECT
        ano_fonte,

        'REPETICAO_EXATA_OBSERVADA_TRECHO',

        'MULTIPLICIDADE',

        CAST(
            repeticoes_exatas_trecho
            AS DOUBLE
        ),

        CAST(
            registros_trecho
            AS DOUBLE
        ),

        'Repetição exata observada; multiplicidade preservada.'

    FROM base


    UNION ALL


    SELECT
        ano_fonte,

        'COBERTURA_VALOR_PASSAGEM_DETALHADA',

        'COBERTURA',

        CAST(
            custo_passagem_detalhada
            AS DOUBLE
        ),

        CAST(
            valor_pagamento_passagem
            AS DOUBLE
        ),

        'Valor de Passagem detalhado dividido pelo valor financeiro de Pagamento PASSAGEM.'

    FROM base


    UNION ALL


    SELECT
        ano_fonte,

        'COBERTURA_PROCESSOS_PASSAGEM_DETALHADA',

        'COBERTURA',

        CAST(
            processos_com_detalhamento
            AS DOUBLE
        ),

        CAST(
            processos_pagamento_passagem
            AS DOUBLE
        ),

        'Processos com pagamento PASSAGEM que também possuem detalhamento em Passagem.'

    FROM base
)

ORDER BY
    ano_fonte,
    categoria,
    indicador
"""


copy_parquet(
    con,
    MART_QUALIDADE,
    SQL_QUALIDADE
)


# 8. MANIFESTO

print(
    "\n" + "=" * 76
)

print(
    "8. GERANDO MANIFESTO"
)

print(
    "=" * 76
)


marts = [
    MART_EXECUTIVO,
    MART_GASTOS,
    MART_ANTECEDENCIA,
    MART_ANTECEDENCIA_DETALHE,
    MART_ORGAOS,
    MART_ROTAS,
    MART_MODAIS,
    MART_QUALIDADE,
]


linhas_manifesto = []


for arquivo in marts:

    total = con.execute(
        f"""
        SELECT COUNT(*)

        FROM read_parquet(
            '{sql_path(arquivo)}'
        )
        """
    ).fetchone()[0]

    schema = con.execute(
        f"""
        DESCRIBE

        SELECT *

        FROM read_parquet(
            '{sql_path(arquivo)}'
        )
        """
    ).fetchall()

    linhas_manifesto.append([
        arquivo.name,
        total,
        len(schema),
        arquivo.stat().st_size
    ])


salvar_csv(
    "01_manifesto_marts.csv",
    [
        "arquivo",
        "registros",
        "colunas",
        "tamanho_bytes"
    ],
    linhas_manifesto
)


# 9. VALIDAÇÕES DOS MARTS

print(
    "\n" + "=" * 76
)

print(
    "9. VALIDANDO MARTS"
)

print(
    "=" * 76
)


problemas = []

validacoes = []


# EXECUTIVO: 4 ANOS

qtd_exec = con.execute(
    f"""
    SELECT COUNT(*)

    FROM read_parquet(
        '{sql_path(MART_EXECUTIVO)}'
    )
    """
).fetchone()[0]


status = (
    "OK"
    if qtd_exec == 4
    else "ERRO"
)


validacoes.append([
    "mart_executivo_anual",
    "quantidade_anos",
    qtd_exec,
    4,
    status
])


if status == "ERRO":

    problemas.append(
        "Mart executivo deve possuir "
        "exatamente quatro anos."
    )


# VALOR TOTAL: FATO PAGAMENTO × MART EXECUTIVO

dados = con.execute(
    f"""
    WITH fato AS (

        SELECT
            ano_fonte,

            SUM(valor)
                AS valor_fato

        FROM read_parquet(
            '{sql_path(FATO_PAGAMENTO)}'
        )

        WHERE ano_fonte IN {ANOS_SQL}

        GROUP BY ano_fonte
    ),

    mart AS (

        SELECT
            ano_fonte,

            valor_total_pagamentos
                AS valor_mart

        FROM read_parquet(
            '{sql_path(MART_EXECUTIVO)}'
        )
    )

    SELECT
        f.ano_fonte,

        f.valor_fato,

        m.valor_mart,

        m.valor_mart
        -
        f.valor_fato
            AS diferenca

    FROM fato f

    INNER JOIN mart m
        USING (ano_fonte)

    ORDER BY f.ano_fonte
    """
).fetchall()


for (
    ano,
    valor_fato,
    valor_mart,
    diferenca
) in dados:

    status = (
        "OK"
        if abs(
            float(diferenca)
        ) <= 0.01
        else "ERRO"
    )

    validacoes.append([
        "mart_executivo_anual",
        f"reconciliacao_pagamentos_{ano}",
        valor_mart,
        valor_fato,
        status
    ])

    if status == "ERRO":

        problemas.append(
            f"Mart executivo não "
            f"reconcilia pagamentos em {ano}."
        )


# ANTECEDÊNCIA: PRESERVAR CUSTO PASSAGEM

dados = con.execute(
    f"""
    WITH fato AS (

        SELECT
            ano_fonte,

            SUM(custo_total_passagem)
                AS valor_fato

        FROM read_parquet(
            '{sql_path(FATO_PASSAGEM)}'
        )

        WHERE ano_fonte IN {ANOS_SQL}

        GROUP BY ano_fonte
    ),

    mart AS (

        SELECT
            ano_fonte,

            SUM(custo_total_passagens)
                AS valor_mart

        FROM read_parquet(
            '{sql_path(MART_ANTECEDENCIA)}'
        )

        GROUP BY ano_fonte
    )

    SELECT
        f.ano_fonte,

        f.valor_fato,

        m.valor_mart,

        m.valor_mart
        -
        f.valor_fato
            AS diferenca

    FROM fato f

    INNER JOIN mart m
        USING (ano_fonte)

    ORDER BY f.ano_fonte
    """
).fetchall()


for (
    ano,
    valor_fato,
    valor_mart,
    diferenca
) in dados:

    status = (
        "OK"
        if abs(
            float(diferenca)
        ) <= 0.01
        else "ERRO"
    )

    validacoes.append([
        "mart_antecedencia",
        f"reconciliacao_passagem_{ano}",
        valor_mart,
        valor_fato,
        status
    ])

    if status == "ERRO":

        problemas.append(
            f"Mart de antecedência "
            f"não reconcilia em {ano}."
        )


# ROTAS: PRESERVAR QUANTIDADE DE TRECHOS

dados = con.execute(
    f"""
    WITH fato AS (

        SELECT
            ano_fonte,

            COUNT(*)
                AS qtd_fato

        FROM read_parquet(
            '{sql_path(FATO_TRECHO)}'
        )

        WHERE ano_fonte IN {ANOS_SQL}

        GROUP BY ano_fonte
    ),

    mart AS (

        SELECT
            ano_fonte,

            SUM(qtd_trechos)
                AS qtd_mart

        FROM read_parquet(
            '{sql_path(MART_ROTAS)}'
        )

        GROUP BY ano_fonte
    )

    SELECT
        f.ano_fonte,

        f.qtd_fato,

        m.qtd_mart,

        m.qtd_mart
        -
        f.qtd_fato
            AS diferenca

    FROM fato f

    INNER JOIN mart m
        USING (ano_fonte)

    ORDER BY f.ano_fonte
    """
).fetchall()


for (
    ano,
    qtd_fato,
    qtd_mart,
    diferenca
) in dados:

    status = (
        "OK"
        if diferenca == 0
        else "ERRO"
    )

    validacoes.append([
        "mart_rotas",
        f"reconciliacao_trechos_{ano}",
        qtd_mart,
        qtd_fato,
        status
    ])

    if status == "ERRO":

        problemas.append(
            f"Mart de rotas não preserva "
            f"os trechos de {ano}."
        )


salvar_csv(
    "02_validacao_marts.csv",
    [
        "mart",
        "teste",
        "valor_obtido",
        "valor_esperado",
        "status"
    ],
    validacoes
)


# 10. CATÁLOGO FORMAL DE KPIs

print(
    "\n" + "=" * 76
)

print(
    "10. GERANDO CATÁLOGO DE KPIs"
)

print(
    "=" * 76
)


catalogo = [

    [
        "QTD_PROCESSOS",
        "Quantidade de processos",
        "COUNT(SK_Processo)",
        "Uma observação por processo e AnoFonte.",
        "FatoProcessoViagem",
        "Não contar as linhas brutas de Viagem como viagens independentes."
    ],

    [
        "PCT_PROCESSOS_URGENTES",
        "% de processos urgentes",
        "100 * processos urgentes / processos",
        "Participação dos processos classificados como urgentes.",
        "FatoProcessoViagem",
        "Urgência indeterminada permanece identificada separadamente."
    ],

    [
        "VALOR_TOTAL_PAGAMENTOS",
        "Valor total registrado em pagamentos",
        "SUM(FatoPagamento.valor)",
        "Valor total registrado nas quatro categorias de Pagamento.",
        "FatoPagamento",
        "Não denominar automaticamente como custo líquido."
    ],

    [
        "VALOR_PAGO_PASSAGENS",
        "Valor registrado em pagamentos de passagens",
        "SUM(valor) WHERE tipo = PASSAGEM",
        "Referência financeira principal para passagens.",
        "FatoPagamento",
        "FatoPassagem possui cobertura parcial."
    ],

    [
        "VALOR_PAGO_DIARIAS",
        "Valor registrado em pagamentos de diárias",
        "SUM(valor) WHERE tipo = DIARIAS",
        "Referência financeira principal para diárias.",
        "FatoPagamento",
        "Preserva a multiplicidade da fonte."
    ],

    [
        "VALOR_RESTITUICOES",
        "Valor de restituições",
        "SUM(valor) WHERE tipo = RESTITUICAO",
        "Pagamentos classificados como restituição.",
        "FatoPagamento",
        "Não equivale a Valor devolução da tabela Viagem."
    ],

    [
        "VALOR_SEGURO",
        "Valor de seguro",
        "SUM(valor) WHERE tipo = SEGURO",
        "Pagamentos classificados como serviço correlato: seguro.",
        "FatoPagamento",
        "Não equivale a Valor outros gastos."
    ],

    [
        "CUSTO_PASSAGEM_DETALHADA",
        "Custo das passagens com detalhamento disponível",
        "SUM(valor_passagem + taxa_servico)",
        "Custo dos registros existentes em FatoPassagem.",
        "FatoPassagem",
        "Não representa todo o gasto financeiro de passagens."
    ],

    [
        "COBERTURA_VALOR_PASSAGEM",
        "% de cobertura financeira do detalhamento",
        "100 * custo detalhado / pagamento PASSAGEM",
        "Percentual do valor financeiro de passagem coberto pelo detalhamento.",
        "FatoPassagem + FatoPagamento",
        "Indicador de cobertura da fonte."
    ],

    [
        "ANTECEDENCIA_MEDIANA",
        "Antecedência mediana",
        "MEDIAN(antecedencia_dias) WHERE antecedencia_dias >= 0",
        "Dias entre emissão e início da viagem.",
        "FatoPassagem",
        "Emissão após início é analisada separadamente."
    ],

    [
        "PCT_EMISSOES_ATE_7_DIAS",
        "% de emissões com até 7 dias de antecedência",
        "100 * registros de 0 a 7 dias / registros com antecedência >= 0",
        "Participação das emissões de curta antecedência.",
        "FatoPassagem",
        "Não implica causalidade entre antecedência e preço."
    ],

    [
        "PCT_EMISSAO_APOS_INICIO",
        "% de emissões após o início",
        "100 * antecedencia < 0 / registros Passagem",
        "Indicador operacional e de qualidade.",
        "FatoPassagem",
        "Não classificar automaticamente como erro."
    ],

    [
        "QTD_TRECHOS",
        "Quantidade de trechos",
        "COUNT(FatoTrecho)",
        "Quantidade de observações de trecho.",
        "FatoTrecho",
        "Modal INVÁLIDO deve ser tratado separadamente."
    ],
]


salvar_csv(
    "03_catalogo_kpis.csv",
    [
        "codigo_kpi",
        "nome_kpi",
        "formula",
        "definicao",
        "fonte_principal",
        "observacao_metodologica"
    ],
    catalogo
)


# ENCERRAMENTO

con.close()


print(
    "\n" + "=" * 76
)


if problemas:

    print(
        "MARTS CONSTRUÍDOS, "
        "MAS HÁ PROBLEMAS DE VALIDAÇÃO"
    )

    print(
        "=" * 76
    )

    for problema in problemas:

        print(
            f"⚠ {problema}"
        )

    raise RuntimeError(
        "Corrija os problemas "
        "antes de iniciar o dashboard."
    )


print(
    "ANALYTICS MARTS CONSTRUÍDOS "
    "E VALIDAÇÕES: OK"
)

print(
    "=" * 76
)

print(
    "\nDiretório dos marts:"
)

print(
    PASTA_MARTS
)

print(
    "\nMetadados:"
)

print(
    PASTA_METADATA
)