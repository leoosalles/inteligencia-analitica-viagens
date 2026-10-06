from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

from dashboard.config import (
    MART_EXECUTIVO,
    MART_GASTOS,
    MART_ORGAOS,
    MART_ANTECEDENCIA,
    MART_ANTECEDENCIA_DETALHE,
    MART_ROTAS,
    MART_MODAIS,
    MART_QUALIDADE,
)


def sql_path(path: Path) -> str:
    return (
        path
        .as_posix()
        .replace("'", "''")
    )


def validar_arquivo(arquivo: Path):
    if not arquivo.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {arquivo}"
        )


@st.cache_data(show_spinner=False)
def carregar_parquet(caminho: str) -> pd.DataFrame:
    arquivo = Path(caminho)

    validar_arquivo(arquivo)

    con = duckdb.connect()

    try:
        df = con.execute(
            f"""
            SELECT *
            FROM read_parquet(
                '{sql_path(arquivo)}'
            )
            """
        ).df()

    finally:
        con.close()

    return df


def carregar_executivo():
    return carregar_parquet(
        str(MART_EXECUTIVO)
    )


def carregar_gastos():
    return carregar_parquet(
        str(MART_GASTOS)
    )


@st.cache_data(show_spinner=False)
def obter_antecedencia_mediana(anos_tuple):
    anos = [
        int(x)
        for x in anos_tuple
    ]

    if not anos:
        return None

    lista_anos = ", ".join(
        str(x)
        for x in anos
    )

    validar_arquivo(
        MART_ANTECEDENCIA_DETALHE
    )

    con = duckdb.connect()

    try:
        resultado = con.execute(
            f"""
            SELECT
                MEDIAN(antecedencia_dias)

            FROM read_parquet(
                '{sql_path(MART_ANTECEDENCIA_DETALHE)}'
            )

            WHERE ano_fonte IN (
                {lista_anos}
            )

              AND antecedencia_dias >= 0
            """
        ).fetchone()[0]

    finally:
        con.close()

    if resultado is None:
        return None

    return float(resultado)


def carregar_orgaos():
    return carregar_parquet(
        str(MART_ORGAOS)
    )


# ANTECEDÊNCIA

def carregar_antecedencia():
    return carregar_parquet(
        str(MART_ANTECEDENCIA)
    )


def _sql_lista_texto(valores):
    return ", ".join(
        "'"
        + str(valor).replace("'", "''")
        + "'"
        for valor in valores
    )


@st.cache_data(show_spinner=False)
def consultar_antecedencia_faixas(
    anos_tuple,
    urgencias_tuple,
    modais_tuple,
):
    anos = [
        int(x)
        for x in anos_tuple
    ]

    urgencias = list(
        urgencias_tuple
    )

    modais = list(
        modais_tuple
    )

    if not anos:
        return pd.DataFrame()

    anos_sql = ", ".join(
        str(x)
        for x in anos
    )

    filtros = [
        f"ano_fonte IN ({anos_sql})"
    ]

    if urgencias:
        filtros.append(
            "categoria_urgencia IN ("
            + _sql_lista_texto(
                urgencias
            )
            + ")"
        )

    if modais:
        filtros.append(
            "modal IN ("
            + _sql_lista_texto(
                modais
            )
            + ")"
        )

    where_sql = (
        " AND ".join(
            filtros
        )
    )

    validar_arquivo(
        MART_ANTECEDENCIA_DETALHE
    )

    con = duckdb.connect()

    try:
        df = con.execute(
            f"""
            SELECT
                faixa_antecedencia,

                CASE
                    WHEN faixa_antecedencia
                        = 'EMISSAO_APOS_INICIO'
                    THEN 0

                    WHEN faixa_antecedencia
                        = '0_A_3_DIAS'
                    THEN 1

                    WHEN faixa_antecedencia
                        = '4_A_7_DIAS'
                    THEN 2

                    WHEN faixa_antecedencia
                        = '8_A_14_DIAS'
                    THEN 3

                    WHEN faixa_antecedencia
                        = '15_A_30_DIAS'
                    THEN 4

                    WHEN faixa_antecedencia
                        = 'MAIS_DE_30_DIAS'
                    THEN 5

                    WHEN faixa_antecedencia
                        = 'SEM_INFORMACAO'
                    THEN 6

                    ELSE 99
                END
                    AS ordem_faixa,

                COUNT(*)
                    AS qtd_registros,

                COUNT(
                    DISTINCT sk_processo
                )
                    AS qtd_processos,

                SUM(
                    custo_total_passagem
                )
                    AS custo_total,

                AVG(
                    custo_total_passagem
                )
                    AS custo_medio_passagem,

                MEDIAN(
                    custo_total_passagem
                )
                    AS custo_mediano_passagem,

                AVG(
                    antecedencia_dias
                )
                    AS antecedencia_media_dias,

                MEDIAN(
                    antecedencia_dias
                )
                    AS antecedencia_mediana_dias

            FROM read_parquet(
                '{sql_path(MART_ANTECEDENCIA_DETALHE)}'
            )

            WHERE {where_sql}

            GROUP BY
                faixa_antecedencia,
                ordem_faixa

            ORDER BY
                ordem_faixa
            """
        ).df()

    finally:
        con.close()

    return df


