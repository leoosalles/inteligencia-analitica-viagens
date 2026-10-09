import pandas as pd
import streamlit as st

from dashboard.charts import (
    grafico_composicao_financeira_orgao,
    grafico_orgaos_processos,
    grafico_orgaos_valor,
    grafico_urgencia_orgaos,
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
    carregar_orgaos,
)
from dashboard.formatters import (
    inteiro_br,
    moeda_br,
    percentual_br,
)


# CABEÇALHO

cabecalho_pagina(
    titulo="Órgãos e Operação",
    subtitulo=(
        "Análise da distribuição financeira e "
        "operacional entre as estruturas "
        "organizacionais presentes nos dados."
    ),
)


# CARREGAMENTO

try:
    df = (
        carregar_orgaos()
        .copy()
    )

except FileNotFoundError as exc:
    st.error(
        str(exc)
    )
    st.stop()


# FILTROS GLOBAIS

st.sidebar.header(
    "Filtros"
)


anos_disponiveis = sorted(
    int(x)
    for x in df[
        "ano_fonte"
    ].unique()
    if int(x) in ANOS_HISTORICOS
)


anos_selecionados = (
    st.sidebar.multiselect(
        "Ano",
        options=anos_disponiveis,
        default=anos_disponiveis,
        key="orgaos_anos",
    )
)


if not anos_selecionados:
    anos_selecionados = (
        anos_disponiveis
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
        key="orgaos_top_n",
    )
)


df = df[
    df[
        "ano_fonte"
    ].isin(
        anos_selecionados
    )
].copy()


# ABAS

aba_financeira, aba_operacional = (
    st.tabs(
        [
            "Financeiro",
            "Operacional",
        ]
    )
)


# ABA FINANCEIRA

