import pandas as pd
import streamlit as st

from dashboard.charts import (
    grafico_qualidade_evolucao,
    grafico_qualidade_resumo,
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
    carregar_qualidade,
)
from dashboard.formatters import (
    inteiro_br,
    percentual_br,
)


# CABEÇALHO

cabecalho_pagina(
    titulo="Qualidade e Metodologia",
    subtitulo=(
        "Transparência sobre cobertura, exceções, "
        "regras de transformação e interpretação "
        "dos indicadores."
    ),
)


# CARREGAMENTO

try:
    df = (
        carregar_qualidade()
        .copy()
    )

except FileNotFoundError as exc:
    st.error(
        str(exc)
    )
    st.stop()


# FILTRO DE ANO

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
        key="qualidade_anos",
    )
)


if not anos_selecionados:
    anos_selecionados = (
        anos_disponiveis
    )


df_filtrado = df[
    df[
        "ano_fonte"
    ].isin(
        anos_selecionados
    )
].copy()


# FUNÇÕES

nomes_indicadores = {
    "PROCESSO_REPETIDO_FONTE":
        "Processos repetidos na fonte",

    "PROCESSO_FINANCEIRO_MULTIVALORADO":
        "Processos financeiros multivalorados",

    "PROCESSO_SEM_DATA_INICIO_CONSOLIDADA":
        "Sem data de início consolidada",

    "PROCESSO_SEM_DATA_FIM_CONSOLIDADA":
        "Sem data de fim consolidada",

    "PROCESSO_SEM_VIAJANTE_IDENTIFICADO":
        "Sem viajante identificado",

    "PASSAGEM_SEM_DATA_EMISSAO":
        "Passagem sem data de emissão",

    "PASSAGEM_EMISSAO_APOS_INICIO":
        "Emissão após o início",

    "TRECHO_MODAL_INVALIDO":
        "Modal inválido",

    "REPETICAO_EXATA_OBSERVADA_PAGAMENTO":
        "Repetição exata em Pagamento",

    "REPETICAO_EXATA_OBSERVADA_PASSAGEM":
        "Repetição exata em Passagem",

    "REPETICAO_EXATA_OBSERVADA_TRECHO":
        "Repetição exata em Trecho",

    "COBERTURA_VALOR_PASSAGEM_DETALHADA":
        "Cobertura financeira de Passagem",

    "COBERTURA_PROCESSOS_PASSAGEM_DETALHADA":
        "Cobertura de processos de Passagem",
}


def consolidar_indicador(
    indicador,
):
    dados = df_filtrado[
        df_filtrado[
            "indicador"
        ] == indicador
    ]

    if dados.empty:
        return {
            "numerador": 0,
            "denominador": 0,
            "percentual": None,
        }

    numerador = pd.to_numeric(
        dados[
            "numerador"
        ],
        errors="coerce",
    ).fillna(0).sum()

    denominador = pd.to_numeric(
        dados[
            "denominador"
        ],
        errors="coerce",
    ).fillna(0).sum()

    percentual = (
        100.0
        * numerador
        / denominador
        if denominador
        else None
    )

    return {
        "numerador":
            float(numerador),

        "denominador":
            float(denominador),

        "percentual":
            percentual,
    }


# ABAS

aba_qualidade, aba_metodologia = st.tabs(
    [
        "Qualidade dos dados",
        "Metodologia",
    ]
)


# ABA QUALIDADE