@st.cache_data(show_spinner=False)
def consultar_resumo_antecedencia(
    anos_tuple,
    urgencias_tuple,
    modais_tuple,
):
    anos = [
        int(x)
        for x in anos_tuple
    ]

    urgencias = list(
        urgencias_tuple
    )

    modais = list(
        modais_tuple
    )

    if not anos:
        return {}

    anos_sql = ", ".join(
        str(x)
        for x in anos
    )

    filtros = [
        f"ano_fonte IN ({anos_sql})"
    ]

    if urgencias:
        filtros.append(
            "categoria_urgencia IN ("
            + _sql_lista_texto(
                urgencias
            )
            + ")"
        )

    if modais:
        filtros.append(
            "modal IN ("
            + _sql_lista_texto(
                modais
            )
            + ")"
        )

    where_sql = (
        " AND ".join(
            filtros
        )
    )

    validar_arquivo(
        MART_ANTECEDENCIA_DETALHE
    )

    con = duckdb.connect()

    try:
        resultado = con.execute(
            f"""
            SELECT
                COUNT(*)
                    AS total_registros,

                COUNT(*) FILTER (
                    WHERE antecedencia_dias >= 0
                )
                    AS registros_antecedencia_valida,

                COUNT(*) FILTER (
                    WHERE antecedencia_dias
                        BETWEEN 0 AND 7
                )
                    AS registros_ate_7_dias,

                COUNT(*) FILTER (
                    WHERE antecedencia_dias < 0
                )
                    AS registros_apos_inicio,

                COUNT(*) FILTER (
                    WHERE antecedencia_dias
                        IS NULL
                )
                    AS registros_sem_antecedencia,

                MEDIAN(
                    antecedencia_dias
                ) FILTER (
                    WHERE antecedencia_dias >= 0
                )
                    AS antecedencia_mediana,

                AVG(
                    antecedencia_dias
                ) FILTER (
                    WHERE antecedencia_dias >= 0
                )
                    AS antecedencia_media,

                MEDIAN(
                    custo_total_passagem
                ) FILTER (
                    WHERE antecedencia_dias >= 0
                )
                    AS custo_mediano,

                AVG(
                    custo_total_passagem
                ) FILTER (
                    WHERE antecedencia_dias >= 0
                )
                    AS custo_medio

            FROM read_parquet(
                '{sql_path(MART_ANTECEDENCIA_DETALHE)}'
            )

            WHERE {where_sql}
            """
        ).fetchone()

    finally:
        con.close()

    colunas = [
        "total_registros",
        "registros_antecedencia_valida",
        "registros_ate_7_dias",
        "registros_apos_inicio",
        "registros_sem_antecedencia",
        "antecedencia_mediana",
        "antecedencia_media",
        "custo_mediano",
        "custo_medio",
    ]

    return dict(
        zip(
            colunas,
            resultado,
        )
    )


# ROTAS E MODAIS

def carregar_modais():
    return carregar_parquet(
        str(MART_MODAIS)
    )


def _sql_lista_inteiros(valores):
    return ", ".join(
        str(int(valor))
        for valor in valores
    )


def _sql_lista_strings(valores):
    return ", ".join(
        "'"
        + str(valor).replace("'", "''")
        + "'"
        for valor in valores
    )


