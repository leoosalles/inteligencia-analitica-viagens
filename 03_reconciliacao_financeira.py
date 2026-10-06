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

PASTA_SILVER = PASTA_DADOS / "silver"
PASTA_METADATA = PASTA_SILVER / "_metadata"

PASTA_METADATA.mkdir(
    parents=True,
    exist_ok=True
)


VIAGEM = PASTA_SILVER / "viagem.parquet"
PASSAGEM = PASTA_SILVER / "passagem.parquet"
PAGAMENTO = PASTA_SILVER / "pagamento.parquet"


def path_sql(path):
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


# VIEWS AGREGADAS POR PROCESSO

print("\nCriando agregações por processo...")


con.execute(f"""
    CREATE OR REPLACE TEMP VIEW viagem_proc AS

    SELECT
        ano_fonte,
        sk_processo,
        identificador_processo_viagem,

        COUNT(*) AS qtd_registros_viagem,

        MIN(valor_passagens)
            AS min_valor_passagens_viagem,

        MAX(valor_passagens)
            AS max_valor_passagens_viagem,

        MIN(valor_diarias)
            AS min_valor_diarias_viagem,

        MAX(valor_diarias)
            AS max_valor_diarias_viagem,

        CASE
            WHEN MIN(valor_passagens)
               = MAX(valor_passagens)
            THEN MAX(valor_passagens)
            ELSE NULL
        END
            AS valor_passagens_viagem_ref,

        CASE
            WHEN MIN(valor_diarias)
               = MAX(valor_diarias)
            THEN MAX(valor_diarias)
            ELSE NULL
        END
            AS valor_diarias_viagem_ref

    FROM read_parquet(
        '{path_sql(VIAGEM)}'
    )

    GROUP BY
        ano_fonte,
        sk_processo,
        identificador_processo_viagem
""")


# PAGAMENTO - PASSAGEM

con.execute(f"""
    CREATE OR REPLACE TEMP VIEW pagamento_passagem_proc AS

    SELECT
        ano_fonte,
        sk_processo,

        COUNT(*) AS qtd_pagamentos_passagem,

        SUM(valor)
            AS valor_pagamento_passagem

    FROM read_parquet(
        '{path_sql(PAGAMENTO)}'
    )

    WHERE tipo_pagamento_normalizado
        = 'PASSAGEM'

    GROUP BY
        ano_fonte,
        sk_processo
""")


# PAGAMENTO - DIÁRIAS

con.execute(f"""
    CREATE OR REPLACE TEMP VIEW pagamento_diarias_proc AS

    SELECT
        ano_fonte,
        sk_processo,

        COUNT(*) AS qtd_pagamentos_diarias,

        SUM(valor)
            AS valor_pagamento_diarias

    FROM read_parquet(
        '{path_sql(PAGAMENTO)}'
    )

    WHERE tipo_pagamento_normalizado
        = 'DIARIAS'

    GROUP BY
        ano_fonte,
        sk_processo
""")


# PASSAGEM

con.execute(f"""
    CREATE OR REPLACE TEMP VIEW passagem_proc AS

    SELECT
        ano_fonte,
        sk_processo,

        COUNT(*) AS qtd_registros_passagem,

        SUM(valor_passagem)
            AS valor_tarifa,

        SUM(taxa_servico)
            AS valor_taxa_servico,

        SUM(custo_total_passagem)
            AS custo_total_passagem

    FROM read_parquet(
        '{path_sql(PASSAGEM)}'
    )

    GROUP BY
        ano_fonte,
        sk_processo
""")


# 1. COBERTURA PASSAGEM × PAGAMENTO

print("\n[1/5] Analisando cobertura Passagem × Pagamento...")


cobertura = con.execute("""
    WITH universo AS (

        SELECT
            COALESCE(
                pg.ano_fonte,
                ps.ano_fonte
            ) AS ano,

            COALESCE(
                pg.sk_processo,
                ps.sk_processo
            ) AS sk_processo,

            pg.valor_pagamento_passagem,
            ps.custo_total_passagem,

            CASE
                WHEN pg.sk_processo IS NOT NULL
                 AND ps.sk_processo IS NOT NULL
                THEN 1
                ELSE 0
            END AS em_ambas,

            CASE
                WHEN pg.sk_processo IS NOT NULL
                 AND ps.sk_processo IS NULL
                THEN 1
                ELSE 0
            END AS somente_pagamento,

            CASE
                WHEN pg.sk_processo IS NULL
                 AND ps.sk_processo IS NOT NULL
                THEN 1
                ELSE 0
            END AS somente_passagem

        FROM pagamento_passagem_proc pg

        FULL OUTER JOIN passagem_proc ps
            ON pg.ano_fonte = ps.ano_fonte
           AND pg.sk_processo = ps.sk_processo
    )

    SELECT
        ano,

        COUNT(*) AS processos_uniao,

        SUM(em_ambas)
            AS processos_em_ambas,

        SUM(somente_pagamento)
            AS processos_so_pagamento,

        SUM(somente_passagem)
            AS processos_so_passagem,

        SUM(
            COALESCE(
                valor_pagamento_passagem,
                0
            )
        )
            AS valor_pagamento_total,

        SUM(
            COALESCE(
                custo_total_passagem,
                0
            )
        )
            AS valor_passagem_total,

        SUM(
            CASE
                WHEN em_ambas = 1
                THEN valor_pagamento_passagem
                ELSE 0
            END
        )
            AS pagamento_processos_comuns,

        SUM(
            CASE
                WHEN em_ambas = 1
                THEN custo_total_passagem
                ELSE 0
            END
        )
            AS passagem_processos_comuns,

        SUM(
            CASE
                WHEN somente_pagamento = 1
                THEN valor_pagamento_passagem
                ELSE 0
            END
        )
            AS valor_so_pagamento,

        SUM(
            CASE
                WHEN somente_passagem = 1
                THEN custo_total_passagem
                ELSE 0
            END
        )
            AS valor_so_passagem

    FROM universo

    GROUP BY ano
    ORDER BY ano
""").fetchall()