with aba_qualidade:

    titulo_secao(
        "Cobertura e consistência",
        (
            "Indicadores consolidados conforme "
            "os anos selecionados."
        ),
    )


    cobertura_valor = consolidar_indicador(
        "COBERTURA_VALOR_PASSAGEM_DETALHADA"
    )

    cobertura_processos = consolidar_indicador(
        "COBERTURA_PROCESSOS_PASSAGEM_DETALHADA"
    )

    sem_data = consolidar_indicador(
        "PASSAGEM_SEM_DATA_EMISSAO"
    )

    apos_inicio = consolidar_indicador(
        "PASSAGEM_EMISSAO_APOS_INICIO"
    )


    c1, c2, c3, c4 = st.columns(
        4
    )


    with c1:
        st.metric(
            "Cobertura financeira de Passagem",
            percentual_br(
                cobertura_valor[
                    "percentual"
                ]
            ),
        )


    with c2:
        st.metric(
            "Cobertura de processos",
            percentual_br(
                cobertura_processos[
                    "percentual"
                ]
            ),
        )


    with c3:
        st.metric(
            "Passagens sem data de emissão",
            percentual_br(
                sem_data[
                    "percentual"
                ]
            ),
        )


    with c4:
        st.metric(
            "Emissões após o início",
            percentual_br(
                apos_inicio[
                    "percentual"
                ]
            ),
        )


    # EXCEÇÕES E MULTIPLICIDADE

    titulo_secao(
        "Exceções observadas",
        (
            "Ocorrências preservadas ou tratadas "
            "explicitamente durante a modelagem."
        ),
    )


    proc_repetidos = consolidar_indicador(
        "PROCESSO_REPETIDO_FONTE"
    )

    proc_multivalorados = consolidar_indicador(
        "PROCESSO_FINANCEIRO_MULTIVALORADO"
    )

    modal_invalido = consolidar_indicador(
        "TRECHO_MODAL_INVALIDO"
    )


    c5, c6, c7 = st.columns(
        3
    )


    with c5:
        st.metric(
            "Processos repetidos na fonte",
            inteiro_br(
                proc_repetidos[
                    "numerador"
                ]
            ),
        )


    with c6:
        st.metric(
            "Processos financeiros multivalorados",
            inteiro_br(
                proc_multivalorados[
                    "numerador"
                ]
            ),
        )


    with c7:
        st.metric(
            "Trechos com modal inválido",
            inteiro_br(
                modal_invalido[
                    "numerador"
                ]
            ),
        )


    st.divider()


    # GRÁFICO GERAL

    resumo = (
        df_filtrado.groupby(
            [
                "indicador",
                "categoria",
            ],
            as_index=False,
        )
        .agg(
            numerador=(
                "numerador",
                "sum",
            ),
            denominador=(
                "denominador",
                "sum",
            ),
        )
    )


    resumo[
        "percentual"
    ] = (
        100.0
        * resumo[
            "numerador"
        ]
        / resumo[
            "denominador"
        ].replace(
            0,
            float("nan"),
        )
    )


    st.plotly_chart(
        grafico_qualidade_resumo(
            resumo
        ),
        width="stretch",
    )


    # EVOLUÇÃO DE UM INDICADOR

    titulo_secao(
        "Evolução temporal",
        (
            "Selecione um indicador para visualizar "
            "seu comportamento anual."
        ),
    )


    indicadores_disponiveis = sorted(
        df[
            "indicador"
        ].unique(),
        key=lambda x:
            nomes_indicadores.get(
                x,
                x,
            ),
    )


    indicador_selecionado = (
        st.selectbox(
            "Indicador",
            options=indicadores_disponiveis,
            format_func=lambda x:
                nomes_indicadores.get(
                    x,
                    x,
                ),
            key="qualidade_indicador",
        )
    )


    st.plotly_chart(
        grafico_qualidade_evolucao(
            df_filtrado,
            indicador_selecionado,
        ),
        width="stretch",
    )


    # TABELA

    titulo_secao(
        "Detalhamento dos indicadores",
        (
            "Numeradores, denominadores e percentuais "
            "utilizados na avaliação."
        ),
    )


    tabela = resumo.copy()

    tabela[
        "Indicador"
    ] = (
        tabela[
            "indicador"
        ]
        .map(
            nomes_indicadores
        )
        .fillna(
            tabela[
                "indicador"
            ]
        )
    )


    tabela = tabela[
        [
            "Indicador",
            "categoria",
            "numerador",
            "denominador",
            "percentual",
        ]
    ].rename(
        columns={
            "categoria":
                "Categoria",

            "numerador":
                "Numerador",

            "denominador":
                "Denominador",

            "percentual":
                "Percentual (%)",
        }
    )


    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        column_config={
            "Numerador":
                st.column_config.NumberColumn(
                    format="%.2f",
                ),

            "Denominador":
                st.column_config.NumberColumn(
                    format="%.2f",
                ),

            "Percentual (%)":
                st.column_config.NumberColumn(
                    format="%.4f%%",
                ),
        },
    )


# ABA METODOLOGIA

