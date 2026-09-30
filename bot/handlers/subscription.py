import os
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import User, TelegramAccount
from core.services.subscription_service import SubscriptionService, PLAN_LIMITS
from core.services.payment_service import PaymentService
from core.services.notification_service import NotificationService
from bot.keyboards import (
    get_subscription_keyboard,
    get_payment_order_keyboard,
    get_admin_payment_approval_keyboard,
    get_back_button
)
from bot.states import PaymentStates
from bot.handlers.admin import is_authorized_admin
from core.config import settings
from core.utils.logger import logger

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
        f"🎓 <b>Student Plan</b> — ${student_info['price_usd']:.0f} USDT per month\n"
        f"• {student_info['files']} files/month quota\n"
        "• Unlocks full academic suite & fast processing\n\n"
        f"🚀 <b>Pro Plan</b> — ${pro_info['price_usd']:.0f} USDT per month\n"
        f"• {pro_info['files']} files/month high-volume quota\n"
        "• Priority background processing queue\n"
        "• Extended multi-tool document operations\n\n"
        "<i>Payment Method: <b>Binance Pay (Manual Verification)</b></i>\n"
        "Select a tier below to upgrade:"
    )

@router.message(Command("subscription"))
async def handle_subscription_command(message: Message, session: AsyncSession, user: User, state: FSMContext):
    await state.clear()
    usage_data = await SubscriptionService.get_usage_dashboard(session, user.id)
    text = format_subscription_overview(usage_data)
    await message.answer(text=text, parse_mode="HTML", reply_markup=get_subscription_keyboard())

@router.callback_query(F.data == "menu_subscription")
async def handle_subscription_callback(callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext):
    await state.clear()
    usage_data = await SubscriptionService.get_usage_dashboard(session, user.id)
    text = format_subscription_overview(usage_data)
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=get_subscription_keyboard())
    await callback.answer()

@router.callback_query(F.data.in_(["sub_choose_student", "sub_choose_pro"]))
async def handle_choose_tier(callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext):
    tier = "student" if callback.data == "sub_choose_student" else "pro"
    tier_name = "Student Plan" if tier == "student" else "Pro Plan"

    order = await PaymentService.initiate_subscription_payment(
        session=session,
        user_id=user.id,
        plan_tier_str=tier,
        provider_name="binance_pay"
    )

    caption = (
        f"<b>🟡 Binance Pay — {tier_name} (${order['amount']:.2f} USDT)</b>\n\n"
        f"{order['instructions']}\n\n"
        "<i>Tap 'Submit Payment Proof' below once you have completed the transfer.</i>"
    )

    qr_path = order["qr_image_path"]
    if os.path.exists(qr_path):
        photo = FSInputFile(qr_path)
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=photo,
            caption=caption,
            parse_mode="HTML",
            reply_markup=get_payment_order_keyboard(order["transaction_ref"])
        )
    else:
        await callback.message.edit_text(
            text=caption,
            parse_mode="HTML",
            reply_markup=get_payment_order_keyboard(order["transaction_ref"])
        )
    await callback.answer()

@router.callback_query(F.data.startswith("submit_proof_"))
async def handle_submit_proof_prompt(callback: CallbackQuery, state: FSMContext):
    tx_ref = callback.data.replace("submit_proof_", "").strip()
    await state.set_state(PaymentStates.waiting_for_proof)
    await state.update_data(tx_ref=tx_ref)

    prompt = (
        "<b>📤 Submit Your Binance Payment Proof</b>\n\n"
        f"Payment Reference: <code>{tx_ref}</code>\n\n"
        "Please reply with one of the following:\n"
        "• Your <b>Binance Transaction ID (TxID)</b> or Order ID\n"
        "• Or send a <b>screenshot</b> of your completed Binance payment\n\n"
        "<i>Our admin team will review and activate your plan immediately upon verification.</i>"
    )
    await callback.message.answer(
        text=prompt,
        parse_mode="HTML",
        reply_markup=get_back_button("menu_subscription")
    )
    await callback.answer()

