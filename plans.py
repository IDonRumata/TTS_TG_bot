"""Тарифные планы и их лимиты."""

PLANS: dict[str, dict] = {
    "free": {
        "name":              "🆓 Бесплатный",
        "chars_per_day":     3_000,
        "chars_per_month":   None,       # без месячного лимита
        "max_per_request":   1_500,
        "all_voices":        False,      # только базовые голоса
        "price_month_stars": 0,
        "price_year_stars":  0,
        "price_month_byn":   0,
        "price_year_byn":    0,
    },
    "basic": {
        "name":              "⭐ Базовый",
        "chars_per_day":     None,
        "chars_per_month":   300_000,
        "max_per_request":   3_000,
        "all_voices":        True,
        "price_month_stars": 500,        # ~$6.50
        "price_year_stars":  4_800,      # ~$62 (экономия 20%)
        "price_month_byn":   20,
        "price_year_byn":    190,
    },
    "pro": {
        "name":              "🚀 Про",
        "chars_per_day":     None,
        "chars_per_month":   3_000_000,
        "max_per_request":   5_000,
        "all_voices":        True,
        "price_month_stars": 1_200,      # ~$15.60
        "price_year_stars":  11_520,     # ~$150 (экономия 20%)
        "price_month_byn":   50,
        "price_year_byn":    480,
    },
}

# Голоса, доступные на бесплатном тарифе
FREE_VOICES = {"ru-RU-SvetlanaNeural", "en-US-JennyNeural"}


def get_plan(plan_name: str) -> dict:
    return PLANS.get(plan_name, PLANS["free"])


def plan_description(plan_name: str) -> str:
    p = get_plan(plan_name)
    lines = [f"**{p['name']}**"]
    if p["chars_per_day"]:
        lines.append(f"• {p['chars_per_day']:,} символов в день")
    if p["chars_per_month"]:
        lines.append(f"• {p['chars_per_month']:,} символов в месяц")
    lines.append(f"• До {p['max_per_request']:,} символов за запрос")
    lines.append(f"• {'Все голоса' if p['all_voices'] else 'Базовые голоса'}")
    if p["price_month_stars"]:
        lines.append(f"• {p['price_month_stars']}⭐/мес или {p['price_month_byn']} BYN/мес")
    return "\n".join(lines)