def _filtros_rotas_sql(
    anos_tuple,
    modais_tuple,
    origem_pais=None,
    origem_uf=None,
    destino_pais=None,
    destino_uf=None,
    incluir_invalidos=False,
):
    filtros = []

    anos = list(
        anos_tuple
    )

    modais = list(
        modais_tuple
    )

    if anos:
        filtros.append(
            "ano_fonte IN ("
            + _sql_lista_inteiros(anos)
            + ")"
        )

    if modais:
        filtros.append(
            "modal IN ("
            + _sql_lista_strings(modais)
            + ")"
        )

    if not incluir_invalidos:
        filtros.append(
            "COALESCE(flag_modal_valido, FALSE) = TRUE"
        )

    if origem_pais:
        filtros.append(
            "origem_pais = '"
            + str(origem_pais).replace(
                "'",
                "''"
            )
            + "'"
        )

    if origem_uf:
        filtros.append(
            "origem_uf = '"
            + str(origem_uf).replace(
                "'",
                "''"
            )
            + "'"
        )

    if destino_pais:
        filtros.append(
            "destino_pais = '"
            + str(destino_pais).replace(
                "'",
                "''"
            )
            + "'"
        )

    if destino_uf:
        filtros.append(
            "destino_uf = '"
            + str(destino_uf).replace(
                "'",
                "''"
            )
            + "'"
        )

    if not filtros:
        return "TRUE"

    return " AND ".join(
        filtros
    )


@st.cache_data(
    show_spinner=False
)
def consultar_filtros_rotas():
    validar_arquivo(
        MART_ROTAS
    )

    con = duckdb.connect()

    try:
        paises_origem = [
            row[0]
            for row in con.execute(
                f"""
                SELECT DISTINCT
                    origem_pais

                FROM read_parquet(
                    '{sql_path(MART_ROTAS)}'
                )

                WHERE origem_pais IS NOT NULL

                ORDER BY origem_pais
                """
            ).fetchall()
        ]

        paises_destino = [
            row[0]
            for row in con.execute(
                f"""
                SELECT DISTINCT
                    destino_pais

                FROM read_parquet(
                    '{sql_path(MART_ROTAS)}'
                )

                WHERE destino_pais IS NOT NULL

                ORDER BY destino_pais
                """
            ).fetchall()
        ]

        ufs_origem = [
            row[0]
            for row in con.execute(
                f"""
                SELECT DISTINCT
                    origem_uf

                FROM read_parquet(
                    '{sql_path(MART_ROTAS)}'
                )

                WHERE origem_uf IS NOT NULL

                ORDER BY origem_uf
                """
            ).fetchall()
        ]

        ufs_destino = [
            row[0]
            for row in con.execute(
                f"""
                SELECT DISTINCT
                    destino_uf

                FROM read_parquet(
                    '{sql_path(MART_ROTAS)}'
                )

                WHERE destino_uf IS NOT NULL

                ORDER BY destino_uf
                """
            ).fetchall()
        ]

    finally:
        con.close()

    return {
        "paises_origem":
            paises_origem,

        "paises_destino":
            paises_destino,

        "ufs_origem":
            ufs_origem,

        "ufs_destino":
            ufs_destino,
    }


@st.cache_data(
    show_spinner=False
)
def consultar_resumo_rotas(
    anos_tuple,
    modais_tuple,
    origem_pais,
    origem_uf,
    destino_pais,
    destino_uf,
    incluir_invalidos,
):
    validar_arquivo(
        MART_ROTAS
    )

    where_sql = _filtros_rotas_sql(
        anos_tuple=anos_tuple,
        modais_tuple=modais_tuple,
        origem_pais=origem_pais,
        origem_uf=origem_uf,
        destino_pais=destino_pais,
        destino_uf=destino_uf,
        incluir_invalidos=incluir_invalidos,
    )

    con = duckdb.connect()

    try:
        resultado = con.execute(
            f"""
            SELECT
                SUM(qtd_trechos)
                    AS qtd_trechos,

                COUNT(
                    DISTINCT
                    sk_localidade_origem
                )
                    AS qtd_origens,

                COUNT(
                    DISTINCT
                    sk_localidade_destino
                )
                    AS qtd_destinos,

                COUNT(
                    DISTINCT
                    sk_localidade_origem
                    || '|'
                    || sk_localidade_destino
                )
                    AS qtd_rotas,

                COUNT(
                    DISTINCT sk_modal
                )
                    AS qtd_modais

            FROM read_parquet(
                '{sql_path(MART_ROTAS)}'
            )

            WHERE {where_sql}
            """
        ).fetchone()

    finally:
        con.close()

    nomes = [
        "qtd_trechos",
        "qtd_origens",
        "qtd_destinos",
        "qtd_rotas",
        "qtd_modais",
    ]

    return dict(
        zip(
            nomes,
            resultado,
        )
    )