@router.message(PaymentStates.waiting_for_proof)
async def handle_receive_proof(
    message: Message,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    tg_account: TelegramAccount,
    user: User
):
    state_data = await state.get_data()
    tx_ref = state_data.get("tx_ref")
    if not tx_ref:
        await message.answer("Session expired. Please select a plan again from /subscription.")
        await state.clear()
        return

    proof_text = message.text or message.caption or "Screenshot submitted"
    proof_image_file_id = message.photo[-1].file_id if message.photo else None

    success, msg, tx = await PaymentService.submit_payment_proof(
        session=session,
        transaction_ref=tx_ref,
        proof_text=proof_text,
        proof_image_file_id=proof_image_file_id
    )

    await state.clear()

    if not success:
        await message.answer(f"⚠️ {msg}", reply_markup=get_back_button("menu_subscription"))
        return

    await message.answer(
        text=(
            "✅ <b>Payment Proof Submitted!</b>\n\n"
            f"<b>Reference:</b> <code>{tx_ref}</code>\n"
            f"<b>Amount:</b> ${tx.amount:.2f} USDT\n"
            f"<b>Status:</b> Under Review ⏳\n\n"
            "Thank you! Our administrators will verify the transaction on Binance and activate your subscription shortly."
        ),
        parse_mode="HTML",
        reply_markup=get_back_button("main_menu")
    )

    # Notify all administrators with actionable inline approval buttons
    admin_caption = (
        "🔔 <b>New Binance Payment Pending Approval</b>\n\n"
        f"• <b>User:</b> {tg_account.first_name} (@{tg_account.username or 'N/A'})\n"
        f"• <b>Telegram ID:</b> <code>{tg_account.telegram_id}</code>\n"
        f"• <b>Reference:</b> <code>{tx_ref}</code>\n"
        f"• <b>Amount:</b> ${tx.amount:.2f} USDT\n"
        f"• <b>Proof:</b> <code>{proof_text}</code>"
    )
    approval_kb = get_admin_payment_approval_keyboard(tx_ref)

    for admin_id in settings.admin_telegram_ids:
        try:
            if proof_image_file_id:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=proof_image_file_id,
                    caption=admin_caption,
                    parse_mode="HTML",
                    reply_markup=approval_kb
                )
            else:
                await bot.send_message(
                    chat_id=admin_id,
                    text=admin_caption,
                    parse_mode="HTML",
                    reply_markup=approval_kb
                )
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")

@router.callback_query(F.data.startswith("admin_pay_approve_"))
async def handle_admin_approve_payment(
    callback: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
    tg_account: TelegramAccount,
    user: User
):
    if not is_authorized_admin(tg_account.telegram_id, user):
        await callback.answer("⛔ Access Denied. Admin privileges required.", show_alert=True)
        return

    tx_ref = callback.data.replace("admin_pay_approve_", "").strip()
    success, msg, tx = await PaymentService.approve_manual_payment(session, tx_ref)

    if not success:
        await callback.answer(f"Error: {msg}", show_alert=True)
        return

    # Update admin message
    new_text = f"✅ <b>Payment Approved by Admin</b>\n\nReference: <code>{tx_ref}</code>\nAmount: ${tx.amount:.2f} USDT"
    if callback.message.caption:
        await callback.message.edit_caption(caption=new_text, parse_mode="HTML", reply_markup=None)
    else:
        await callback.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=None)

    await callback.answer("Payment approved!", show_alert=True)

    # Lookup target user's Telegram Account and send congratulatory activation alert
    from core.models import TelegramAccount
    from sqlalchemy import select
    user_stmt = select(TelegramAccount).where(TelegramAccount.user_id == tx.user_id)
    user_res = await session.execute(user_stmt)
    customer_account = user_res.scalar_one_or_none()

    if customer_account:
        try:
            await bot.send_message(
                chat_id=customer_account.telegram_id,
                text=(
                    "🎉 <b>Payment Approved! Your Subscription is Active</b>\n\n"
                    f"Your Binance payment (Ref: <code>{tx_ref}</code>) has been verified and approved.\n"
                    "Your new monthly document quota has been credited to your account.\n\n"
                    "Thank you for supporting Humatron! 🚀"
                ),
                parse_mode="HTML",
                reply_markup=get_back_button("menu_usage")
            )
        except Exception as e:
            logger.warning(f"Failed to send approval message to customer: {e}")

@router.callback_query(F.data.startswith("admin_pay_reject_"))
async def handle_admin_reject_payment(
    callback: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
    tg_account: TelegramAccount,
    user: User
):
    if not is_authorized_admin(tg_account.telegram_id, user):
        await callback.answer("⛔ Access Denied. Admin privileges required.", show_alert=True)
        return

    tx_ref = callback.data.replace("admin_pay_reject_", "").strip()
    success, msg, tx = await PaymentService.reject_manual_payment(session, tx_ref)

    new_text = f"❌ <b>Payment Rejected by Admin</b>\n\nReference: <code>{tx_ref}</code>"
    if callback.message.caption:
        await callback.message.edit_caption(caption=new_text, parse_mode="HTML", reply_markup=None)
    else:
        await callback.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=None)

    await callback.answer("Payment rejected.", show_alert=True)

    # Notify customer of rejection
    from core.models import TelegramAccount
    from sqlalchemy import select
    user_stmt = select(TelegramAccount).where(TelegramAccount.user_id == tx.user_id)
    user_res = await session.execute(user_stmt)
    customer_account = user_res.scalar_one_or_none()

    if customer_account:
        try:
            await bot.send_message(
                chat_id=customer_account.telegram_id,
                text=(
                    "⚠️ <b>Payment Verification Notice</b>\n\n"
                    f"Your payment with reference <code>{tx_ref}</code> could not be verified on Binance.\n"
                    "Please double check your transaction ID or contact support if you need assistance."
                ),
                parse_mode="HTML",
                reply_markup=get_back_button("menu_help")
            )
        except Exception as e:
            logger.warning(f"Failed to send rejection message to customer: {e}")
