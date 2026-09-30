from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_pdf_tools_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📥 Upload & Inspect PDF", callback_data="pdf_action_inspect"),
            InlineKeyboardButton(text="🗜️ Compress PDF", callback_data="pdf_action_compress"),
        ],
        [
            InlineKeyboardButton(text="📝 Extract Text", callback_data="pdf_action_extract"),
            InlineKeyboardButton(text="📄 Document Info", callback_data="pdf_action_info"),
        ],
        [
            InlineKeyboardButton(text="« Back", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel Operation", callback_data="pdf_cancel")]
        ]
    )
