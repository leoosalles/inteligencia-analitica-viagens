import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# PADRÃO VISUAL GLOBAL DOS GRÁFICOS

def aplicar_padrao_grafico(fig):
    """
    Aplica configurações visuais comuns a todos os gráficos.

    separators=",.":
        decimal = vírgula
        milhar  = ponto

    Exemplo:
        1234567.89 -> 1.234.567,89
    """

    fig.update_layout(
        separators=",.",
        font=dict(
            family=(
                "Arial, Helvetica, "
                "sans-serif"
            ),
        ),
        hoverlabel=dict(
            font_size=13,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig


# FUNÇÕES AUXILIARES

def _texto_valido(valor):
    if valor is None:
        return False

    try:
        if pd.isna(valor):
            return False
    except (TypeError, ValueError):
        pass

    texto = str(valor).strip()

    return texto != ""


def _rotulo_localidade(
    cidade,
    uf,
    pais,
):
    partes = []

    if _texto_valido(cidade):
        partes.append(
            str(cidade).strip()
        )

    if _texto_valido(uf):
        partes.append(
            str(uf).strip()
        )

    if not partes and _texto_valido(pais):
        partes.append(
            str(pais).strip()
        )

    if not partes:
        return "Não informado"

    return " / ".join(
        partes
    )


def _nome_faixa_antecedencia(valor):
    nomes = {
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

    return nomes.get(
        valor,
        valor,
    )


def _nome_indicador_qualidade(codigo):
    nomes = {
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

    return nomes.get(
        codigo,
        codigo,
    )


# PÁGINA 1 — VISÃO EXECUTIVA

def grafico_processos(df):
    fig = px.line(
        df,
        x="ano_fonte",
        y="qtd_processos",
        markers=True,
        labels={
            "ano_fonte": "Ano",
            "qtd_processos": "Processos",
        },
    )

    fig.update_layout(
        title="Evolução da quantidade de processos",
        xaxis=dict(
            dtick=1,
        ),
        yaxis_title=None,
        xaxis_title=None,
        hovermode="x unified",
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Processos: %{y:,.0f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_pagamentos(df):
    fig = px.bar(
        df,
        x="ano_fonte",
        y="valor_total_pagamentos",
        labels={
            "ano_fonte":
                "Ano",

            "valor_total_pagamentos":
                "Valor registrado",
        },
    )

    fig.update_layout(
        title=(
            "Evolução do valor registrado "
            "em pagamentos"
        ),
        xaxis=dict(
            dtick=1,
        ),
        yaxis_title=None,
        xaxis_title=None,
        hovermode="x unified",
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Valor: R$ %{y:,.2f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_composicao_gastos(df):
    ordem = [
        "DIARIAS",
        "PASSAGEM",
        "RESTITUICAO",
        "SEGURO",
    ]

    nomes = {
        "DIARIAS":
            "Diárias",

        "PASSAGEM":
            "Passagens",

        "RESTITUICAO":
            "Restituições",

        "SEGURO":
            "Seguro",
    }

    dados = df.copy()

    dados[
        "categoria_exibicao"
    ] = (
        dados[
            "codigo_tipo_pagamento"
        ]
        .map(nomes)
        .fillna(
            dados[
                "codigo_tipo_pagamento"
            ]
        )
    )

    ordem_exibicao = [
        nomes[x]
        for x in ordem
    ]

    fig = px.bar(
        dados,
        x="ano_fonte",
        y="valor_total",
        color="categoria_exibicao",
        category_orders={
            "categoria_exibicao":
                ordem_exibicao
        },
        labels={
            "ano_fonte":
                "Ano",

            "valor_total":
                "Valor",

            "categoria_exibicao":
                "Categoria",
        },
    )

    fig.update_layout(
        title=(
            "Composição anual "
            "dos pagamentos"
        ),
        barmode="stack",
        xaxis=dict(
            dtick=1,
        ),
        xaxis_title=None,
        yaxis_title=None,
        legend_title=None,
        hovermode="x unified",
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "R$ %{y:,.2f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_indicadores_operacionais(df):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df[
                "ano_fonte"
            ],
            y=df[
                "pct_cobertura_valor_passagem_detalhada"
            ],
            mode="lines+markers",
            name=(
                "Cobertura financeira "
                "do detalhamento"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df[
                "ano_fonte"
            ],
            y=df[
                "pct_emissoes_ate_7_dias"
            ],
            mode="lines+markers",
            name=(
                "Emissões em até 7 dias"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df[
                "ano_fonte"
            ],
            y=df[
                "pct_processos_urgentes"
            ],
            mode="lines+markers",
            name=(
                "Processos urgentes"
            ),
        )
    )

    fig.update_layout(
        title=(
            "Indicadores operacionais "
            "e de cobertura"
        ),
        xaxis=dict(
            dtick=1,
        ),
        xaxis_title=None,
        yaxis_title="Percentual",
        legend_title=None,
        hovermode="x unified",
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_yaxes(
        ticksuffix="%"
    )

    return aplicar_padrao_grafico(
        fig
    )


# PÁGINA 2 — GASTOS E PAGAMENTOS

def grafico_evolucao_categoria(df):
    nomes = {
        "DIARIAS":
            "Diárias",

        "PASSAGEM":
            "Passagens",

        "RESTITUICAO":
            "Restituições",

        "SEGURO":
            "Seguro",
    }

    dados = df.copy()

    dados[
        "categoria_exibicao"
    ] = (
        dados[
            "codigo_tipo_pagamento"
        ]
        .map(nomes)
        .fillna(
            dados[
                "codigo_tipo_pagamento"
            ]
        )
    )

    fig = px.line(
        dados,
        x="ano_fonte",
        y="valor_total",
        color="categoria_exibicao",
        markers=True,
        labels={
            "ano_fonte":
                "Ano",

            "valor_total":
                "Valor",

            "categoria_exibicao":
                "Categoria",
        },
    )

    fig.update_layout(
        title=(
            "Evolução anual por categoria "
            "de pagamento"
        ),
        xaxis=dict(
            dtick=1,
        ),
        xaxis_title=None,
        yaxis_title=None,
        legend_title=None,
        hovermode="x unified",
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "R$ %{y:,.2f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_participacao_categorias(df):
    nomes = {
        "DIARIAS":
            "Diárias",

        "PASSAGEM":
            "Passagens",

        "RESTITUICAO":
            "Restituições",

        "SEGURO":
            "Seguro",
    }

    dados = (
        df.groupby(
            "codigo_tipo_pagamento",
            as_index=False,
        )[
            "valor_total"
        ]
        .sum()
    )

    dados[
        "categoria_exibicao"
    ] = (
        dados[
            "codigo_tipo_pagamento"
        ]
        .map(nomes)
        .fillna(
            dados[
                "codigo_tipo_pagamento"
            ]
        )
    )

    fig = px.pie(
        dados,
        names="categoria_exibicao",
        values="valor_total",
        hole=0.55,
    )

    fig.update_layout(
        title=(
            "Participação no valor "
            "registrado"
        ),
        legend_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "R$ %{value:,.2f}<br>"
            "%{percent}"
            "<extra></extra>"
        ),
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_top_orgaos(
    df,
    top_n=10,
):
    dados = (
        df.groupby(
            [
                "sk_organizacao",
                "nome_organizacao",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            valor_total=(
                "valor_total",
                "sum",
            ),
            qtd_processos=(
                "qtd_processos",
                "sum",
            ),
        )
    )

    dados[
        "nome_organizacao"
    ] = (
        dados[
            "nome_organizacao"
        ]
        .fillna(
            "Não informado"
        )
    )

    dados = (
        dados
        .sort_values(
            "valor_total",
            ascending=False,
        )
        .head(
            top_n
        )
        .sort_values(
            "valor_total",
            ascending=True,
        )
    )

    fig = px.bar(
        dados,
        x="valor_total",
        y="nome_organizacao",
        orientation="h",
        custom_data=[
            "qtd_processos"
        ],
        labels={
            "valor_total":
                "Valor registrado",

            "nome_organizacao":
                "Organização",
        },
    )

    fig.update_layout(
        title=(
            f"Top {top_n} organizações "
            "por valor registrado"
        ),
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Valor: R$ %{x:,.2f}<br>"
            "Processos: %{customdata[0]:,.0f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_top_orgaos_processos(
    df,
    top_n=10,
):
    dados = (
        df.groupby(
            [
                "sk_organizacao",
                "nome_organizacao",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            qtd_processos=(
                "qtd_processos",
                "sum",
            )
        )
    )

    dados[
        "nome_organizacao"
    ] = (
        dados[
            "nome_organizacao"
        ]
        .fillna(
            "Não informado"
        )
    )

    dados = (
        dados
        .sort_values(
            "qtd_processos",
            ascending=False,
        )
        .head(
            top_n
        )
        .sort_values(
            "qtd_processos",
            ascending=True,
        )
    )

    fig = px.bar(
        dados,
        x="qtd_processos",
        y="nome_organizacao",
        orientation="h",
        labels={
            "qtd_processos":
                "Processos",

            "nome_organizacao":
                "Organização",
        },
    )

    fig.update_layout(
        title=(
            f"Top {top_n} organizações "
            "por quantidade de processos"
        ),
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Processos: %{x:,.0f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


# PÁGINA 3 — ANTECEDÊNCIA E CUSTO

def grafico_custo_antecedencia(df):
    dados = df[
        df[
            "ordem_faixa"
        ].between(
            1,
            5,
        )
    ].copy()

    dados[
        "faixa_exibicao"
    ] = (
        dados[
            "faixa_antecedencia"
        ]
        .map(
            _nome_faixa_antecedencia
        )
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=dados[
                "faixa_exibicao"
            ],
            y=dados[
                "custo_mediano_passagem"
            ],
            name="Mediana",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Mediana: R$ %{y:,.2f}"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dados[
                "faixa_exibicao"
            ],
            y=dados[
                "custo_medio_passagem"
            ],
            mode="lines+markers",
            name="Média",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Média: R$ %{y:,.2f}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=(
            "Custo da passagem por "
            "faixa de antecedência"
        ),
        xaxis_title=None,
        yaxis_title=None,
        legend_title=None,
        hovermode="x unified",
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_volume_antecedencia(df):
    dados = df[
        df[
            "ordem_faixa"
        ].between(
            1,
            5,
        )
    ].copy()

    dados[
        "faixa_exibicao"
    ] = (
        dados[
            "faixa_antecedencia"
        ]
        .map(
            _nome_faixa_antecedencia
        )
    )

    fig = px.bar(
        dados,
        x="faixa_exibicao",
        y="qtd_registros",
        labels={
            "faixa_exibicao":
                "Antecedência",

            "qtd_registros":
                "Registros",
        },
    )

    fig.update_layout(
        title=(
            "Distribuição das emissões "
            "por antecedência"
        ),
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Registros: %{y:,.0f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_urgencia_antecedencia(df):
    dados = (
        df[
            df[
                "ordem_faixa"
            ].between(
                1,
                5,
            )
        ]
        .groupby(
            [
                "faixa_antecedencia",
                "ordem_faixa",
                "categoria_urgencia",
            ],
            as_index=False,
        )[
            "qtd_registros_passagem"
        ]
        .sum()
    )

    dados[
        "faixa_exibicao"
    ] = (
        dados[
            "faixa_antecedencia"
        ]
        .map(
            _nome_faixa_antecedencia
        )
    )

    nomes_urgencia = {
        "URGENTE":
            "Urgente",

        "NAO_URGENTE":
            "Não urgente",

        "INDETERMINADA":
            "Indeterminada",
    }

    dados[
        "urgencia_exibicao"
    ] = (
        dados[
            "categoria_urgencia"
        ]
        .map(
            nomes_urgencia
        )
        .fillna(
            dados[
                "categoria_urgencia"
            ]
        )
    )

    dados = dados.sort_values(
        "ordem_faixa"
    )

    fig = px.bar(
        dados,
        x="faixa_exibicao",
        y="qtd_registros_passagem",
        color="urgencia_exibicao",
        barmode="group",
        labels={
            "faixa_exibicao":
                "Antecedência",

            "qtd_registros_passagem":
                "Registros",

            "urgencia_exibicao":
                "Urgência",
        },
    )

    fig.update_layout(
        title=(
            "Antecedência por classificação "
            "de urgência"
        ),
        xaxis_title=None,
        yaxis_title=None,
        legend_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_modal_custo(df):
    dados = (
        df[
            df[
                "ordem_faixa"
            ].between(
                1,
                5,
            )
        ]
        .groupby(
            "modal",
            as_index=False,
            dropna=False,
        )
        .agg(
            qtd_registros=(
                "qtd_registros_passagem",
                "sum",
            ),
            custo_total=(
                "custo_total_passagens",
                "sum",
            ),
        )
    )

    dados[
        "custo_medio"
    ] = (
        dados[
            "custo_total"
        ]
        /
        dados[
            "qtd_registros"
        ].replace(
            0,
            float("nan"),
        )
    )

    dados = (
        dados
        .sort_values(
            "qtd_registros",
            ascending=False,
        )
        .head(10)
        .sort_values(
            "custo_medio",
            ascending=True,
        )
    )

    fig = px.bar(
        dados,
        x="custo_medio",
        y="modal",
        orientation="h",
        custom_data=[
            "qtd_registros"
        ],
        labels={
            "custo_medio":
                "Custo médio",

            "modal":
                "Modal",
        },
    )

    fig.update_layout(
        title=(
            "Custo médio por modal "
            "nas emissões válidas"
        ),
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Custo médio: R$ %{x:,.2f}<br>"
            "Registros: %{customdata[0]:,.0f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


# PÁGINA 4 — ROTAS E MODAIS

def grafico_top_origens(df):
    dados = df.copy()

    dados[
        "localidade"
    ] = dados.apply(
        lambda row:
            _rotulo_localidade(
                row.get(
                    "origem_cidade"
                ),
                row.get(
                    "origem_uf"
                ),
                row.get(
                    "origem_pais"
                ),
            ),
        axis=1,
    )

    dados = dados.sort_values(
        "qtd_trechos",
        ascending=True,
    )

    fig = px.bar(
        dados,
        x="qtd_trechos",
        y="localidade",
        orientation="h",
        labels={
            "qtd_trechos":
                "Trechos",

            "localidade":
                "Origem",
        },
    )

    fig.update_layout(
        title="Principais origens",
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Trechos: %{x:,.0f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_top_destinos(df):
    dados = df.copy()

    dados[
        "localidade"
    ] = dados.apply(
        lambda row:
            _rotulo_localidade(
                row.get(
                    "destino_cidade"
                ),
                row.get(
                    "destino_uf"
                ),
                row.get(
                    "destino_pais"
                ),
            ),
        axis=1,
    )

    dados = dados.sort_values(
        "qtd_trechos",
        ascending=True,
    )

    fig = px.bar(
        dados,
        x="qtd_trechos",
        y="localidade",
        orientation="h",
        labels={
            "qtd_trechos":
                "Trechos",

            "localidade":
                "Destino",
        },
    )

    fig.update_layout(
        title="Principais destinos",
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Trechos: %{x:,.0f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_top_rotas(df):
    dados = df.copy()

    dados[
        "origem"
    ] = dados.apply(
        lambda row:
            _rotulo_localidade(
                row.get(
                    "origem_cidade"
                ),
                row.get(
                    "origem_uf"
                ),
                row.get(
                    "origem_pais"
                ),
            ),
        axis=1,
    )

    dados[
        "destino"
    ] = dados.apply(
        lambda row:
            _rotulo_localidade(
                row.get(
                    "destino_cidade"
                ),
                row.get(
                    "destino_uf"
                ),
                row.get(
                    "destino_pais"
                ),
            ),
        axis=1,
    )

    dados[
        "rota"
    ] = (
        dados[
            "origem"
        ]
        + " → "
        + dados[
            "destino"
        ]
    )

    dados = dados.sort_values(
        "qtd_trechos",
        ascending=True,
    )

    fig = px.bar(
        dados,
        x="qtd_trechos",
        y="rota",
        orientation="h",
        labels={
            "qtd_trechos":
                "Trechos",

            "rota":
                "Rota",
        },
    )

    fig.update_layout(
        title="Rotas mais frequentes",
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Trechos: %{x:,.0f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_distribuicao_modais(df):
    dados = (
        df.copy()
        .sort_values(
            "qtd_trechos",
            ascending=True,
        )
    )

    fig = px.bar(
        dados,
        x="qtd_trechos",
        y="modal",
        orientation="h",
        labels={
            "qtd_trechos":
                "Trechos",

            "modal":
                "Modal",
        },
    )

    fig.update_layout(
        title=(
            "Distribuição dos trechos "
            "por modal"
        ),
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Trechos: %{x:,.0f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_custo_modal_rotas(df):
    dados = df[
        df[
            "qtd_registros_passagem"
        ] > 0
    ].copy()

    dados = dados.sort_values(
        "custo_medio_passagem",
        ascending=True,
    )

    fig = px.bar(
        dados,
        x="custo_medio_passagem",
        y="modal",
        orientation="h",
        custom_data=[
            "qtd_registros_passagem"
        ],
        labels={
            "custo_medio_passagem":
                "Custo médio",

            "modal":
                "Modal",
        },
    )

    fig.update_layout(
        title=(
            "Custo médio dos registros "
            "de passagem por modal"
        ),
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Custo médio: R$ %{x:,.2f}<br>"
            "Registros: %{customdata[0]:,.0f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


# PÁGINA 5 — ÓRGÃOS E OPERAÇÃO

def grafico_orgaos_valor(
    df,
    top_n=10,
):
    dados = (
        df.groupby(
            [
                "sk_organizacao",
                "nome_organizacao",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            valor_total=(
                "valor_total",
                "sum",
            ),
            qtd_processos=(
                "qtd_processos",
                "sum",
            ),
        )
    )

    dados[
        "nome_organizacao"
    ] = (
        dados[
            "nome_organizacao"
        ]
        .fillna(
            "Não informado"
        )
    )

    dados = (
        dados
        .sort_values(
            "valor_total",
            ascending=False,
        )
        .head(
            top_n
        )
        .sort_values(
            "valor_total",
            ascending=True,
        )
    )

    fig = px.bar(
        dados,
        x="valor_total",
        y="nome_organizacao",
        orientation="h",
        custom_data=[
            "qtd_processos"
        ],
        labels={
            "valor_total":
                "Valor registrado",

            "nome_organizacao":
                "Organização",
        },
    )

    fig.update_layout(
        title=(
            f"Top {top_n} por "
            "valor registrado"
        ),
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Valor: R$ %{x:,.2f}<br>"
            "Processos: %{customdata[0]:,.0f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_orgaos_processos(
    df,
    top_n=10,
):
    dados = (
        df.groupby(
            [
                "sk_organizacao",
                "nome_organizacao",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            qtd_processos=(
                "qtd_processos",
                "sum",
            )
        )
    )

    dados[
        "nome_organizacao"
    ] = (
        dados[
            "nome_organizacao"
        ]
        .fillna(
            "Não informado"
        )
    )

    dados = (
        dados
        .sort_values(
            "qtd_processos",
            ascending=False,
        )
        .head(
            top_n
        )
        .sort_values(
            "qtd_processos",
            ascending=True,
        )
    )

    fig = px.bar(
        dados,
        x="qtd_processos",
        y="nome_organizacao",
        orientation="h",
        labels={
            "qtd_processos":
                "Processos",

            "nome_organizacao":
                "Organização",
        },
    )

    fig.update_layout(
        title=(
            f"Top {top_n} por "
            "quantidade de processos"
        ),
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Processos: %{x:,.0f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_composicao_financeira_orgao(df):
    categorias = {
        "valor_diarias":
            "Diárias",

        "valor_passagens":
            "Passagens",

        "valor_restituicao":
            "Restituições",

        "valor_seguro":
            "Seguro",
    }

    valores = []

    for coluna, nome in categorias.items():
        valor = (
            pd.to_numeric(
                df[coluna],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )

        valores.append(
            {
                "categoria":
                    nome,

                "valor":
                    valor,
            }
        )

    dados = pd.DataFrame(
        valores
    )

    fig = px.pie(
        dados,
        names="categoria",
        values="valor",
        hole=0.55,
    )

    fig.update_layout(
        title=(
            "Composição financeira "
            "da perspectiva selecionada"
        ),
        legend_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "R$ %{value:,.2f}<br>"
            "%{percent}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_urgencia_orgaos(
    df,
    top_n=10,
):
    dados = (
        df.groupby(
            [
                "sk_organizacao",
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
            qtd_processos_urgentes=(
                "qtd_processos_urgentes",
                "sum",
            ),
        )
    )

    dados[
        "nome_organizacao"
    ] = (
        dados[
            "nome_organizacao"
        ]
        .fillna(
            "Não informado"
        )
    )

    dados[
        "pct_urgentes"
    ] = (
        100.0
        * dados[
            "qtd_processos_urgentes"
        ]
        /
        dados[
            "qtd_processos"
        ].replace(
            0,
            float("nan"),
        )
    )

    dados = (
        dados
        .sort_values(
            "qtd_processos",
            ascending=False,
        )
        .head(
            top_n
        )
        .sort_values(
            "pct_urgentes",
            ascending=True,
        )
    )

    fig = px.bar(
        dados,
        x="pct_urgentes",
        y="nome_organizacao",
        orientation="h",
        custom_data=[
            "qtd_processos",
            "qtd_processos_urgentes",
        ],
        labels={
            "pct_urgentes":
                "% urgentes",

            "nome_organizacao":
                "Órgão solicitante",
        },
    )

    fig.update_layout(
        title=(
            "Urgência entre os órgãos "
            "com maior volume"
        ),
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_xaxes(
        ticksuffix="%"
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Urgentes: %{customdata[1]:,.0f}<br>"
            "Processos: %{customdata[0]:,.0f}<br>"
            "% urgente: %{x:.1f}%"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


# PÁGINA 6 — QUALIDADE E METODOLOGIA

def grafico_qualidade_resumo(df):
    dados = df.copy()

    dados[
        "indicador_exibicao"
    ] = (
        dados[
            "indicador"
        ]
        .map(
            _nome_indicador_qualidade
        )
        .fillna(
            dados[
                "indicador"
            ]
        )
    )

    dados = dados.sort_values(
        "percentual",
        ascending=True,
    )

    fig = px.bar(
        dados,
        x="percentual",
        y="indicador_exibicao",
        orientation="h",
        color="categoria",
        custom_data=[
            "numerador",
            "denominador",
        ],
        labels={
            "percentual":
                "Percentual",

            "indicador_exibicao":
                "Indicador",

            "categoria":
                "Categoria",
        },
    )

    fig.update_layout(
        title=(
            "Indicadores de qualidade "
            "e cobertura"
        ),
        xaxis_title=None,
        yaxis_title=None,
        legend_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_xaxes(
        ticksuffix="%"
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Percentual: %{x:.3f}%<br>"
            "Numerador: %{customdata[0]:,.2f}<br>"
            "Denominador: %{customdata[1]:,.2f}"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )


def grafico_qualidade_evolucao(
    df,
    indicador,
):
    dados = df[
        df[
            "indicador"
        ] == indicador
    ].copy()

    nome = (
        _nome_indicador_qualidade(
            indicador
        )
    )

    dados = dados.sort_values(
        "ano_fonte"
    )

    fig = px.line(
        dados,
        x="ano_fonte",
        y="percentual",
        markers=True,
        labels={
            "ano_fonte":
                "Ano",

            "percentual":
                "Percentual",
        },
    )

    fig.update_layout(
        title=(
            f"Evolução — {nome}"
        ),
        xaxis=dict(
            dtick=1,
        ),
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_yaxes(
        ticksuffix="%"
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "%{y:.3f}%"
            "<extra></extra>"
        )
    )

    return aplicar_padrao_grafico(
        fig
    )