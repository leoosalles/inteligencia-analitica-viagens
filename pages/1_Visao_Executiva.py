import pandas as pd
import streamlit as st

from dashboard.charts import (
    grafico_composicao_gastos,
    grafico_indicadores_operacionais,
    grafico_pagamentos,
    grafico_processos,
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
    carregar_executivo,
    carregar_gastos,
    obter_antecedencia_mediana,
)
from dashboard.formatters import (
    delta_pct,
    dias_br,
    inteiro_br,
    moeda_br,
    percentual_br,
)


# CABEÇALHO

cabecalho_pagina(
    titulo="Visão Executiva",
    subtitulo=(
        "Síntese histórica dos processos de viagem, "
        "pagamentos e comportamento de emissão "
        "entre 2022 e 2025."
    ),
)


# CARREGAMENTO

try:
    df_exec = (
        carregar_executivo()
        .sort_values(
            "ano_fonte"
        )
    )

    df_gastos = (
        carregar_gastos()
        .sort_values(
            [
                "ano_fonte",
                "codigo_tipo_pagamento",
            ]
        )
    )

except FileNotFoundError as exc:
    st.error(
        str(exc)
    )
    st.stop()


# FILTRO DE ANO

anos_disponiveis = sorted(
    int(x)
    for x in df_exec[
        "ano_fonte"
    ].unique()
    if int(x) in ANOS_HISTORICOS
)


st.sidebar.header(
    "Filtros"
)


anos_selecionados = st.sidebar.multiselect(
    "Ano",
    options=anos_disponiveis,
    default=anos_disponiveis,
)


if not anos_selecionados:
    anos_selecionados = (
        anos_disponiveis
    )

    st.sidebar.info(
        "Nenhum ano selecionado. "
        "Exibindo toda a série histórica."
    )


df_exec_filtrado = df_exec[
    df_exec[
        "ano_fonte"
    ].isin(
        anos_selecionados
    )
].copy()


df_gastos_filtrado = df_gastos[
    df_gastos[
        "ano_fonte"
    ].isin(
        anos_selecionados
    )
].copy()


# FUNÇÕES LOCAIS

def soma(coluna):
    serie = pd.to_numeric(
        df_exec_filtrado[
            coluna
        ],
        errors="coerce",
    )

    return float(
        serie.sum()
    )


def percentual_seguro(
    numerador,
    denominador,
):
    if denominador in (
        None,
        0,
    ):
        return None

    return (
        100.0
        * float(numerador)
        / float(denominador)
    )


# KPIs AGREGADOS

qtd_processos = soma(
    "qtd_processos"
)

qtd_urgentes = soma(
    "qtd_processos_urgentes"
)

valor_total = soma(
    "valor_total_pagamentos"
)

valor_passagens = soma(
    "valor_pago_passagens"
)

valor_diarias = soma(
    "valor_pago_diarias"
)

custo_detalhado = soma(
    "custo_passagens_detalhadas"
)

antecedencia_valida = soma(
    "qtd_antecedencia_valida"
)

emissoes_ate_7 = soma(
    "qtd_emissoes_ate_7_dias"
)

emissoes_apos_inicio = soma(
    "qtd_emissoes_apos_inicio"
)

registros_passagem = soma(
    "qtd_registros_passagem_detalhada"
)


pct_urgentes = percentual_seguro(
    qtd_urgentes,
    qtd_processos,
)

pct_cobertura = percentual_seguro(
    custo_detalhado,
    valor_passagens,
)

pct_ate_7 = percentual_seguro(
    emissoes_ate_7,
    antecedencia_valida,
)

pct_apos_inicio = percentual_seguro(
    emissoes_apos_inicio,
    registros_passagem,
)


antecedencia_mediana = (
    obter_antecedencia_mediana(
        tuple(
            sorted(
                anos_selecionados
            )
        )
    )
)


# DELTAS

delta_processos = None
delta_pagamentos = None


if len(
    anos_selecionados
) == 1:

    ano = anos_selecionados[0]

    linha = df_exec[
        df_exec[
            "ano_fonte"
        ] == ano
    ]

    if not linha.empty:

        linha = linha.iloc[0]

        delta_processos = (
            delta_pct(
                linha[
                    "variacao_yoy_processos_pct"
                ]
            )
        )

        delta_pagamentos = (
            delta_pct(
                linha[
                    "variacao_yoy_pagamentos_pct"
                ]
            )
        )


# KPIs PRINCIPAIS

titulo_secao(
    "Indicadores principais",
    (
        "Os valores financeiros desta página utilizam "
        "Pagamento como referência principal."
    ),
)


c1, c2, c3 = st.columns(
    3
)