@st.cache_data(
    show_spinner=False
)
def consultar_top_origens(
    anos_tuple,
    modais_tuple,
    origem_pais,
    origem_uf,
    destino_pais,
    destino_uf,
    incluir_invalidos,
    top_n,
):
    validar_arquivo(
        MART_ROTAS
    )

    where_sql = _filtros_rotas_sql(
        anos_tuple,
        modais_tuple,
        origem_pais,
        origem_uf,
        destino_pais,
        destino_uf,
        incluir_invalidos,
    )

    con = duckdb.connect()

    try:
        df = con.execute(
            f"""
            SELECT
                origem_pais,
                origem_uf,
                origem_cidade,

                SUM(qtd_trechos)
                    AS qtd_trechos

            FROM read_parquet(
                '{sql_path(MART_ROTAS)}'
            )

            WHERE {where_sql}

            GROUP BY
                origem_pais,
                origem_uf,
                origem_cidade

            ORDER BY
                qtd_trechos DESC

            LIMIT {int(top_n)}
            """
        ).df()

    finally:
        con.close()

    return df


@st.cache_data(
    show_spinner=False
)
def consultar_top_destinos(
    anos_tuple,
    modais_tuple,
    origem_pais,
    origem_uf,
    destino_pais,
    destino_uf,
    incluir_invalidos,
    top_n,
):
    validar_arquivo(
        MART_ROTAS
    )

    where_sql = _filtros_rotas_sql(
        anos_tuple,
        modais_tuple,
        origem_pais,
        origem_uf,
        destino_pais,
        destino_uf,
        incluir_invalidos,
    )

    con = duckdb.connect()

    try:
        df = con.execute(
            f"""
            SELECT
                destino_pais,
                destino_uf,
                destino_cidade,

                SUM(qtd_trechos)
                    AS qtd_trechos

            FROM read_parquet(
                '{sql_path(MART_ROTAS)}'
            )

            WHERE {where_sql}

            GROUP BY
                destino_pais,
                destino_uf,
                destino_cidade

            ORDER BY
                qtd_trechos DESC

            LIMIT {int(top_n)}
            """
        ).df()

    finally:
        con.close()

    return df


@st.cache_data(
    show_spinner=False
)
def consultar_top_rotas(
    anos_tuple,
    modais_tuple,
    origem_pais,
    origem_uf,
    destino_pais,
    destino_uf,
    incluir_invalidos,
    top_n,
):
    validar_arquivo(
        MART_ROTAS
    )

    where_sql = _filtros_rotas_sql(
        anos_tuple,
        modais_tuple,
        origem_pais,
        origem_uf,
        destino_pais,
        destino_uf,
        incluir_invalidos,
    )

    con = duckdb.connect()

    try:
        df = con.execute(
            f"""
            SELECT
                origem_pais,
                origem_uf,
                origem_cidade,

                destino_pais,
                destino_uf,
                destino_cidade,

                SUM(qtd_trechos)
                    AS qtd_trechos

            FROM read_parquet(
                '{sql_path(MART_ROTAS)}'
            )

            WHERE {where_sql}

            GROUP BY
                origem_pais,
                origem_uf,
                origem_cidade,
                destino_pais,
                destino_uf,
                destino_cidade

            ORDER BY
                qtd_trechos DESC

            LIMIT {int(top_n)}
            """
        ).df()

    finally:
        con.close()

    return df


@st.cache_data(
    show_spinner=False
)
def consultar_modais_resumo(
    anos_tuple,
    incluir_invalidos,
):
    validar_arquivo(
        MART_MODAIS
    )

    anos_sql = (
        _sql_lista_inteiros(
            anos_tuple
        )
    )

    filtros = [
        f"ano_fonte IN ({anos_sql})"
    ]

    if not incluir_invalidos:
        filtros.append(
            "COALESCE(flag_modal_valido, FALSE) = TRUE"
        )

    where_sql = " AND ".join(
        filtros
    )

    con = duckdb.connect()

    try:
        df = con.execute(
            f"""
            SELECT
                modal,

                SUM(qtd_trechos)
                    AS qtd_trechos,

                SUM(qtd_registros_passagem)
                    AS qtd_registros_passagem,

                SUM(custo_total_passagens)
                    AS custo_total_passagens,

                SUM(custo_total_passagens)
                /
                NULLIF(
                    SUM(qtd_registros_passagem),
                    0
                )
                    AS custo_medio_passagem

            FROM read_parquet(
                '{sql_path(MART_MODAIS)}'
            )

            WHERE {where_sql}

            GROUP BY modal

            ORDER BY
                qtd_trechos DESC
            """
        ).df()

    finally:
        con.close()

    return df


# QUALIDADE DOS DADOS

def carregar_qualidade():
    return carregar_parquet(
        str(MART_QUALIDADE)
    )