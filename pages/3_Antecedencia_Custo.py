import pandas as pd
import streamlit as st

from dashboard.charts import (
    grafico_custo_antecedencia,
    grafico_modal_custo,
    grafico_urgencia_antecedencia,
    grafico_volume_antecedencia,
)
from dashboard.components import (
    cabecalho_pagina,
    nota_metodologica,
    titulo_secao,
)
from dashboard.config import (
    ANOS_HISTORICOS,
)
from dashboard.data import (
    carregar_antecedencia,
    consultar_antecedencia_faixas,
    consultar_resumo_antecedencia,
)
from dashboard.formatters import (
    dias_br,
    inteiro_br,
    moeda_br,
    percentual_br,
)


# CABEÇALHO

cabecalho_pagina(
    titulo="Antecedência e Custo",
    subtitulo=(
        "Análise da associação entre o prazo de emissão "
        "e o custo das passagens com detalhamento disponível."
    ),
)


# CARREGAMENTO

try:
    df_mart = (
        carregar_antecedencia()
        .copy()
    )

except FileNotFoundError as exc:
    st.error(
        str(exc)
    )
    st.stop()


# FILTROS

st.sidebar.header(
    "Filtros"
)


anos_disponiveis = sorted(
    int(x)
    for x in df_mart[
        "ano_fonte"
    ].unique()
    if int(x) in ANOS_HISTORICOS
)


anos_selecionados = st.sidebar.multiselect(
    "Ano",
    options=anos_disponiveis,
    default=anos_disponiveis,
    key="antecedencia_anos",
)


if not anos_selecionados:
    anos_selecionados = (
        anos_disponiveis
    )


urgencias_disponiveis = [
    "URGENTE",
    "NAO_URGENTE",
    "INDETERMINADA",
]


nomes_urgencia = {
    "URGENTE":
        "Urgente",

    "NAO_URGENTE":
        "Não urgente",

    "INDETERMINADA":
        "Indeterminada",
}


urgencias_selecionadas = (
    st.sidebar.multiselect(
        "Urgência",
        options=urgencias_disponiveis,
        default=urgencias_disponiveis,
        format_func=lambda x:
            nomes_urgencia.get(
                x,
                x,
            ),
        key="antecedencia_urgencia",
    )
)


if not urgencias_selecionadas:
    urgencias_selecionadas = (
        urgencias_disponiveis
    )


modais_disponiveis = sorted(
    str(x)
    for x in df_mart[
        "modal"
    ].dropna().unique()
)


modais_selecionados = st.sidebar.multiselect(
    "Modal",
    options=modais_disponiveis,
    default=modais_disponiveis,
    key="antecedencia_modal",
)


if not modais_selecionados:
    modais_selecionados = (
        modais_disponiveis
    )


# CONSULTAS EXATAS

with st.spinner(
    "Calculando indicadores..."
):

    df_faixas = (
        consultar_antecedencia_faixas(
            tuple(
                sorted(
                    anos_selecionados
                )
            ),
            tuple(
                sorted(
                    urgencias_selecionadas
                )
            ),
            tuple(
                sorted(
                    modais_selecionados
                )
            ),
        )
    )

    resumo = (
        consultar_resumo_antecedencia(
            tuple(
                sorted(
                    anos_selecionados
                )
            ),
            tuple(
                sorted(
                    urgencias_selecionadas
                )
            ),
            tuple(
                sorted(
                    modais_selecionados
                )
            ),
        )
    )


# MART FILTRADO

mart_filtrado = df_mart[
    df_mart[
        "ano_fonte"
    ].isin(
        anos_selecionados
    )
    &
    df_mart[
        "categoria_urgencia"
    ].isin(
        urgencias_selecionadas
    )
    &
    df_mart[
        "modal"
    ].isin(
        modais_selecionados
    )
].copy()


# KPIs

total = (
    resumo.get(
        "total_registros",
        0
    )
    or 0
)

validos = (
    resumo.get(
        "registros_antecedencia_valida",
        0
    )
    or 0
)

ate_7 = (
    resumo.get(
        "registros_ate_7_dias",
        0
    )
    or 0
)

apos_inicio = (
    resumo.get(
        "registros_apos_inicio",
        0
    )
    or 0
)

sem_antecedencia = (
    resumo.get(
        "registros_sem_antecedencia",
        0
    )
    or 0
)


pct_ate_7 = (
    100.0
    * ate_7
    / validos
    if validos
    else None
)


pct_apos_inicio = (
    100.0
    * apos_inicio
    / total
    if total
    else None
)


# CARTÕES

titulo_secao(
    "Indicadores de planejamento",
    (
        "As métricas principais excluem emissões "
        "posteriores ao início da viagem."
    ),
)


c1, c2, c3 = st.columns(
    3
)

with c1:
    st.metric(
        "Antecedência mediana",
        dias_br(
            resumo.get(
                "antecedencia_mediana"
            )
        ),
    )

with c2:
    st.metric(
        "Custo mediano da passagem",
        moeda_br(
            resumo.get(
                "custo_mediano"
            ),
            compacto=False,
        ),
    )

with c3:
    st.metric(
        "Emissões em até 7 dias",
        percentual_br(
            pct_ate_7
        ),
    )


c4, c5, c6 = st.columns(
    3
)

with c4:
    st.metric(
        "Registros com antecedência válida",
        inteiro_br(
            validos
        ),
    )

