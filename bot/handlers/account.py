from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import User, TelegramAccount
from core.services.account_service import AccountService
from bot.keyboards import get_account_keyboard, get_back_button
from core.config import settings

router = Router(name="account_router")

def format_profile_text(profile: dict) -> str:
    linked_badge = "✅ Linked" if profile["is_linked"] else "⚠️ Not Linked (Telegram Only)"
    return (
        "<b>👤 My Account — Humatron</b>\n\n"
        f"<b>Name:</b> {profile['name']}\n"
        f"<b>Telegram ID:</b> <code>{profile['telegram_id']}</code>\n"
        f"<b>Humatron Account:</b> {profile['humatron_email']}\n"
        f"<b>Status:</b> {linked_badge}\n"
        f"<b>Student Verification:</b> {profile['student_status']}\n"
        f"<b>Current Plan:</b> {profile['plan_tier']}\n"
        f"<b>Member Since:</b> {profile['created_at']}\n\n"
        "<i>To access web tools and sync across devices, link your account below.</i>"
    )

@router.message(Command("account"))
async def handle_account_command(
    message: Message,
    session: AsyncSession,
    tg_account: TelegramAccount
):
    profile = await AccountService.get_profile(session, tg_account.telegram_id)
    if not profile:
        await message.answer("Account not found. Please type /start to initialize.")
        return

    text = format_profile_text(profile)
    await message.answer(text=text, parse_mode="HTML", reply_markup=get_account_keyboard(profile["is_linked"]))

@router.callback_query(F.data == "menu_account")
async def handle_account_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    tg_account: TelegramAccount
):
    profile = await AccountService.get_profile(session, tg_account.telegram_id)
    text = format_profile_text(profile)
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=get_account_keyboard(profile["is_linked"]))
    await callback.answer()

@router.callback_query(F.data == "account_link")
async def handle_account_link(
    callback: CallbackQuery,
    session: AsyncSession,
    tg_account: TelegramAccount
):
    token = await AccountService.generate_linking_token(session, tg_account.telegram_id)
    web_link_url = f"{settings.humatron_api_base_url}/link-telegram?token={token}"

    text = (
        "<b>🔗 Link Your Humatron Account</b>\n\n"
        "To securely link your Telegram account without sharing passwords:\n\n"
        f"1. Open the secure link below:\n<a href='{web_link_url}'>Click here to Confirm Account Link</a>\n\n"
        f"2. Or enter this code on the website:\n<code>{token}</code>\n\n"
        "⏱️ <i>This one-time token is valid for 10 minutes.</i>"
    )
    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=get_back_button("menu_account")
    )
    await callback.answer()

@router.callback_query(F.data == "account_unlink")
async def handle_account_unlink(
    callback: CallbackQuery,
    session: AsyncSession,
    tg_account: TelegramAccount
):
    success, msg = await AccountService.unlink_telegram_account(session, tg_account.telegram_id)
    if success:
        await callback.message.edit_text(
            text="✅ <b>Account Unlinked</b>\n\nYour Telegram profile has been detached from your Humatron web account.",
            parse_mode="HTML",
            reply_markup=get_back_button("menu_account")
        )
    else:
        await callback.message.edit_text(
            text=f"⚠️ {msg}",
            reply_markup=get_back_button("menu_account")
        )
    await callback.answer()
