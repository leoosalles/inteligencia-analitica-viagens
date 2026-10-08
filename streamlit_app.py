import streamlit as st

from dashboard.components import (
    aplicar_estilo_global,
)
from dashboard.config import (
    APP_TITLE,
)


# CONFIGURAÇÃO GERAL DA APLICAÇÃO

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ESTILO GLOBAL

aplicar_estilo_global()


# PÁGINAS

pagina_executiva = st.Page(
    "pages/1_Visao_Executiva.py",
    title="Visão Executiva",
    icon="📊",
    default=True,
)


pagina_gastos = st.Page(
    "pages/2_Gastos_Pagamentos.py",
    title="Gastos e Pagamentos",
    icon="💳",
)


pagina_antecedencia = st.Page(
    "pages/3_Antecedencia_Custo.py",
    title="Antecedência e Custo",
    icon="⏱️",
)


pagina_rotas = st.Page(
    "pages/4_Rotas_Modais.py",
    title="Rotas e Modais",
    icon="🧭",
)


pagina_orgaos = st.Page(
    "pages/5_Orgaos_Operacao.py",
    title="Órgãos e Operação",
    icon="🏢",
)


pagina_qualidade = st.Page(
    "pages/6_Qualidade_Metodologia.py",
    title="Qualidade e Metodologia",
    icon="🔎",
)


# NAVEGAÇÃO

navegacao = st.navigation(
    {
        "Dashboard": [
            pagina_executiva,
            pagina_gastos,
            pagina_antecedencia,
            pagina_rotas,
            pagina_orgaos,
            pagina_qualidade,
        ]
    }
)


# EXECUÇÃO

navegacao.run()