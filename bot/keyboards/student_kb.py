from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.config import settings

def get_student_keyboard(is_verified: bool) -> InlineKeyboardMarkup:
    buttons = []
    if not is_verified:
        buttons.append([
            InlineKeyboardButton(text="✉️ Enter Educational Email", callback_data="student_enter_email"),
            InlineKeyboardButton(text="🔢 Enter Verification Code", callback_data="student_enter_code")
        ])
        buttons.append([
            InlineKeyboardButton(text="🌐 Verify on Humatron Web", url=f"{settings.humatron_api_base_url}/verify-student")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="🎉 View Student Benefits", callback_data="menu_subscription")
        ])

    buttons.append([
        InlineKeyboardButton(text="« Back", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
