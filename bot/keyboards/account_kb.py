from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.config import settings

def get_account_keyboard(is_linked: bool) -> InlineKeyboardMarkup:
    buttons = []
    if not is_linked:
        buttons.append([
            InlineKeyboardButton(text="🔗 Link Humatron Account", callback_data="account_link")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="🔓 Unlink Telegram Account", callback_data="account_unlink")
        ])

    buttons.append([
        InlineKeyboardButton(text="🌐 Manage on Website", url=f"{settings.humatron_api_base_url}/account")
    ])
    buttons.append([
        InlineKeyboardButton(text="« Back", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
