from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import User
from core.services.subscription_service import SubscriptionService
from bot.keyboards import get_back_button

router = Router(name="usage_router")

def format_usage_text(data: dict) -> str:
    used = data["used"]
    limit = data["limit"]
    remaining = data["remaining"]

    # Progress bar visualization (10 segments)
    filled = min(10, int((used / max(1, limit)) * 10))
    bar = "█" * filled + "░" * (10 - filled)

    return (
        "<b>📊 My Usage — Humatron</b>\n\n"
        f"<b>Plan:</b> {data['plan_name']}\n"
        f"<b>Usage:</b> {used} / {limit} files\n"
        f"<b>Progress:</b> <code>[{bar}]</code>\n"
        f"<b>Remaining:</b> {remaining} files\n"
        f"<b>Renewal / Reset:</b> {data['renewal']}\n\n"
        "<i>Need more processing capacity? You can upgrade your plan at any time.</i>"
    )

@router.message(Command("usage"))
async def handle_usage_command(message: Message, session: AsyncSession, user: User):
    usage_data = await SubscriptionService.get_usage_dashboard(session, user.id)
    text = format_usage_text(usage_data)
    await message.answer(text=text, parse_mode="HTML", reply_markup=get_back_button("main_menu"))

@router.callback_query(F.data == "menu_usage")
async def handle_usage_callback(callback: CallbackQuery, session: AsyncSession, user: User):
    usage_data = await SubscriptionService.get_usage_dashboard(session, user.id)
    text = format_usage_text(usage_data)
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=get_back_button("main_menu"))
    await callback.answer()
