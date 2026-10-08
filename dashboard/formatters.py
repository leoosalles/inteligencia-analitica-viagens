import math


def _valido(valor):
    if valor is None:
        return False

    try:
        return not math.isnan(float(valor))
    except (TypeError, ValueError):
        return False


def inteiro_br(valor):
    if not _valido(valor):
        return "—"

    valor = int(round(float(valor)))

    return f"{valor:,}".replace(",", ".")


def numero_br(valor, casas=2):
    if not _valido(valor):
        return "—"

    texto = f"{float(valor):,.{casas}f}"

    return (
        texto
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def moeda_br(valor, compacto=False):
    if not _valido(valor):
        return "—"

    valor = float(valor)

    if compacto:
        abs_valor = abs(valor)

        if abs_valor >= 1_000_000_000:
            return (
                "R$ "
                + numero_br(valor / 1_000_000_000, 2)
                + " bi"
            )

        if abs_valor >= 1_000_000:
            return (
                "R$ "
                + numero_br(valor / 1_000_000, 1)
                + " mi"
            )

        if abs_valor >= 1_000:
            return (
                "R$ "
                + numero_br(valor / 1_000, 1)
                + " mil"
            )

    return "R$ " + numero_br(valor, 2)


def percentual_br(valor, casas=1):
    if not _valido(valor):
        return "—"

    return numero_br(valor, casas) + "%"


def dias_br(valor):
    if not _valido(valor):
        return "—"

    valor = float(valor)

    if valor.is_integer():
        return f"{int(valor)} dias"

    return numero_br(valor, 1) + " dias"


def delta_pct(valor):
    if not _valido(valor):
        return None

    return (
        percentual_br(valor, 1)
        + " vs. ano anterior"
    )