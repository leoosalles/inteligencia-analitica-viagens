import os
from pathlib import Path


# PROJETO

PROJECT_DIR = Path(
    __file__
).resolve().parents[1]


# DADOS

DEFAULT_DATA_ROOT = (
    PROJECT_DIR /
    "data"
)

DATA_ROOT = Path(
    os.getenv(
        "PI_DATA_ROOT",
        str(DEFAULT_DATA_ROOT)
    )
).expanduser().resolve()

GOLD_DIR = DATA_ROOT / "gold"
MARTS_DIR = GOLD_DIR / "marts"


# MARTS

MART_EXECUTIVO = (
    MARTS_DIR /
    "mart_executivo_anual.parquet"
)

MART_GASTOS = (
    MARTS_DIR /
    "mart_gastos_categoria.parquet"
)

MART_ANTECEDENCIA = (
    MARTS_DIR /
    "mart_antecedencia.parquet"
)

MART_ANTECEDENCIA_DETALHE = (
    MARTS_DIR /
    "mart_antecedencia_detalhe.parquet"
)

MART_ORGAOS = (
    MARTS_DIR /
    "mart_orgaos.parquet"
)

MART_ROTAS = (
    MARTS_DIR /
    "mart_rotas.parquet"
)

MART_MODAIS = (
    MARTS_DIR /
    "mart_modais.parquet"
)

MART_QUALIDADE = (
    MARTS_DIR /
    "mart_qualidade_dados.parquet"
)


# ESCOPO HISTÓRICO

ANOS_HISTORICOS = [
    2022,
    2023,
    2024,
    2025,
]


# IDENTIDADE DO DASHBOARD

APP_TITLE = (
    "Inteligência Analítica de Viagens"
)

APP_SUBTITLE = (
    "Painel histórico de processos, pagamentos, "
    "passagens e deslocamentos — 2022 a 2025"
)