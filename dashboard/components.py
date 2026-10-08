import streamlit as st

from dashboard.config import (
    APP_TITLE,
    APP_SUBTITLE,
)


# ESTILO GLOBAL

def aplicar_estilo_global():
    st.markdown(
        """
        <style>

        /* ===================================================
           ÁREA PRINCIPAL
        =================================================== */

        .block-container {
            max-width: 1500px;
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }


        /* ===================================================
           TÍTULOS
        =================================================== */

        h1 {
            font-weight: 750 !important;
            letter-spacing: -0.02em;
        }

        h2,
        h3 {
            letter-spacing: -0.01em;
        }


        /* ===================================================
           SUBTÍTULO DAS PÁGINAS
        =================================================== */

        .pi-subtitle {
            opacity: 0.72;
            margin-top: -0.6rem;
            margin-bottom: 1.6rem;
            font-size: 1rem;
            line-height: 1.55;
        }


        /* ===================================================
           CARTÕES DE MÉTRICA
        =================================================== */

        [data-testid="stMetric"] {
            border: 1px solid rgba(90, 100, 120, 0.18);
            border-radius: 14px;
            padding: 16px 18px;
            background: rgba(255, 255, 255, 0.72);
            min-height: 126px;
        }

        [data-testid="stMetric"]:hover {
            border-color: rgba(31, 90, 166, 0.35);
            box-shadow: 0 3px 12px rgba(30, 50, 80, 0.05);
        }

        /*
        Evita títulos truncados como:
        "Cobertura financeira de ..."
        */

        [data-testid="stMetricLabel"] {
            min-height: 2.7rem;
            align-items: flex-start !important;
        }

        [data-testid="stMetricLabel"] * {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
            line-height: 1.25 !important;
        }

        [data-testid="stMetricLabel"] p {
            font-size: 0.91rem !important;
        }

        [data-testid="stMetricValue"] {
            font-weight: 500;
        }


        /* ===================================================
           SIDEBAR
        =================================================== */

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(90, 100, 120, 0.12);
        }

        [data-testid="stSidebar"] .block-container {
            padding-top: 1.5rem;
        }


        /* ===================================================
           DIVISORES
        =================================================== */

        hr {
            margin-top: 2rem !important;
            margin-bottom: 2rem !important;
            opacity: 0.45;
        }


        /* ===================================================
           EXPANDERS
        =================================================== */

        div[data-testid="stExpander"] {
            border-radius: 12px;
            border-color: rgba(90, 100, 120, 0.18);
        }


        /* ===================================================
           DATAFRAMES
        =================================================== */

        [data-testid="stDataFrame"] {
            border-radius: 10px;
            overflow: hidden;
        }


        /* ===================================================
           NOTA METODOLÓGICA
        =================================================== */

        .pi-note {
            padding: 0.95rem 1.1rem;
            border-left: 4px solid #1F5AA6;
            background: rgba(31, 90, 166, 0.065);
            border-radius: 7px;
            font-size: 0.93rem;
            line-height: 1.6;
            margin-top: 0.5rem;
            margin-bottom: 1rem;
        }


        /* ===================================================
           RODAPÉ / TEXTO SECUNDÁRIO
        =================================================== */

        .pi-footer {
            opacity: 0.68;
            font-size: 0.83rem;
            margin-top: 1.5rem;
        }


        /* ===================================================
           RESPONSIVIDADE
        =================================================== */

        @media (max-width: 900px) {

            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            [data-testid="stMetric"] {
                min-height: auto;
            }
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# CABEÇALHO

def cabecalho_pagina(
    titulo=None,
    subtitulo=None,
):
    st.title(
        titulo or APP_TITLE
    )

    st.markdown(
        (
            '<div class="pi-subtitle">'
            f'{subtitulo or APP_SUBTITLE}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


# NOTA METODOLÓGICA

def nota_metodologica(texto):
    st.markdown(
        (
            '<div class="pi-note">'
            f'{texto.strip()}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


# TÍTULO DE SEÇÃO

def titulo_secao(
    titulo,
    descricao=None,
):
    st.subheader(
        titulo
    )

    if descricao:
        st.caption(
            descricao
        )


# RODAPÉ PADRONIZADO

def rodape_pagina(texto):
    st.markdown(
        (
            '<div class="pi-footer">'
            f'{texto}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )