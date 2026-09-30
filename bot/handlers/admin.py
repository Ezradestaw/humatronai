from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import User, TelegramAccount, Subscription, ProcessedFile, StudentVerification
from core.services.notification_service import NotificationService
from bot.keyboards import get_admin_keyboard, get_cancel_keyboard, get_back_button
from bot.states import AdminStates
from core.config import settings
from core.utils.logger import logger

router = Router(name="admin_router")

def is_authorized_admin(telegram_id: int, user: User) -> bool:
    """Validate admin privileges by Telegram User ID or DB admin flag."""
    if telegram_id in settings.admin_telegram_ids:
        return True
    if user and user.is_admin:
        return True
    return False

@router.message(Command("admin"))
async def handle_admin_command(
    message: Message,
    tg_account: TelegramAccount,
    user: User,
    state: FSMContext
):
    await state.clear()
    if not is_authorized_admin(tg_account.telegram_id, user):
        await message.answer("⛔ Access Denied. Administrator privileges required.")
        return

    text = (
        "<b>🛡️ Humatron Administrator Control Panel</b>\n\n"
        "Welcome to the official administrative control interface.\n"
        "Use the options below to inspect platform metrics or broadcast announcements."
    )
    await message.answer(text=text, parse_mode="HTML", reply_markup=get_admin_keyboard())

@router.callback_query(F.data == "menu_admin")
async def handle_admin_callback(
    callback: CallbackQuery,
    tg_account: TelegramAccount,
    user: User,
    state: FSMContext
):
    await state.clear()
    if not is_authorized_admin(tg_account.telegram_id, user):
        await callback.answer("⛔ Access Denied.", show_alert=True)
        return

    text = (
        "<b>🛡️ Humatron Administrator Control Panel</b>\n\n"
        "Select an administrative operation:"
    )
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=get_admin_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_stats")
async def handle_admin_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    tg_account: TelegramAccount,
    user: User
):
    if not is_authorized_admin(tg_account.telegram_id, user):
        await callback.answer("⛔ Access Denied.", show_alert=True)
        return

    # Aggregate database statistics
    total_tg_users = await session.scalar(select(func.count(TelegramAccount.id)))
    total_web_users = await session.scalar(select(func.count(User.id)).where(User.email != None))
    total_files = await session.scalar(select(func.count(ProcessedFile.id)))
    verified_students = await session.scalar(select(func.count(User.id)).where(User.is_student == True))
    active_paid_subs = await session.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.plan_tier.in_(["student", "pro"]),
            Subscription.status == "active"
        )
    )

    stats_text = (
        "<b>📊 Humatron System & Bot Statistics</b>\n\n"
        f"• <b>Telegram Users:</b> {total_tg_users or 0}\n"
        f"• <b>Linked Web Accounts:</b> {total_web_users or 0}\n"
        f"• <b>Verified Students:</b> {verified_students or 0}\n"
        f"• <b>Active Paid Subscriptions:</b> {active_paid_subs or 0}\n"
        f"• <b>Total Documents Processed:</b> {total_files or 0}\n\n"
        f"<i>Environment: {settings.environment.upper()}</i>\n"
        f"<i>Database: PostgreSQL 18 (Local)</i>"
    )

    await callback.message.edit_text(text=stats_text, parse_mode="HTML", reply_markup=get_back_button("menu_admin"))
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def handle_admin_broadcast_prompt(
    callback: CallbackQuery,
    tg_account: TelegramAccount,
    user: User,
    state: FSMContext
):
    if not is_authorized_admin(tg_account.telegram_id, user):
        await callback.answer("⛔ Access Denied.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_broadcast_text)
    await callback.message.edit_text(
        text=(
            "📢 <b>Broadcast Announcement</b>\n\n"
            "Please reply with the exact message you wish to broadcast to all active Telegram users:\n\n"
            "<i>Note: Messages will be formatted as official announcements and will only be delivered to users who have notifications enabled.</i>"
        ),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast_text, F.text)
async def handle_admin_broadcast_send(
    message: Message,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    tg_account: TelegramAccount,
    user: User
):
    if not is_authorized_admin(tg_account.telegram_id, user):
        await message.answer("⛔ Access Denied.")
        await state.clear()
        return

    announcement = message.text.strip()
    status_msg = await message.answer("⏳ Sending broadcast to active users...")

    delivered = await NotificationService.broadcast_announcement(bot, session, announcement)
    await state.clear()

    await status_msg.edit_text(
        text=f"✅ <b>Broadcast Delivered</b>\n\nSuccessfully sent announcement to {delivered} active subscribers.",
        parse_mode="HTML",
        reply_markup=get_back_button("menu_admin")
    )
