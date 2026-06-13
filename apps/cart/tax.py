from decimal import Decimal, ROUND_HALF_UP


CLP_QUANT = Decimal("1")


def quantize_clp(value):
    return Decimal(value or 0).quantize(CLP_QUANT, rounding=ROUND_HALF_UP)


def calculate_tax_breakdown(total_gross, tax_rate=Decimal("0.19")):
    gross = quantize_clp(total_gross)
    rate = Decimal(tax_rate)
    if gross <= 0:
        return {
            "net": Decimal("0"),
            "tax": Decimal("0"),
            "gross": Decimal("0"),
        }
    net = quantize_clp(gross / (Decimal("1") + rate))
    tax = gross - net
    return {
        "net": net,
        "tax": tax,
        "gross": gross,
    }
