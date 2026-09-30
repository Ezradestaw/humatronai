from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import TelegramAccount
from bot.keyboards import get_settings_keyboard, get_back_button

router = Router(name="settings_router")

def format_settings_text(notifications_enabled: bool) -> str:
    status_str = "Enabled 🔔" if notifications_enabled else "Disabled 🔕"
    return (
        "<b>⚙️ Humatron Preferences & Settings</b>\n\n"
        f"<b>Notification Alerts:</b> {status_str}\n\n"
        "• <i>Enabled:</i> You will receive notifications when PDF jobs finish, when payments succeed, and for essential announcements.\n"
        "• <i>Disabled:</i> All non-essential messages are muted.\n\n"
        "Tap the button below to toggle:"
    )

@router.message(Command("settings"))
async def handle_settings_command(message: Message, tg_account: TelegramAccount):
    text = format_settings_text(tg_account.notifications_enabled)
    await message.answer(text=text, parse_mode="HTML", reply_markup=get_settings_keyboard(tg_account.notifications_enabled))

@router.callback_query(F.data == "menu_settings")
async def handle_settings_callback(callback: CallbackQuery, tg_account: TelegramAccount):
    text = format_settings_text(tg_account.notifications_enabled)
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=get_settings_keyboard(tg_account.notifications_enabled))
    await callback.answer()

@router.callback_query(F.data == "settings_toggle_notifications")
async def handle_toggle_notifications(callback: CallbackQuery, session: AsyncSession, tg_account: TelegramAccount):
    tg_account.notifications_enabled = not tg_account.notifications_enabled
    await session.commit()

    text = format_settings_text(tg_account.notifications_enabled)
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=get_settings_keyboard(tg_account.notifications_enabled))
    await callback.answer("Settings updated!", show_alert=False)