salvar_csv(
    "08_cobertura_passagem_pagamento.csv",
    [
        "ano",
        "processos_uniao",
        "processos_em_ambas",
        "processos_so_pagamento",
        "processos_so_passagem",
        "valor_pagamento_total",
        "valor_passagem_total",
        "pagamento_processos_comuns",
        "passagem_processos_comuns",
        "valor_so_pagamento",
        "valor_so_passagem"
    ],
    cobertura
)


# 2. RECONCILIAÇÃO NOS PROCESSOS PRESENTES EM AMBAS

print("\n[2/5] Reconciliando processos comuns...")


reconciliacao = con.execute("""
    WITH base AS (

        SELECT
            pg.ano_fonte AS ano,
            pg.sk_processo,

            pg.valor_pagamento_passagem,
            ps.custo_total_passagem,

            (
                ps.custo_total_passagem
                -
                pg.valor_pagamento_passagem
            ) AS diferenca,

            ABS(
                ps.custo_total_passagem
                -
                pg.valor_pagamento_passagem
            ) AS diferenca_absoluta

        FROM pagamento_passagem_proc pg

        INNER JOIN passagem_proc ps
            ON pg.ano_fonte = ps.ano_fonte
           AND pg.sk_processo = ps.sk_processo
    )

    SELECT
        ano,

        COUNT(*)
            AS processos_comuns,

        SUM(
            CASE
                WHEN diferenca_absoluta <= 0.01
                THEN 1
                ELSE 0
            END
        )
            AS correspondencia_ate_1_centavo,

        SUM(
            CASE
                WHEN diferenca_absoluta <= 1.00
                THEN 1
                ELSE 0
            END
        )
            AS correspondencia_ate_1_real,

        SUM(
            CASE
                WHEN
                    valor_pagamento_passagem <> 0
                    AND (
                        diferenca_absoluta
                        /
                        ABS(valor_pagamento_passagem)
                    ) <= 0.01
                THEN 1
                ELSE 0
            END
        )
            AS correspondencia_ate_1_pct,

        SUM(valor_pagamento_passagem)
            AS pagamento_total_comum,

        SUM(custo_total_passagem)
            AS passagem_total_comum,

        SUM(diferenca)
            AS diferenca_liquida,

        SUM(diferenca_absoluta)
            AS diferenca_absoluta_total

    FROM base

    GROUP BY ano
    ORDER BY ano
""").fetchall()


salvar_csv(
    "09_reconciliacao_passagem_pagamento.csv",
    [
        "ano",
        "processos_comuns",
        "correspondencia_ate_1_centavo",
        "correspondencia_ate_1_real",
        "correspondencia_ate_1_pct",
        "pagamento_total_comum",
        "passagem_total_comum",
        "diferenca_liquida",
        "diferenca_absoluta_total"
    ],
    reconciliacao
)


# 3. VIAGEM × PAGAMENTO

print("\n[3/5] Reconciliando Viagem × Pagamento...")


