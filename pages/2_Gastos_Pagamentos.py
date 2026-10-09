import pandas as pd
import streamlit as st

from dashboard.charts import (
    grafico_evolucao_categoria,
    grafico_participacao_categorias,
    grafico_top_orgaos,
    grafico_top_orgaos_processos,
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
    carregar_gastos,
    carregar_orgaos,
)
from dashboard.formatters import (
    inteiro_br,
    moeda_br,
    percentual_br,
)


# CABEÇALHO

cabecalho_pagina(
    titulo="Gastos e Pagamentos",
    subtitulo=(
        "Análise dos valores registrados em pagamentos, "
        "sua composição e distribuição organizacional."
    ),
)


# CARREGAMENTO

try:
    df_gastos = (
        carregar_gastos()
        .sort_values(
            [
                "ano_fonte",
                "codigo_tipo_pagamento",
            ]
        )
    )

    df_orgaos = (
        carregar_orgaos()
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
    for x in df_gastos[
        "ano_fonte"
    ].unique()
    if int(x) in ANOS_HISTORICOS
)


anos_selecionados = (
    st.sidebar.multiselect(
        "Ano",
        options=anos_disponiveis,
        default=anos_disponiveis,
        key="gastos_anos",
    )
)


if not anos_selecionados:
    anos_selecionados = (
        anos_disponiveis
    )


categorias_disponiveis = [
    "DIARIAS",
    "PASSAGEM",
    "RESTITUICAO",
    "SEGURO",
]


nomes_categorias = {
    "DIARIAS":
        "Diárias",

    "PASSAGEM":
        "Passagens",

    "RESTITUICAO":
        "Restituições",

    "SEGURO":
        "Seguro",
}


categorias_selecionadas = (
    st.sidebar.multiselect(
        "Categoria de pagamento",
        options=categorias_disponiveis,
        default=categorias_disponiveis,
        format_func=lambda x:
            nomes_categorias.get(
                x,
                x,
            ),
        key="gastos_categorias",
    )
)


if not categorias_selecionadas:
    categorias_selecionadas = (
        categorias_disponiveis
    )


perspectivas_financeiras = {
    "Órgão superior":
        "ORGAO_SUPERIOR_FINANCEIRO",

    "Órgão pagador":
        "ORGAO_PAGADOR_FINANCEIRO",

    "Unidade gestora pagadora":
        "UNIDADE_GESTORA_PAGADORA_FINANCEIRO",
}


nome_perspectiva = (
    st.sidebar.selectbox(
        "Perspectiva organizacional",
        options=list(
            perspectivas_financeiras.keys()
        ),
    )
)


perspectiva = (
    perspectivas_financeiras[
        nome_perspectiva
    ]
)


top_n = (
    st.sidebar.select_slider(
        "Quantidade no ranking",
        options=[
            5,
            10,
            15,
            20,
            30,
            50,
        ],
        value=10,
    )
)


# FILTRAGEM

gastos = df_gastos[
    df_gastos[
        "ano_fonte"
    ].isin(
        anos_selecionados
    )
    &
    df_gastos[
        "codigo_tipo_pagamento"
    ].isin(
        categorias_selecionadas
    )
].copy()


orgaos = df_orgaos[
    df_orgaos[
        "ano_fonte"
    ].isin(
        anos_selecionados
    )
    &
    (
        df_orgaos[
            "perspectiva"
        ]
        == perspectiva
    )
].copy()


# FUNÇÕES

