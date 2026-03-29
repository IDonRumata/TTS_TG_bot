"""Оплата через Telegram Stars."""

import logging
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice,
    PreCheckoutQuery, SuccessfulPayment,
    InlineKeyboardMarkup
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import activate_subscription
from plans import PLANS

logger = logging.getLogger(__name__)
router = Router()

# Payload формат: stars:{plan}:{period}
# Например: stars:basic:month


def plans_keyboard_stars() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура выбора тарифа для оплаты Stars."""
    builder = InlineKeyboardBuilder()
    for plan_id, plan in PLANS.items():
        if plan_id == "free":
            continue
        m_stars = plan["price_month_stars"]
        y_stars = plan["price_year_stars"]
        builder.button(
            text=f"{plan['name']} — {m_stars}⭐/мес",
            callback_data=f"buy_stars:{plan_id}:month"
        )
        builder.button(
            text=f"{plan['name']} — {y_stars}⭐/год (−20%)",
            callback_data=f"buy_stars:{plan_id}:year"
        )
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data.startswith("buy_stars:"))
async def cb_buy_stars(callback: CallbackQuery):
    _, plan_id, period = callback.data.split(":")
    plan = PLANS[plan_id]

    stars = plan[f"price_{period}_stars"]
    period_label = "месяц" if period == "month" else "год"

    await callback.message.answer_invoice(
        title=f"{plan['name']} — {period_label}",
        description=(
            f"Доступ к тарифу {plan['name']} на {period_label}.\n"
            f"Лимит: {plan['chars_per_month']:,} символов/мес."
        ),
        payload=f"stars:{plan_id}:{period}",
        currency="XTR",
        prices=[LabeledPrice(label="XTR", amount=stars)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    """Telegram требует ответить на pre_checkout_query в течение 10 секунд."""
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message):
    payment: SuccessfulPayment = message.successful_payment
    payload = payment.invoice_payload  # "stars:basic:month"

    if not payload.startswith("stars:"):
        return

    _, plan_id, period = payload.split(":")
    plan = PLANS.get(plan_id)
    if not plan:
        logger.error("Неизвестный план в payload: %s", payload)
        return

    stars_paid = payment.total_amount
    await activate_subscription(
        user_id=message.from_user.id,
        plan=plan_id,
        period=period,
        provider="stars",
        provider_id=payment.telegram_payment_charge_id,
        amount=stars_paid,
        currency="XTR"
    )

    period_label = "месяц" if period == "month" else "год"
    await message.answer(
        f"✅ Оплата прошла! {stars_paid}⭐ получено.\n"
        f"Тариф **{plan['name']}** активирован на {period_label}.\n\n"
        f"Лимит: {plan['chars_per_month']:,} символов/мес.\n"
        f"Проверь командой /status",
        parse_mode="Markdown"
    )
    logger.info(
        "Stars-оплата: user=%s plan=%s период=%s stars=%s charge_id=%s",
        message.from_user.id, plan_id, period, stars_paid,
        payment.telegram_payment_charge_id
    )