viagem_pagamento = con.execute("""
    WITH passagem AS (

        SELECT
            v.ano_fonte AS ano,
            v.sk_processo,

            v.valor_passagens_viagem_ref
                AS valor_viagem,

            p.valor_pagamento_passagem
                AS valor_pagamento

        FROM viagem_proc v

        INNER JOIN pagamento_passagem_proc p
            ON v.ano_fonte = p.ano_fonte
           AND v.sk_processo = p.sk_processo

        WHERE v.valor_passagens_viagem_ref
            IS NOT NULL
    ),

    diarias AS (

        SELECT
            v.ano_fonte AS ano,
            v.sk_processo,

            v.valor_diarias_viagem_ref
                AS valor_viagem,

            p.valor_pagamento_diarias
                AS valor_pagamento

        FROM viagem_proc v

        INNER JOIN pagamento_diarias_proc p
            ON v.ano_fonte = p.ano_fonte
           AND v.sk_processo = p.sk_processo

        WHERE v.valor_diarias_viagem_ref
            IS NOT NULL
    ),

    combinado AS (

        SELECT
            ano,
            'PASSAGEM' AS tipo,
            valor_viagem,
            valor_pagamento
        FROM passagem

        UNION ALL

        SELECT
            ano,
            'DIARIAS' AS tipo,
            valor_viagem,
            valor_pagamento
        FROM diarias
    )

    SELECT
        ano,
        tipo,

        COUNT(*)
            AS processos_comparados,

        SUM(valor_viagem)
            AS total_viagem,

        SUM(valor_pagamento)
            AS total_pagamento,

        SUM(
            valor_pagamento
            -
            valor_viagem
        )
            AS diferenca_liquida,

        SUM(
            ABS(
                valor_pagamento
                -
                valor_viagem
            )
        )
            AS diferenca_absoluta,

        SUM(
            CASE
                WHEN ABS(
                    valor_pagamento
                    -
                    valor_viagem
                ) <= 0.01
                THEN 1
                ELSE 0
            END
        )
            AS correspondencia_centavo,

        SUM(
            CASE
                WHEN
                    valor_viagem <> 0
                    AND
                    (
                        ABS(
                            valor_pagamento
                            -
                            valor_viagem
                        )
                        /
                        ABS(valor_viagem)
                    ) <= 0.01
                THEN 1
                ELSE 0
            END
        )
            AS correspondencia_1_pct

    FROM combinado

    GROUP BY
        ano,
        tipo

    ORDER BY
        ano,
        tipo
""").fetchall()


salvar_csv(
    "10_reconciliacao_viagem_pagamento.csv",
    [
        "ano",
        "tipo",
        "processos_comparados",
        "total_viagem",
        "total_pagamento",
        "diferenca_liquida",
        "diferenca_absoluta",
        "correspondencia_centavo",
        "correspondencia_1_pct"
    ],
    viagem_pagamento
)


# 4. PROCESSOS COM VALORES DIFERENTES DENTRO DE VIAGEM

print("\n[4/5] Localizando processos multivalorados em Viagem...")


multivalorados = con.execute("""
    SELECT
        ano_fonte,
        sk_processo,
        identificador_processo_viagem,
        qtd_registros_viagem,

        min_valor_passagens_viagem,
        max_valor_passagens_viagem,

        min_valor_diarias_viagem,
        max_valor_diarias_viagem

    FROM viagem_proc

    WHERE
        min_valor_passagens_viagem
            IS DISTINCT FROM
        max_valor_passagens_viagem

       OR

        min_valor_diarias_viagem
            IS DISTINCT FROM
        max_valor_diarias_viagem

    ORDER BY
        ano_fonte,
        identificador_processo_viagem
""").fetchall()


salvar_csv(
    "11_processos_viagem_multivalorados.csv",
    [
        "ano",
        "sk_processo",
        "identificador_processo_viagem",
        "qtd_registros_viagem",
        "min_valor_passagens",
        "max_valor_passagens",
        "min_valor_diarias",
        "max_valor_diarias"
    ],
    multivalorados
)


# 5. MAIORES DIFERENÇAS PASSAGEM × PAGAMENTO

print("\n[5/5] Localizando maiores diferenças...")


maiores_diferencas = con.execute("""
    SELECT
        pg.ano_fonte,
        pg.sk_processo,

        pg.qtd_pagamentos_passagem,
        ps.qtd_registros_passagem,

        pg.valor_pagamento_passagem,
        ps.custo_total_passagem,

        (
            ps.custo_total_passagem
            -
            pg.valor_pagamento_passagem
        ) AS diferenca,

        ABS(
            ps.custo_total_passagem
            -
            pg.valor_pagamento_passagem
        ) AS diferenca_absoluta

    FROM pagamento_passagem_proc pg

    INNER JOIN passagem_proc ps
        ON pg.ano_fonte = ps.ano_fonte
       AND pg.sk_processo = ps.sk_processo

    ORDER BY
        diferenca_absoluta DESC

    LIMIT 500
""").fetchall()


salvar_csv(
    "12_maiores_diferencas_passagem_pagamento.csv",
    [
        "ano",
        "sk_processo",
        "qtd_pagamentos_passagem",
        "qtd_registros_passagem",
        "valor_pagamento_passagem",
        "custo_total_passagem",
        "diferenca",
        "diferenca_absoluta"
    ],
    maiores_diferencas
)


con.close()


print("\n" + "=" * 72)
print("RECONCILIAÇÃO FINANCEIRA CONCLUÍDA")
print("=" * 72)

print("\nRelatórios gerados:")

print("08_cobertura_passagem_pagamento.csv")
print("09_reconciliacao_passagem_pagamento.csv")
print("10_reconciliacao_viagem_pagamento.csv")
print("11_processos_viagem_multivalorados.csv")
print("12_maiores_diferencas_passagem_pagamento.csv")