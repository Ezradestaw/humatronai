from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import User
from core.services.subscription_service import SubscriptionService, PLAN_LIMITS
from core.services.payment_service import PaymentService
from bot.keyboards import (
    get_subscription_keyboard,
    get_payment_method_keyboard,
    get_back_button
)

router = Router(name="subscription_router")

def format_subscription_overview(current_sub: dict) -> str:
    student_info = PLAN_LIMITS["student"]
    pro_info = PLAN_LIMITS["pro"]

    return (
        "<b>💳 Humatron Subscriptions & Plans</b>\n\n"
        f"<b>Your Current Plan:</b> {current_sub['plan_name']}\n"
        f"<b>Status:</b> Active\n"
        f"<b>Quota:</b> {current_sub['used']} / {current_sub['limit']} files\n\n"
        "<b>Available Tiers:</b>\n\n"
        f"🎓 <b>Student Plan</b> — {student_info['price_etb']:.0f} ETB / ${student_info['price_usd']:.0f} per month\n"
        f"• {student_info['files']} files/month quota\n"
        "• Unlocks full student suite & faster processing\n\n"
        f"🚀 <b>Pro Plan</b> — ${pro_info['price_usd']:.0f} USD ({pro_info['price_etb']:.0f} ETB) per month\n"
        f"• {pro_info['files']} files/month high-volume quota\n"
        "• Priority background processing queue\n"
        "• Extended multi-tool document operations\n\n"
        "<i>Select a tier below to upgrade:</i>"
    )

@router.message(Command("subscription"))
async def handle_subscription_command(message: Message, session: AsyncSession, user: User):
    usage_data = await SubscriptionService.get_usage_dashboard(session, user.id)
    text = format_subscription_overview(usage_data)
    await message.answer(text=text, parse_mode="HTML", reply_markup=get_subscription_keyboard())

@router.callback_query(F.data == "menu_subscription")
async def handle_subscription_callback(callback: CallbackQuery, session: AsyncSession, user: User):
    usage_data = await SubscriptionService.get_usage_dashboard(session, user.id)
    text = format_subscription_overview(usage_data)
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=get_subscription_keyboard())
    await callback.answer()

@router.callback_query(F.data.in_(["sub_choose_student", "sub_choose_pro"]))
async def handle_choose_tier(callback: CallbackQuery):
    tier = "student" if callback.data == "sub_choose_student" else "pro"
    tier_title = "Student Plan" if tier == "student" else "Pro Plan"

    text = (
        f"<b>Selected: {tier_title}</b>\n\n"
        "Choose your preferred payment method:\n\n"
        "• <b>Telebirr:</b> For domestic Ethiopian Birr (ETB) payments.\n"
        "• <b>Binance Pay:</b> For international or cryptocurrency payments (USDT/USD)."
    )
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=get_payment_method_keyboard(tier))
    await callback.answer()

@router.callback_query(F.data.startswith("pay_telebirr_"))
async def handle_pay_telebirr(callback: CallbackQuery, session: AsyncSession, user: User):
    tier = callback.data.replace("pay_telebirr_", "")
    order = await PaymentService.initiate_subscription_payment(
        session=session,
        user_id=user.id,
        plan_tier_str=tier,
        provider_name="telebirr"
    )

    text = (
        "<b>📱 Telebirr Checkout Instructions</b>\n\n"
        f"<b>Reference ID:</b> <code>{order['transaction_ref']}</code>\n"
        f"<b>Total Amount:</b> <b>{order['amount']:.2f} ETB</b>\n\n"
        f"{order['instructions']}\n\n"
        f"<a href='{order['checkout_url']}'>👉 Click Here to Open Telebirr Payment Portal</a>"
    )
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=get_back_button("menu_subscription")
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pay_binance_"))
async def handle_pay_binance(callback: CallbackQuery, session: AsyncSession, user: User):
    tier = callback.data.replace("pay_binance_", "")
    order = await PaymentService.initiate_subscription_payment(
        session=session,
        user_id=user.id,
        plan_tier_str=tier,
        provider_name="binance_pay"
    )

    text = (
        "<b>🟡 Binance Pay Checkout Instructions</b>\n\n"
        f"<b>Reference ID:</b> <code>{order['transaction_ref']}</code>\n"
        f"<b>Total Amount:</b> <b>${order['amount']:.2f} USDT/USD</b>\n\n"
        f"{order['instructions']}\n\n"
        f"<a href='{order['checkout_url']}'>👉 Click Here to Open Binance Pay Checkout</a>"
    )
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=get_back_button("menu_subscription")
    )
    await callback.answer()
