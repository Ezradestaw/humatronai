from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import User, TelegramAccount
from core.services.account_service import AccountService
from bot.keyboards import get_main_keyboard, get_back_button
from core.config import settings

router = Router(name="start_router")

WELCOME_TEXT = (
    "<b>Welcome to Humatron.</b>\n\n"
    "Humatron provides digital tools designed to help students work, learn, "
    "and process documents more efficiently.\n\n"
    f"Official Website: <a href='{settings.humatron_api_base_url}'>humatron.me</a>\n\n"
    "Select an option from the menu below to get started:"
)

@router.message(CommandStart())
async def handle_start(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    tg_account: TelegramAccount,
    user: User
):
    args = command.args
    if args:
        # Check for deep link parameters
        if args.startswith("link_"):
            token = args.replace("link_", "").strip()
            # If a user clicked a web linking deep-link
            success, msg = await AccountService.redeem_linking_token(session, token, user.id)
            if success:
                await message.answer(f"✅ {msg}\n\n" + WELCOME_TEXT, parse_mode="HTML", reply_markup=get_main_keyboard(user.is_admin))
                return
            else:
                await message.answer(f"⚠️ Account Linking: {msg}\n\n" + WELCOME_TEXT, parse_mode="HTML", reply_markup=get_main_keyboard(user.is_admin))
                return

    await message.answer(
        text=WELCOME_TEXT,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=get_main_keyboard(user.is_admin)
    )

@router.callback_query(F.data == "main_menu")
async def handle_main_menu(
    callback: CallbackQuery,
    user: User
):
    await callback.message.edit_text(
        text=WELCOME_TEXT,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=get_main_keyboard(user.is_admin)
    )
    await callback.answer()