with c5:
    st.metric(
        "Emissões após o início",
        percentual_br(
            pct_apos_inicio
        ),
    )

with c6:
    st.metric(
        "Sem antecedência calculável",
        inteiro_br(
            sem_antecedencia
        ),
    )


st.divider()


# CUSTO × ANTECEDÊNCIA

titulo_secao(
    "Antecedência e valor da passagem",
    (
        "Comparação entre média, mediana "
        "e volume das emissões."
    ),
)


g1, g2 = st.columns(
    2
)


with g1:
    st.plotly_chart(
        grafico_custo_antecedencia(
            df_faixas
        ),
        width="stretch",
    )


with g2:
    st.plotly_chart(
        grafico_volume_antecedencia(
            df_faixas
        ),
        width="stretch",
    )


# INTERPRETAÇÃO

nota_metodologica(
    """
    Nas emissões com antecedência válida, valores médios e
    medianos tendem a ser maiores nas faixas mais próximas
    ao início da viagem. Esse padrão representa uma
    <strong>associação observada</strong> e não demonstra,
    isoladamente, que menor antecedência seja a causa do
    maior preço.
    """
)


st.divider()


# URGÊNCIA

titulo_secao(
    "Urgência e antecedência",
    (
        "Distribuição das emissões segundo a "
        "classificação de urgência do processo."
    ),
)


st.plotly_chart(
    grafico_urgencia_antecedencia(
        mart_filtrado
    ),
    width="stretch",
)


# MODAIS

titulo_secao(
    "Comportamento por modal",
    (
        "Custo médio dos modais presentes "
        "nos registros de passagem detalhada."
    ),
)


st.plotly_chart(
    grafico_modal_custo(
        mart_filtrado
    ),
    width="stretch",
)


# DETALHAMENTO DAS FAIXAS

titulo_secao(
    "Detalhamento por faixa",
    (
        "Valores calculados diretamente sobre "
        "os registros compatíveis com os filtros."
    ),
)


nomes_faixa = {
    "0_A_3_DIAS":
        "0–3 dias",

    "4_A_7_DIAS":
        "4–7 dias",

    "8_A_14_DIAS":
        "8–14 dias",

    "15_A_30_DIAS":
        "15–30 dias",

    "MAIS_DE_30_DIAS":
        "Mais de 30 dias",

    "EMISSAO_APOS_INICIO":
        "Após o início",

    "SEM_INFORMACAO":
        "Sem informação",
}


tabela = df_faixas.copy()

tabela[
    "Faixa"
] = (
    tabela[
        "faixa_antecedencia"
    ]
    .map(
        nomes_faixa
    )
)


tabela = tabela[
    [
        "Faixa",
        "qtd_registros",
        "qtd_processos",
        "custo_medio_passagem",
        "custo_mediano_passagem",
        "antecedencia_media_dias",
        "antecedencia_mediana_dias",
    ]
].rename(
    columns={
        "qtd_registros":
            "Registros",

        "qtd_processos":
            "Processos",

        "custo_medio_passagem":
            "Custo médio",

        "custo_mediano_passagem":
            "Custo mediano",

        "antecedencia_media_dias":
            "Antecedência média",

        "antecedencia_mediana_dias":
            "Antecedência mediana",
    }
)


st.dataframe(
    tabela,
    width="stretch",
    hide_index=True,
    column_config={
        "Registros":
            st.column_config.NumberColumn(
                format="%d",
            ),

        "Processos":
            st.column_config.NumberColumn(
                format="%d",
            ),

        "Custo médio":
            st.column_config.NumberColumn(
                format="R$ %.2f",
            ),

        "Custo mediano":
            st.column_config.NumberColumn(
                format="R$ %.2f",
            ),

        "Antecedência média":
            st.column_config.NumberColumn(
                format="%.1f dias",
            ),

        "Antecedência mediana":
            st.column_config.NumberColumn(
                format="%.1f dias",
            ),
    },
)


st.divider()


# METODOLOGIA

with st.expander(
    "Como interpretar esta análise"
):
    st.markdown(
        """
        **Antecedência**

        Corresponde à diferença, em dias, entre a data de
        emissão da passagem e a data de início do processo
        de viagem.

        **Faixas principais**

        A análise de planejamento utiliza apenas valores
        maiores ou iguais a zero: 0–3, 4–7, 8–14,
        15–30 e mais de 30 dias.

        **Emissão após o início**

        Registros com antecedência negativa permanecem
        separados. Eles não são classificados
        automaticamente como erro, pois podem representar
        alterações, reemissões ou outros eventos
        operacionais não identificáveis pela base.

        **Sem informação**

        Ocorre quando não existe informação suficiente
        para calcular a antecedência.

        **Custo**

        Nesta página utiliza-se o detalhamento existente
        em `FatoPassagem`. Ele não representa toda a
        cobertura financeira de pagamentos de passagens.

        **Causalidade**

        Comparações de preço entre faixas demonstram
        associação estatística observada. Outros fatores,
        como rota, modal, sazonalidade, disponibilidade e
        características da viagem, também podem afetar
        os valores.
        """
    )


st.caption(
    "Fonte analítica: FatoPassagem, "
    "FatoProcessoViagem e mart_antecedencia.parquet. "
    "Escopo histórico: 2022–2025."
)