with aba_financeira:

    titulo_secao(
        "Perspectiva financeira",
        (
            "Valores registrados em Pagamento "
            "segundo diferentes estruturas "
            "organizacionais."
        ),
    )


    # PERSPECTIVA

    perspectivas = {
        "Órgão superior":
            "ORGAO_SUPERIOR_FINANCEIRO",

        "Órgão pagador":
            "ORGAO_PAGADOR_FINANCEIRO",

        "Unidade gestora pagadora":
            "UNIDADE_GESTORA_PAGADORA_FINANCEIRO",
    }


    nome_perspectiva = st.selectbox(
        "Agrupar por",
        options=list(
            perspectivas.keys()
        ),
        key="orgaos_perspectiva_financeira",
        help=(
            "Seleciona a estrutura organizacional "
            "pela qual os pagamentos serão analisados."
        ),
    )


    codigo_perspectiva = (
        perspectivas[
            nome_perspectiva
        ]
    )


    financeiro = df[
        df[
            "perspectiva"
        ]
        == codigo_perspectiva
    ].copy()


    # SELETOR DE ORGANIZAÇÃO

    org_lookup = (
        financeiro[
            [
                "sk_organizacao",
                "codigo_organizacao",
                "nome_organizacao",
            ]
        ]
        .drop_duplicates(
            subset=[
                "sk_organizacao"
            ]
        )
        .copy()
    )


    def criar_rotulo_organizacao(row):

        nome = row[
            "nome_organizacao"
        ]

        codigo = row[
            "codigo_organizacao"
        ]

        if pd.isna(nome):
            nome = "Não informado"

        else:
            nome = str(
                nome
            ).strip()

        if (
            pd.isna(codigo)
            or str(codigo).strip() == ""
        ):
            return nome

        return (
            f"{nome} — "
            f"{str(codigo).strip()}"
        )


    org_lookup[
        "rotulo"
    ] = org_lookup.apply(
        criar_rotulo_organizacao,
        axis=1,
    )


    org_lookup[
        "sk_texto"
    ] = (
        org_lookup[
            "sk_organizacao"
        ]
        .astype(str)
    )


    org_lookup = (
        org_lookup
        .sort_values(
            "rotulo"
        )
    )


    mapa_organizacoes = dict(
        zip(
            org_lookup[
                "sk_texto"
            ],
            org_lookup[
                "rotulo"
            ],
        )
    )


    TODAS_ORGANIZACOES = (
        "__TODAS_ORGANIZACOES__"
    )


    opcoes_organizacao = [
        TODAS_ORGANIZACOES
    ] + list(
        org_lookup[
            "sk_texto"
        ]
    )


    organizacao_selecionada = (
        st.selectbox(
            "Organização",
            options=opcoes_organizacao,
            format_func=lambda valor: (
                "Todas as organizações"
                if valor
                == TODAS_ORGANIZACOES
                else mapa_organizacoes.get(
                    valor,
                    valor,
                )
            ),
            key="orgaos_organizacao_financeira",
            help=(
                "Selecione uma organização específica "
                "para recalcular os indicadores "
                "financeiros."
            ),
        )
    )


    # APLICA FILTRO DA ORGANIZAÇÃO

    if (
        organizacao_selecionada
        == TODAS_ORGANIZACOES
    ):

        financeiro_selecionado = (
            financeiro.copy()
        )

        nome_organizacao_selecionada = (
            "Todas as organizações"
        )

    else:

        financeiro_selecionado = (
            financeiro[
                financeiro[
                    "sk_organizacao"
                ].astype(str)
                == organizacao_selecionada
            ]
            .copy()
        )

        nome_organizacao_selecionada = (
            mapa_organizacoes.get(
                organizacao_selecionada,
                organizacao_selecionada,
            )
        )


    # KPIs FINANCEIROS

    valor_total = float(
        pd.to_numeric(
            financeiro_selecionado[
                "valor_total"
            ],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )


    valor_diarias = float(
        pd.to_numeric(
            financeiro_selecionado[
                "valor_diarias"
            ],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )


    valor_passagens = float(
        pd.to_numeric(
            financeiro_selecionado[
                "valor_passagens"
            ],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )


    valor_restituicao = float(
        pd.to_numeric(
            financeiro_selecionado[
                "valor_restituicao"
            ],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )


    valor_seguro = float(
        pd.to_numeric(
            financeiro_selecionado[
                "valor_seguro"
            ],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )


    if (
        organizacao_selecionada
        == TODAS_ORGANIZACOES
    ):

        st.caption(
            "Os cartões abaixo representam o total "
            "do período. Como as perspectivas são "
            "formas diferentes de agrupar o mesmo "
            "universo de pagamentos, o total geral "
            "permanece igual entre elas."
        )

    else:

        st.caption(
            f"Indicadores filtrados para: "
            f"{nome_organizacao_selecionada}."
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
            "Passagens",
            moeda_br(
                valor_passagens,
                compacto=True,
            ),
        )


    with c3:
        st.metric(
            "Diárias",
            moeda_br(
                valor_diarias,
                compacto=True,
            ),
        )


    c4, c5 = st.columns(
        2
    )


    with c4:
        st.metric(
            "Restituições",
            moeda_br(
                valor_restituicao,
                compacto=True,
            ),
        )


    with c5:
        st.metric(
            "Seguro",
            moeda_br(
                valor_seguro,
                compacto=True,
            ),
        )


    st.divider()


    # RANKINGS

    titulo_secao(
        "Concentração organizacional",
        (
            f"Ranking segundo a perspectiva: "
            f"{nome_perspectiva}."
        ),
    )


    st.caption(
        "O filtro de organização afeta os cartões e o "
        "detalhamento. O ranking permanece referente ao "
        "conjunto completo da perspectiva selecionada."
    )


    g1, g2 = st.columns(
        2
    )


    with g1:
        st.plotly_chart(
            grafico_orgaos_valor(
                financeiro,
                top_n=top_n,
            ),
            width="stretch",
        )


    with g2:
        st.plotly_chart(
            grafico_orgaos_processos(
                financeiro,
                top_n=top_n,
            ),
            width="stretch",
        )


    # COMPOSIÇÃO

    titulo_secao(
        "Composição dos pagamentos",
        (
            "Distribuição entre diárias, passagens, "
            "restituições e seguro para a seleção atual."
        ),
    )


    st.plotly_chart(
        grafico_composicao_financeira_orgao(
            financeiro_selecionado
        ),
        width="stretch",
    )


    # TABELA FINANCEIRA

    titulo_secao(
        "Detalhamento financeiro",
        (
            "Valores correspondentes à organização "
            "selecionada ou ao conjunto completo."
        ),
    )


    tabela_financeira = (
        financeiro_selecionado.groupby(
            [
                "sk_organizacao",
                "codigo_organizacao",
                "nome_organizacao",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            qtd_processos=(
                "qtd_processos",
                "sum",
            ),
            valor_total=(
                "valor_total",
                "sum",
            ),
            valor_diarias=(
                "valor_diarias",
                "sum",
            ),
            valor_passagens=(
                "valor_passagens",
                "sum",
            ),
            valor_restituicao=(
                "valor_restituicao",
                "sum",
            ),
            valor_seguro=(
                "valor_seguro",
                "sum",
            ),
        )
        .sort_values(
            "valor_total",
            ascending=False,
        )
    )


    tabela_financeira = (
        tabela_financeira[
            [
                "codigo_organizacao",
                "nome_organizacao",
                "qtd_processos",
                "valor_total",
                "valor_diarias",
                "valor_passagens",
                "valor_restituicao",
                "valor_seguro",
            ]
        ]
        .rename(
            columns={
                "codigo_organizacao":
                    "Código",

                "nome_organizacao":
                    "Organização",

                "qtd_processos":
                    "Processos",

                "valor_total":
                    "Valor registrado",

                "valor_diarias":
                    "Diárias",

                "valor_passagens":
                    "Passagens",

                "valor_restituicao":
                    "Restituições",

                "valor_seguro":
                    "Seguro",
            }
        )
        .reset_index(
            drop=True
        )
    )


    tabela_financeira_exibicao = (
        tabela_financeira.copy()
    )


    tabela_financeira_exibicao[
        "Processos"
    ] = (
        tabela_financeira_exibicao[
            "Processos"
        ]
        .map(
            inteiro_br
        )
    )


    colunas_financeiras = [
        "Valor registrado",
        "Diárias",
        "Passagens",
        "Restituições",
        "Seguro",
    ]


    for coluna in colunas_financeiras:

        tabela_financeira_exibicao[
            coluna
        ] = (
            tabela_financeira_exibicao[
                coluna
            ]
            .map(
                lambda valor:
                    moeda_br(
                        valor,
                        compacto=False,
                    )
            )
        )


    st.dataframe(
        tabela_financeira_exibicao,
        width="stretch",
        hide_index=True,
        column_config={
            "Código":
                st.column_config.TextColumn(
                    "Código",
                    width="small",
                ),

            "Organização":
                st.column_config.TextColumn(
                    "Organização",
                    width="large",
                ),

            "Processos":
                st.column_config.TextColumn(
                    "Processos",
                    width="small",
                ),

            "Valor registrado":
                st.column_config.TextColumn(
                    "Valor registrado",
                    width="medium",
                ),

            "Diárias":
                st.column_config.TextColumn(
                    "Diárias",
                    width="medium",
                ),

            "Passagens":
                st.column_config.TextColumn(
                    "Passagens",
                    width="medium",
                ),

            "Restituições":
                st.column_config.TextColumn(
                    "Restituições",
                    width="medium",
                ),

            "Seguro":
                st.column_config.TextColumn(
                    "Seguro",
                    width="medium",
                ),
        },
    )


# ABA OPERACIONAL

with aba_operacional:

    titulo_secao(
        "Perspectiva operacional",
        (
            "Análise dos órgãos solicitantes "
            "e da classificação de urgência."
        ),
    )


    operacional = df[
        df[
            "perspectiva"
        ]
        == "ORGAO_SOLICITANTE_OPERACIONAL"
    ].copy()


    qtd_processos = float(
        pd.to_numeric(
            operacional[
                "qtd_processos"
            ],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )


    qtd_urgentes = float(
        pd.to_numeric(
            operacional[
                "qtd_processos_urgentes"
            ],
            errors="coerce",
        )
        .fillna(0)
        .sum()
    )


    pct_urgentes = (
        100.0
        * qtd_urgentes
        / qtd_processos
        if qtd_processos
        else None
    )


    qtd_orgaos = (
        operacional[
            "sk_organizacao"
        ]
        .nunique()
    )


    c1, c2, c3 = st.columns(
        3
    )


    with c1:
        st.metric(
            "Processos",
            inteiro_br(
                qtd_processos
            ),
        )


    with c2:
        st.metric(
            "Órgãos solicitantes",
            inteiro_br(
                qtd_orgaos
            ),
        )


    with c3:
        st.metric(
            "Processos urgentes",
            percentual_br(
                pct_urgentes
            ),
        )


    st.divider()


    # VOLUME

    titulo_secao(
        "Volume por órgão solicitante",
        (
            "Órgãos com maior quantidade "
            "de processos."
        ),
    )


    st.plotly_chart(
        grafico_orgaos_processos(
            operacional,
            top_n=top_n,
        ),
        width="stretch",
    )


    # URGÊNCIA

    titulo_secao(
        "Urgência operacional",
        (
            "Percentual de processos urgentes "
            "entre os órgãos de maior volume."
        ),
    )


    st.plotly_chart(
        grafico_urgencia_orgaos(
            operacional,
            top_n=top_n,
        ),
        width="stretch",
    )


    # TABELA OPERACIONAL

    titulo_secao(
        "Detalhamento operacional",
        (
            "Volume e urgência por órgão "
            "solicitante."
        ),
    )


    tabela_operacional = (
        operacional.groupby(
            [
                "sk_organizacao",
                "codigo_organizacao",
                "nome_organizacao",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            qtd_processos=(
                "qtd_processos",
                "sum",
            ),
            qtd_urgentes=(
                "qtd_processos_urgentes",
                "sum",
            ),
        )
    )


    tabela_operacional[
        "pct_urgentes"
    ] = (
        100.0
        * tabela_operacional[
            "qtd_urgentes"
        ]
        / tabela_operacional[
            "qtd_processos"
        ].replace(
            0,
            float("nan"),
        )
    )


    tabela_operacional = (
        tabela_operacional[
            [
                "codigo_organizacao",
                "nome_organizacao",
                "qtd_processos",
                "qtd_urgentes",
                "pct_urgentes",
            ]
        ]
        .rename(
            columns={
                "codigo_organizacao":
                    "Código",

                "nome_organizacao":
                    "Órgão solicitante",

                "qtd_processos":
                    "Processos",

                "qtd_urgentes":
                    "Urgentes",

                "pct_urgentes":
                    "Urgência (%)",
            }
        )
        .sort_values(
            "Processos",
            ascending=False,
        )
    )


    st.dataframe(
        tabela_operacional,
        width="stretch",
        hide_index=True,
        column_config={
            "Processos":
                st.column_config.NumberColumn(
                    format="%d",
                ),

            "Urgentes":
                st.column_config.NumberColumn(
                    format="%d",
                ),

            "Urgência (%)":
                st.column_config.NumberColumn(
                    format="%.2f%%",
                ),
        },
    )


# METODOLOGIA

st.divider()


with st.expander(
    "Como interpretar esta página"
):

    st.markdown(
        """
        **Agrupar por**
        Define qual papel organizacional será utilizado
        para analisar os mesmos registros financeiros:
        órgão superior, órgão pagador ou unidade gestora
        pagadora.

        **Organização**
        Permite restringir os indicadores financeiros a
        uma organização específica da perspectiva escolhida.

        **Totais globais**
        Quando a opção `Todas as organizações` está ativa,
        os valores totais permanecem iguais entre as
        perspectivas. Isso é esperado, pois são formas
        diferentes de agrupar o mesmo universo de
        pagamentos.

        **Perspectiva operacional**
        Utiliza o órgão solicitante associado ao processo
        de viagem.

        **Separação das perspectivas**
        Não atribuímos automaticamente ao órgão solicitante
        os valores financeiros registrados por outra
        estrutura organizacional.

        **Urgência**
        O percentual representa processos classificados
        como urgentes na fonte e não constitui avaliação
        sobre a necessidade ou mérito da viagem.
        """
    )


nota_metodologica(
    """
    As perspectivas <strong>financeira</strong> e
    <strong>operacional</strong> representam papéis
    administrativos diferentes. A seleção de uma perspectiva
    altera a forma de agrupamento dos pagamentos; a seleção
    de uma organização específica é que restringe o universo
    financeiro utilizado nos cartões.
    """
)


st.caption(
    "Fonte analítica: mart_orgaos.parquet. "
    "Escopo histórico: 2022–2025."
)