with aba_metodologia:

    titulo_secao(
        "Arquitetura analítica",
        (
            "Estrutura adotada desde os arquivos "
            "originais até o dashboard."
        ),
    )


    st.code(
        """
CSV original
    ↓
Bronze — Parquet bruto
    ↓
Silver — tipagem, normalização e linhagem
    ↓
Gold — modelo dimensional
    ↓
Analytics Marts
    ↓
Streamlit + DuckDB + Plotly
        """.strip(),
        language="text",
    )


    titulo_secao(
        "Granularidade",
    )

    st.markdown(
        """
        **Processo de viagem**

        A unidade analítica principal é uma linha por
        combinação de ano de origem e identificador do
        processo.

        **Pagamento**

        Cada observação da fonte é preservada como um
        registro da fato de pagamentos.

        **Passagem**

        Cada registro de passagem é preservado, incluindo
        sua multiplicidade original.

        **Trecho**

        Cada observação de deslocamento constitui um trecho.
        Um processo pode possuir vários trechos.
        """
    )


    titulo_secao(
        "Regras financeiras",
    )

    st.markdown(
        """
        - **FatoPagamento** é a referência principal para
          valores financeiros registrados.

        - `PASSAGEM` em Pagamento representa o valor
          financeiro utilizado nos KPIs de passagens.

        - `DIARIAS` em Pagamento representa o valor
          financeiro utilizado nos KPIs de diárias.

        - **FatoPassagem** é utilizada para detalhamento de
          tarifa, taxa de serviço, modal, emissão e
          antecedência.

        - O detalhamento de Passagem possui cobertura
          parcial e não deve ser tratado como o universo
          completo dos pagamentos de passagens.

        - `RESTITUICAO` de Pagamento não é equivalente ao
          campo `Valor devolução` da fonte Viagem.
        """
    )


    titulo_secao(
        "Tratamento da multiplicidade",
    )

    st.markdown(
        """
        Registros exatamente iguais observados nas fontes
        **não foram eliminados automaticamente**.

        A ausência de identificadores transacionais únicos
        impede afirmar que toda repetição exata seja uma
        duplicidade indevida.

        Dessa forma, a multiplicidade original foi
        preservada e registrada por hash e ordinal de
        ocorrência.
        """
    )


    titulo_secao(
        "Antecedência",
    )

    st.markdown(
        """
        A antecedência é calculada como:

        `data de início do processo − data de emissão`

        As faixas utilizadas são:

        - 0–3 dias
        - 4–7 dias
        - 8–14 dias
        - 15–30 dias
        - mais de 30 dias

        Emissões posteriores ao início são mantidas em
        categoria própria e não são classificadas
        automaticamente como erro.
        """
    )


    titulo_secao(
        "Privacidade",
    )

    st.markdown(
        """
        O dashboard não expõe CPF ou nome individual dos
        viajantes.

        Quando necessário para relacionamentos analíticos,
        são utilizados identificadores pseudonimizados.
        As visualizações priorizam informações agregadas.
        """
    )


    titulo_secao(
        "Escopo temporal",
    )

    st.markdown(
        """
        A série histórica principal considera
        **2022 a 2025**.

        O ano de 2026 não é incorporado às comparações
        históricas principais por representar período
        incompleto.

        Datas operacionais fora desse intervalo podem
        existir na dimensão de datas sem alterar o
        `AnoFonte` utilizado para delimitar a série.
        """
    )


    titulo_secao(
        "Limitações interpretativas",
    )

    st.markdown(
        """
        **Associação não implica causalidade.**

        A relação observada entre antecedência e preço pode
        ser influenciada também por rota, modal,
        disponibilidade, sazonalidade, características da
        viagem e outros fatores não controlados neste
        conjunto de dados.

        O dashboard deve ser utilizado para apoiar análise
        e decisão, e não para atribuir causalidade sem
        investigação adicional.
        """
    )


    nota_metodologica(
        """
        A solução foi construída com foco em
        <strong>rastreabilidade, reprodutibilidade e
        transparência</strong>. As transformações e
        exceções relevantes foram preservadas ou
        documentadas em vez de serem corrigidas
        arbitrariamente.
        """
    )


st.caption(
    "Escopo histórico: 2022–2025. "
    "Arquitetura: Raw → Bronze → Silver → Gold → "
    "Analytics Marts → Dashboard."
)