with c1:
    st.metric(
        "Processos de viagem",
        inteiro_br(
            qtd_processos
        ),
        delta=delta_processos,
    )


with c2:
    st.metric(
        "Valor registrado em pagamentos",
        moeda_br(
            valor_total,
            compacto=True,
        ),
        delta=delta_pagamentos,
    )


with c3:
    st.metric(
        "Processos urgentes",
        percentual_br(
            pct_urgentes
        ),
    )


c4, c5, c6 = st.columns(
    3
)


with c4:
    st.metric(
        "Valor pago em passagens",
        moeda_br(
            valor_passagens,
            compacto=True,
        ),
    )


with c5:
    st.metric(
        "Valor pago em diárias",
        moeda_br(
            valor_diarias,
            compacto=True,
        ),
    )


with c6:
    st.metric(
        "Antecedência mediana",
        dias_br(
            antecedencia_mediana
        ),
        help=(
            "Mediana calculada apenas para emissões "
            "realizadas na data de início da viagem "
            "ou antes dela."
        ),
    )


st.divider()


# EVOLUÇÃO HISTÓRICA

titulo_secao(
    "Evolução histórica",
    (
        "Comparação anual do volume de processos "
        "e dos valores registrados em pagamentos."
    ),
)


g1, g2 = st.columns(
    2
)


with g1:
    st.plotly_chart(
        grafico_processos(
            df_exec_filtrado
        ),
        width="stretch",
    )


with g2:
    st.plotly_chart(
        grafico_pagamentos(
            df_exec_filtrado
        ),
        width="stretch",
    )


# COMPOSIÇÃO DOS PAGAMENTOS

titulo_secao(
    "Composição dos pagamentos",
    (
        "Distribuição entre diárias, passagens, "
        "restituições e seguro."
    ),
)


st.plotly_chart(
    grafico_composicao_gastos(
        df_gastos_filtrado
    ),
    width="stretch",
)


st.divider()


# INDICADORES OPERACIONAIS

titulo_secao(
    "Planejamento e cobertura",
    (
        "Indicadores de antecedência e cobertura "
        "do detalhamento das passagens."
    ),
)


m1, m2, m3 = st.columns(
    3
)


with m1:
    st.metric(
        "Cobertura financeira do detalhamento",
        percentual_br(
            pct_cobertura
        ),
        help=(
            "Custo das passagens com detalhamento "
            "disponível dividido pelo valor financeiro "
            "registrado em Pagamento como PASSAGEM."
        ),
    )


with m2:
    st.metric(
        "Emissões em até 7 dias",
        percentual_br(
            pct_ate_7
        ),
        help=(
            "Percentual calculado apenas entre registros "
            "com antecedência não negativa."
        ),
    )


with m3:
    st.metric(
        "Emissões após o início",
        percentual_br(
            pct_apos_inicio
        ),
        help=(
            "Não é classificado automaticamente "
            "como erro. É mantido como comportamento "
            "operacional observado."
        ),
    )


st.plotly_chart(
    grafico_indicadores_operacionais(
        df_exec_filtrado
    ),
    width="stretch",
)


# METODOLOGIA

st.divider()


with st.expander(
    "Como interpretar estes indicadores"
):

    st.markdown(
        """
        **Quantidade de processos**

        Utiliza uma observação por processo e ano de origem.
        As linhas brutas da tabela Viagem não são contadas
        automaticamente como viagens independentes.

        **Valor registrado em pagamentos**

        Utiliza `FatoPagamento` como referência financeira.
        O indicador não é denominado automaticamente como
        custo líquido.

        **Valor pago em passagens**

        Utiliza exclusivamente os registros classificados
        como `PASSAGEM` em `FatoPagamento`.

        **Antecedência mediana**

        Representa a diferença entre a data de emissão e
        a data de início do processo, somente quando a
        antecedência é maior ou igual a zero.

        **Cobertura financeira do detalhamento**

        Compara o custo disponível em `FatoPassagem` com
        o valor registrado em `FatoPagamento.PASSAGEM`.
        Portanto, `FatoPassagem` não deve ser interpretada
        como cobertura integral de todo o gasto financeiro.

        **Emissões após o início**

        Permanecem visíveis como categoria operacional.
        Os dados disponíveis não permitem concluir,
        isoladamente, que esses registros sejam erros.
        """
    )


nota_metodologica(
    """
    A relação entre antecedência e custo apresentada neste
    projeto deve ser interpretada como <strong>associação
    observada nos dados</strong>. O conjunto analisado não
    permite atribuir causalidade ao prazo de emissão sem
    controlar outros fatores que também influenciam preços.
    """
)


st.caption(
    "Escopo histórico principal: 2022–2025. "
    "Camadas de dados: Raw → Bronze → Silver → Gold → "
    "Analytics Marts."
)
