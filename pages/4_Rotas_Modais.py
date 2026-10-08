import streamlit as st

from dashboard.charts import (
    grafico_custo_modal_rotas,
    grafico_distribuicao_modais,
    grafico_top_destinos,
    grafico_top_origens,
    grafico_top_rotas,
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
    carregar_modais,
    consultar_filtros_rotas,
    consultar_modais_resumo,
    consultar_resumo_rotas,
    consultar_top_destinos,
    consultar_top_origens,
    consultar_top_rotas,
)
from dashboard.formatters import (
    inteiro_br,
)


# CABEÇALHO

cabecalho_pagina(
    titulo="Rotas e Modais",
    subtitulo=(
        "Análise dos padrões de deslocamento, "
        "principais origens, destinos, rotas "
        "e meios de transporte."
    ),
)


# CARREGAMENTO INICIAL

try:
    df_modais_base = (
        carregar_modais()
        .copy()
    )

    filtros_disponiveis = (
        consultar_filtros_rotas()
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
    for x in df_modais_base[
        "ano_fonte"
    ].unique()
    if int(x) in ANOS_HISTORICOS
)


anos_selecionados = (
    st.sidebar.multiselect(
        "Ano",
        options=anos_disponiveis,
        default=anos_disponiveis,
        key="rotas_anos",
    )
)


if not anos_selecionados:
    anos_selecionados = (
        anos_disponiveis
    )


modais_disponiveis = sorted(
    str(x)
    for x in df_modais_base[
        "modal"
    ].dropna().unique()
    if str(x) != "INVÁLIDO"
)


modais_selecionados = (
    st.sidebar.multiselect(
        "Modal",
        options=modais_disponiveis,
        default=modais_disponiveis,
        key="rotas_modais",
    )
)


if not modais_selecionados:
    modais_selecionados = (
        modais_disponiveis
    )


incluir_invalidos = (
    st.sidebar.checkbox(
        "Incluir modal INVÁLIDO",
        value=False,
        key="rotas_invalidos",
    )
)


# LOCALIDADES

paises_origem = (
    filtros_disponiveis[
        "paises_origem"
    ]
)

paises_destino = (
    filtros_disponiveis[
        "paises_destino"
    ]
)

ufs_origem = (
    filtros_disponiveis[
        "ufs_origem"
    ]
)

ufs_destino = (
    filtros_disponiveis[
        "ufs_destino"
    ]
)


origem_pais = (
    st.sidebar.selectbox(
        "País de origem",
        options=[
            "Todos"
        ] + paises_origem,
        key="rotas_origem_pais",
    )
)


origem_uf = (
    st.sidebar.selectbox(
        "UF de origem",
        options=[
            "Todas"
        ] + ufs_origem,
        key="rotas_origem_uf",
    )
)


destino_pais = (
    st.sidebar.selectbox(
        "País de destino",
        options=[
            "Todos"
        ] + paises_destino,
        key="rotas_destino_pais",
    )
)


destino_uf = (
    st.sidebar.selectbox(
        "UF de destino",
        options=[
            "Todas"
        ] + ufs_destino,
        key="rotas_destino_uf",
    )
)


origem_pais_sql = (
    None
    if origem_pais == "Todos"
    else origem_pais
)

origem_uf_sql = (
    None
    if origem_uf == "Todas"
    else origem_uf
)

destino_pais_sql = (
    None
    if destino_pais == "Todos"
    else destino_pais
)

destino_uf_sql = (
    None
    if destino_uf == "Todas"
    else destino_uf
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
        key="rotas_top_n",
    )
)


# CONSULTAS

with st.spinner(
    "Consultando rotas..."
):
    parametros = dict(
        anos_tuple=tuple(
            sorted(
                anos_selecionados
            )
        ),
        modais_tuple=tuple(
            sorted(
                modais_selecionados
            )
        ),
        origem_pais=origem_pais_sql,
        origem_uf=origem_uf_sql,
        destino_pais=destino_pais_sql,
        destino_uf=destino_uf_sql,
        incluir_invalidos=incluir_invalidos,
    )

    resumo = consultar_resumo_rotas(
        **parametros
    )

    df_origens = consultar_top_origens(
        **parametros,
        top_n=top_n,
    )

    df_destinos = consultar_top_destinos(
        **parametros,
        top_n=top_n,
    )

    df_rotas = consultar_top_rotas(
        **parametros,
        top_n=top_n,
    )

    df_modais = consultar_modais_resumo(
        tuple(
            sorted(
                anos_selecionados
            )
        ),
        incluir_invalidos,
    )


# KPIs

titulo_secao(
    "Panorama dos deslocamentos",
    (
        "Indicadores calculados sobre os "
        "trechos compatíveis com os filtros."
    ),
)


c1, c2, c3, c4 = st.columns(
    4
)


