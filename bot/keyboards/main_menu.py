from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.config import settings

def get_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🌐 Open Humatron", url=settings.humatron_api_base_url)
        ],
        [
            InlineKeyboardButton(text="👤 My Account", callback_data="menu_account"),
            InlineKeyboardButton(text="📄 PDF Tools", callback_data="menu_pdf"),
        ],
        [
            InlineKeyboardButton(text="📊 My Usage", callback_data="menu_usage"),
            InlineKeyboardButton(text="💳 Subscription", callback_data="menu_subscription"),
        ],
        [
            InlineKeyboardButton(text="🎓 Student Discount", callback_data="menu_student"),
            InlineKeyboardButton(text="❓ Help", callback_data="menu_help"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Settings", callback_data="menu_settings")
        ]
    ]

    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="🛡️ Admin Dashboard", callback_data="menu_admin")
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_button(target: str = "main_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="« Back to Main Menu", callback_data=target)]
        ]
    )
