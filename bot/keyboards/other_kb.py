from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.config import settings

def get_help_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🚀 Getting Started", callback_data="help_cat_start"),
            InlineKeyboardButton(text="👤 Account & Linking", callback_data="help_cat_account"),
        ],
        [
            InlineKeyboardButton(text="📄 PDF Tools Guide", callback_data="help_cat_pdf"),
            InlineKeyboardButton(text="💳 Plans & Payments", callback_data="help_cat_payments"),
        ],
        [
            InlineKeyboardButton(text="🎓 Student Verification", callback_data="help_cat_student"),
            InlineKeyboardButton(text="🛠️ Technical Support", callback_data="help_cat_support"),
        ],
        [
            InlineKeyboardButton(text="🌐 Official Humatron Website", url=settings.humatron_api_base_url)
        ],
        [
            InlineKeyboardButton(text="« Back", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_settings_keyboard(notifications_enabled: bool) -> InlineKeyboardMarkup:
    status_icon = "🔔 Enabled" if notifications_enabled else "🔕 Disabled"
    toggle_text = "Turn Off Notifications" if notifications_enabled else "Turn On Notifications"

    buttons = [
        [
            InlineKeyboardButton(text=f"Notifications: {status_icon}", callback_data="settings_toggle_notifications")
        ],
        [
            InlineKeyboardButton(text=toggle_text, callback_data="settings_toggle_notifications")
        ],
        [
            InlineKeyboardButton(text="« Back", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📊 Bot & System Statistics", callback_data="admin_stats"),
            InlineKeyboardButton(text="📢 Broadcast Announcement", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton(text="« Back", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