with c1:
    st.metric(
        "Trechos",
        inteiro_br(
            resumo.get(
                "qtd_trechos"
            )
        ),
    )


with c2:
    st.metric(
        "Origens distintas",
        inteiro_br(
            resumo.get(
                "qtd_origens"
            )
        ),
    )


with c3:
    st.metric(
        "Destinos distintos",
        inteiro_br(
            resumo.get(
                "qtd_destinos"
            )
        ),
    )


with c4:
    st.metric(
        "Rotas origem → destino",
        inteiro_br(
            resumo.get(
                "qtd_rotas"
            )
        ),
    )


st.divider()


# ORIGENS E DESTINOS

titulo_secao(
    "Principais localidades",
    (
        "Ranking de origens e destinos "
        "pela quantidade de trechos."
    ),
)


g1, g2 = st.columns(
    2
)


with g1:
    st.plotly_chart(
        grafico_top_origens(
            df_origens
        ),
        width="stretch",
    )


with g2:
    st.plotly_chart(
        grafico_top_destinos(
            df_destinos
        ),
        width="stretch",
    )


# ROTAS

titulo_secao(
    "Principais rotas",
    (
        "Pares de origem e destino com "
        "maior quantidade de trechos."
    ),
)


st.plotly_chart(
    grafico_top_rotas(
        df_rotas
    ),
    width="stretch",
)


st.divider()


# MODAIS

titulo_secao(
    "Meios de transporte",
    (
        "Distribuição operacional dos trechos "
        "e custo médio onde existe detalhamento "
        "de passagem."
    ),
)


m1, m2 = st.columns(
    2
)


with m1:
    st.plotly_chart(
        grafico_distribuicao_modais(
            df_modais
        ),
        width="stretch",
    )


with m2:
    st.plotly_chart(
        grafico_custo_modal_rotas(
            df_modais
        ),
        width="stretch",
    )


# TABELA DE ROTAS

titulo_secao(
    "Ranking detalhado",
    (
        "Principais pares origem → destino "
        "segundo os filtros selecionados."
    ),
)


tabela = df_rotas.copy()


def formatar_local(
    row,
    prefixo,
):
    cidade = row.get(
        f"{prefixo}_cidade"
    )

    uf = row.get(
        f"{prefixo}_uf"
    )

    pais = row.get(
        f"{prefixo}_pais"
    )

    partes = []

    if cidade:
        partes.append(
            str(cidade)
        )

    if uf:
        partes.append(
            str(uf)
        )

    if not partes and pais:
        partes.append(
            str(pais)
        )

    return (
        " / ".join(partes)
        if partes
        else "Não informado"
    )


if not tabela.empty:
    tabela["Origem"] = tabela.apply(
        lambda row:
            formatar_local(
                row,
                "origem",
            ),
        axis=1,
    )

    tabela["Destino"] = tabela.apply(
        lambda row:
            formatar_local(
                row,
                "destino",
            ),
        axis=1,
    )

    tabela = tabela[
        [
            "Origem",
            "Destino",
            "qtd_trechos",
        ]
    ].rename(
        columns={
            "qtd_trechos":
                "Trechos",
        }
    )


st.dataframe(
    tabela,
    width="stretch",
    hide_index=True,
    column_config={
        "Trechos":
            st.column_config.NumberColumn(
                format="%d",
            ),
    },
)


st.divider()


# METODOLOGIA

with st.expander(
    "Como interpretar esta página"
):
    st.markdown(
        """
        **Trecho**

        Corresponde a uma observação da fonte `Trecho`,
        preservando a multiplicidade original.

        **Rota**

        É definida como o par localidade de origem →
        localidade de destino.

        **Ranking**

        Os rankings são calculados pela quantidade de
        trechos, uma medida aditiva e adequada para
        agregações de origem, destino e rota.

        **Processos**

        Não somamos indiscriminadamente contagens de
        processos entre diferentes rotas, pois um mesmo
        processo pode possuir vários trechos e aparecer em
        mais de uma combinação origem-destino.

        **Modal INVÁLIDO**

        A categoria é preservada exatamente como observada
        na fonte, mas fica excluída dos gráficos por padrão.

        **Custo por modal**

        Utiliza apenas os registros que possuem
        detalhamento na fonte `Passagem`. Portanto, não
        representa necessariamente todo o valor financeiro
        registrado em pagamentos.
        """
    )


nota_metodologica(
    """
    Os rankings desta página descrevem a
    <strong>frequência observada de trechos</strong>.
    Eles não devem ser interpretados automaticamente como
    demanda comercial, número de passageiros únicos ou
    quantidade de bilhetes emitidos.
    """
)


st.caption(
    "Fonte analítica: mart_rotas.parquet e "
    "mart_modais.parquet. "
    "Escopo histórico: 2022–2025."
)
