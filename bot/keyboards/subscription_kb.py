from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.services.subscription_service import PLAN_LIMITS

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    student_price = PLAN_LIMITS["student"]["price_etb"]
    pro_price_usd = PLAN_LIMITS["pro"]["price_usd"]
    pro_price_etb = PLAN_LIMITS["pro"]["price_etb"]

    buttons = [
        [
            InlineKeyboardButton(
                text=f"🎓 Student Plan ({student_price:.0f} ETB / $5)",
                callback_data="sub_choose_student"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🚀 Pro Plan (${pro_price_usd:.0f} / {pro_price_etb:.0f} ETB)",
                callback_data="sub_choose_pro"
            )
        ],
        [
            InlineKeyboardButton(text="« Back", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_method_keyboard(tier: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📱 Pay with Telebirr (ETB)", callback_data=f"pay_telebirr_{tier}")
        ],
        [
            InlineKeyboardButton(text="🟡 Pay with Binance Pay (USDT/USD)", callback_data=f"pay_binance_{tier}")
        ],
        [
            InlineKeyboardButton(text="« Back", callback_data="menu_subscription")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
