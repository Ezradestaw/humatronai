from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.services.subscription_service import PLAN_LIMITS

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    student_usd = PLAN_LIMITS["student"]["price_usd"]
    pro_usd = PLAN_LIMITS["pro"]["price_usd"]

    buttons = [
        [
            InlineKeyboardButton(
                text=f"🎓 Student Plan (${student_usd:.0f} USDT/mo - 50 files)",
                callback_data="sub_choose_student"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🚀 Pro Plan (${pro_usd:.0f} USDT/mo - 200 files)",
                callback_data="sub_choose_pro"
            )
        ],
        [
            InlineKeyboardButton(text="« Back", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_order_keyboard(tx_ref: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📤 Submit Payment Proof", callback_data=f"submit_proof_{tx_ref}")
        ],
        [
            InlineKeyboardButton(text="« Back to Plans", callback_data="menu_subscription")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_payment_approval_keyboard(tx_ref: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Approve Payment", callback_data=f"admin_pay_approve_{tx_ref}"),
            InlineKeyboardButton(text="❌ Reject Payment", callback_data=f"admin_pay_reject_{tx_ref}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
