from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from bot.keyboards import get_help_keyboard, get_back_button
from core.config import settings

router = Router(name="help_router")

HELP_MAIN_TEXT = (
    "<b>❓ Humatron Help Center</b>\n\n"
    "Humatron is a dedicated technology platform providing productivity and document processing "
    "tools for students and academic researchers.\n\n"
    "Select a topic below for detailed guidance, or contact our support team directly:"
)

HELP_ARTICLES = {
    "start": (
        "<b>🚀 Getting Started with Humatron</b>\n\n"
        "1. <b>Commands & Navigation:</b> Use /start at any time to open the main menu.\n"
        "2. <b>Process Documents:</b> Go to <i>PDF Tools</i> to compress or extract text from course materials.\n"
        "3. <b>Track Limits:</b> Check <i>My Usage</i> to see your remaining monthly document allowance.\n"
        f"4. <b>Web Platform:</b> Access additional features at <a href='{settings.humatron_api_base_url}'>humatron.me</a>."
    ),
    "account": (
        "<b>👤 Account & Security</b>\n\n"
        "• <b>Is a password needed in Telegram?</b> No. Never send passwords via Telegram.\n"
        "• <b>Account Linking:</b> In <i>My Account</i>, tap <i>Link Humatron Account</i> to generate a secure one-time 10-minute token.\n"
        "• <b>Multi-Device Sync:</b> Linking syncs your document quota and subscription between the website and Telegram."
    ),
    "pdf": (
        "<b>📄 PDF Tools FAQ</b>\n\n"
        f"• <b>File Size Limit:</b> Up to {settings.max_pdf_size_mb} MB per document.\n"
        f"• <b>Page Count Limit:</b> Up to {settings.max_pdf_pages} pages.\n"
        "• <b>Privacy & Retention:</b> Uploaded files are processed in isolated memory and temporary files are purged immediately."
    ),
    "payments": (
        "<b>💳 Plans & Payment Support</b>\n\n"
        "• <b>Domestic Payments:</b> Telebirr is integrated for all users in Ethiopia (ETB).\n"
        "• <b>International Payments:</b> Binance Pay allows seamless payment via USDT / USD.\n"
        "• <b>Activation:</b> Quotas activate automatically once payment confirmation is received."
    ),
    "student": (
        "<b>🎓 Student Discount Program</b>\n\n"
        "• <b>Who qualifies?</b> Any active university or college student with an institutional email (.edu, .edu.et, .ac.*).\n"
        "• <b>Benefit:</b> 50 free files per month (5x the basic tier) plus 90% discount on high-volume plans.\n"
        "• <b>Verification:</b> Submit your student email under <i>Student Discount</i> in the main menu."
    ),
    "support": (
        "<b>🛠️ Official Humatron Support</b>\n\n"
        "Need help with a stuck job or account issue?\n\n"
        "• <b>Official Website:</b> <a href='https://humatron.me'>humatron.me</a>\n"
        "• <b>Contact Portal:</b> <a href='https://humatron.me/contact'>humatron.me/contact</a>\n"
        "• <b>Email:</b> <code>zuhuraengineering@gmail.com</code>\n"
        "• <b>Telegram Community:</b> @ZuhuraEngineering"
    )
}

@router.message(Command("help"))
async def handle_help_command(message: Message):
    await message.answer(text=HELP_MAIN_TEXT, parse_mode="HTML", reply_markup=get_help_keyboard())

@router.callback_query(F.data == "menu_help")
async def handle_help_callback(callback: CallbackQuery):
    await callback.message.edit_text(text=HELP_MAIN_TEXT, parse_mode="HTML", reply_markup=get_help_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("help_cat_"))
async def handle_help_category(callback: CallbackQuery):
    cat_key = callback.data.replace("help_cat_", "")
    content = HELP_ARTICLES.get(cat_key, HELP_MAIN_TEXT)
    await callback.message.edit_text(
        text=content,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=get_back_button("menu_help")
    )
    await callback.answer()