def soma_numerica(
    df,
    coluna,
):
    return float(
        pd.to_numeric(
            df[
                coluna
            ],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )


# KPIs

valor_total = soma_numerica(
    gastos,
    "valor_total",
)


qtd_registros = soma_numerica(
    gastos,
    "qtd_registros_pagamento",
)


valor_diarias = soma_numerica(
    gastos[
        gastos[
            "codigo_tipo_pagamento"
        ] == "DIARIAS"
    ],
    "valor_total",
)


valor_passagens = soma_numerica(
    gastos[
        gastos[
            "codigo_tipo_pagamento"
        ] == "PASSAGEM"
    ],
    "valor_total",
)


valor_restituicao = soma_numerica(
    gastos[
        gastos[
            "codigo_tipo_pagamento"
        ] == "RESTITUICAO"
    ],
    "valor_total",
)


valor_seguro = soma_numerica(
    gastos[
        gastos[
            "codigo_tipo_pagamento"
        ] == "SEGURO"
    ],
    "valor_total",
)


# CARTÕES

titulo_secao(
    "Síntese financeira",
    (
        "Valores agregados conforme o período "
        "e as categorias selecionadas."
    ),
)


c1, c2, c3 = st.columns(
    3
)


with c1:
    st.metric(
        "Valor registrado",
        moeda_br(
            valor_total,
            compacto=True,
        ),
    )


with c2:
    st.metric(
        "Registros de pagamento",
        inteiro_br(
            qtd_registros
        ),
    )


with c3:
    if valor_total > 0:
        participacao_passagens = (
            100.0
            * valor_passagens
            / valor_total
        )
    else:
        participacao_passagens = None

    st.metric(
        "Participação de passagens",
        percentual_br(
            participacao_passagens
        ),
    )


c4, c5 = st.columns(
    2
)


with c4:
    st.metric(
        "Diárias",
        moeda_br(
            valor_diarias,
            compacto=True,
        ),
    )


with c5:
    st.metric(
        "Passagens",
        moeda_br(
            valor_passagens,
            compacto=True,
        ),
    )


c6, c7 = st.columns(
    2
)


with c6:
    st.metric(
        "Restituições",
        moeda_br(
            valor_restituicao,
            compacto=True,
        ),
    )


with c7:
    st.metric(
        "Seguro",
        moeda_br(
            valor_seguro,
            compacto=True,
        ),
    )


st.divider()


# EVOLUÇÃO

titulo_secao(
    "Evolução e composição",
    (
        "Comparação das categorias de pagamento "
        "ao longo da série histórica."
    ),
)


g1, g2 = st.columns(
    [
        1.6,
        1,
    ]
)


with g1:
    st.plotly_chart(
        grafico_evolucao_categoria(
            gastos
        ),
        width="stretch",
    )


with g2:
    st.plotly_chart(
        grafico_participacao_categorias(
            gastos
        ),
        width="stretch",
    )


# TABELA POR CATEGORIA

titulo_secao(
    "Detalhamento por categoria",
    (
        "Valores e participação conforme os "
        "filtros atualmente aplicados."
    ),
)


tabela_categoria = (
    gastos.groupby(
        [
            "codigo_tipo_pagamento",
            "descricao_tipo_pagamento",
        ],
        as_index=False,
    )
    .agg(
        valor_total=(
            "valor_total",
            "sum",
        ),
        qtd_registros=(
            "qtd_registros_pagamento",
            "sum",
        ),
    )
)


total_tabela = (
    tabela_categoria[
        "valor_total"
    ].sum()
)


if total_tabela:
    tabela_categoria[
        "participacao_pct"
    ] = (
        100.0
        * tabela_categoria[
            "valor_total"
        ]
        / total_tabela
    )

else:
    tabela_categoria[
        "participacao_pct"
    ] = 0.0


tabela_exibicao = (
    tabela_categoria[
        [
            "descricao_tipo_pagamento",
            "qtd_registros",
            "valor_total",
            "participacao_pct",
        ]
    ]
    .rename(
        columns={
            "descricao_tipo_pagamento":
                "Categoria",

            "qtd_registros":
                "Registros",

            "valor_total":
                "Valor registrado",

            "participacao_pct":
                "Participação (%)",
        }
    )
    .sort_values(
        "Valor registrado",
        ascending=False,
    )
    .reset_index(
        drop=True
    )
)


tabela_exibicao[
    "Registros"
] = (
    tabela_exibicao[
        "Registros"
    ]
    .map(
        inteiro_br
    )
)


tabela_exibicao[
    "Valor registrado"
] = (
    tabela_exibicao[
        "Valor registrado"
    ]
    .map(
        lambda valor:
            moeda_br(
                valor,
                compacto=False,
            )
    )
)


tabela_exibicao[
    "Participação (%)"
] = (
    tabela_exibicao[
        "Participação (%)"
    ]
    .map(
        lambda valor:
            percentual_br(
                valor,
                casas=2,
            )
    )
)


st.dataframe(
    tabela_exibicao,
    width="stretch",
    hide_index=True,
    column_config={
        "Categoria":
            st.column_config.TextColumn(
                "Categoria",
                width="medium",
            ),

        "Registros":
            st.column_config.TextColumn(
                "Registros",
                width="small",
            ),

        "Valor registrado":
            st.column_config.TextColumn(
                "Valor registrado",
                width="medium",
            ),

        "Participação (%)":
            st.column_config.TextColumn(
                "Participação (%)",
                width="small",
            ),
    },
)


st.divider()


# ORGANIZAÇÕES

titulo_secao(
    "Distribuição organizacional",
    (
        f"Perspectiva selecionada: "
        f"{nome_perspectiva}."
    ),
)


if orgaos.empty:

    st.info(
        "Não há registros para os filtros "
        "selecionados."
    )

else:

    o1, o2 = st.columns(
        2
    )

    with o1:
        st.plotly_chart(
            grafico_top_orgaos(
                orgaos,
                top_n=top_n,
            ),
            width="stretch",
        )

    with o2:
        st.plotly_chart(
            grafico_top_orgaos_processos(
                orgaos,
                top_n=top_n,
            ),
            width="stretch",
        )


# METODOLOGIA

st.divider()


with st.expander(
    "Como interpretar esta página"
):

    st.markdown(
        """
        **Valor registrado**
        Corresponde à soma de `FatoPagamento.valor`
        nas categorias selecionadas.

        **Diárias e passagens**
        São classificações existentes na fonte
        `Pagamento` e constituem as referências
        financeiras principais dessas categorias.

        **Restituições**
        Não devem ser confundidas com o campo
        `Valor devolução` existente na fonte `Viagem`.

        **Seguro**
        Representa os registros classificados como
        serviço correlato de seguro. Não corresponde
        automaticamente a `Valor outros gastos`.

        **Perspectiva organizacional**
        Órgão superior, órgão pagador e unidade gestora
        pagadora são analisados separadamente, evitando
        atribuir valores a estruturas organizacionais
        distintas sem fundamento na fonte.
        """
    )


nota_metodologica(
    """
    Os valores exibidos representam <strong>registros de
    pagamento</strong> disponíveis na base. A terminologia
    financeira foi mantida deliberadamente próxima à fonte,
    evitando interpretar os totais automaticamente como
    despesa líquida, economia ou custo final.
    """
)


st.caption(
    "Fonte analítica: FatoPagamento e "
    "mart_orgaos.parquet. "
    "Escopo histórico: 2022–2025."
)