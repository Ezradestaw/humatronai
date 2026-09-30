import io
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import User, TelegramAccount
from core.services.pdf_service import PDFService
from core.services.subscription_service import SubscriptionService
from bot.keyboards import get_pdf_tools_keyboard, get_cancel_keyboard, get_back_button
from bot.states import PDFStates
from core.utils.validators import sanitize_filename
from core.utils.logger import logger
from core.config import settings

router = Router(name="pdf_router")

PDF_INTRO_TEXT = (
    "<b>📄 Humatron PDF Tools</b>\n\n"
    "Select an operation below, then send your PDF document:\n\n"
    "• <b>Inspect & Pages:</b> Read page count, title, and file specifications.\n"
    "• <b>Compress PDF:</b> Reduce document file size for faster emailing/sharing.\n"
    "• <b>Extract Text:</b> Convert readable document content into clean text.\n\n"
    f"<i>Limits: Max {settings.max_pdf_size_mb} MB and {settings.max_pdf_pages} pages per document.</i>"
)

@router.message(Command("pdf"))
async def handle_pdf_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(text=PDF_INTRO_TEXT, parse_mode="HTML", reply_markup=get_pdf_tools_keyboard())

@router.callback_query(F.data == "menu_pdf")
async def handle_pdf_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(text=PDF_INTRO_TEXT, parse_mode="HTML", reply_markup=get_pdf_tools_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("pdf_action_"))
async def handle_pdf_action_selection(callback: CallbackQuery, state: FSMContext):
    action = callback.data.replace("pdf_action_", "")
    await state.update_data(pdf_action=action)
    await state.set_state(PDFStates.waiting_for_file)

    action_names = {
        "inspect": "Inspect Document & Page Count",
        "compress": "Compress Document",
        "extract": "Extract Text",
        "info": "Document Information",
    }
    name = action_names.get(action, "Processing")

    await callback.message.edit_text(
        text=(
            f"<b>Selected Operation:</b> {name}\n\n"
            "📎 <b>Please upload your PDF file now.</b>\n"
            f"<i>Maximum file size: {settings.max_pdf_size_mb} MB</i>"
        ),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "pdf_cancel")
async def handle_pdf_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        text="❌ Operation cancelled.\n\n" + PDF_INTRO_TEXT,
        parse_mode="HTML",
        reply_markup=get_pdf_tools_keyboard()
    )
    await callback.answer()

@router.message(PDFStates.waiting_for_file, F.document)
async def handle_pdf_file_upload(
    message: Message,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    user: User
):
    doc = message.document
    if not doc:
        await message.answer("Please send a valid PDF document.", reply_markup=get_cancel_keyboard())
        return

    # Check MIME type and extension
    is_pdf_mime = doc.mime_type in ["application/pdf", "application/x-pdf"]
    is_pdf_ext = doc.file_name and doc.file_name.lower().endswith(".pdf")
    if not (is_pdf_mime or is_pdf_ext):
        await message.answer(
            "⚠️ Invalid file type. Only PDF documents (*.pdf) are supported.",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Check file size before downloading
    max_bytes = settings.max_pdf_size_mb * 1024 * 1024
    if doc.file_size and doc.file_size > max_bytes:
        await message.answer(
            f"⚠️ File too large. The document exceeds the {settings.max_pdf_size_mb} MB limit.",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Check usage quota
    can_process, used, limit = await SubscriptionService.check_quota(session, user.id)
    if not can_process:
        await state.clear()
        await message.answer(
            f"⚠️ <b>Monthly Quota Reached</b>\n\n"
            f"You have used {used} of your {limit} monthly files.\n"
            "Please upgrade your plan to continue processing documents.",
            parse_mode="HTML",
            reply_markup=get_back_button("menu_subscription")
        )
        return

    # Retrieve selected action
    state_data = await state.get_data()
    action = state_data.get("pdf_action", "inspect")
    await state.clear()

    status_msg = await message.answer("⏳ Downloading and verifying document safely...")

    try:
        # Download document into in-memory buffer
        file_obj = await bot.get_file(doc.file_id)
        if not file_obj.file_path:
            await status_msg.edit_text("Failed to download file from Telegram servers. Please try again.")
            return

        file_bytes_stream = await bot.download_file(file_obj.file_path)
        data = file_bytes_stream.read()

        safe_filename = sanitize_filename(doc.file_name or "document.pdf")

        if action in ["inspect", "info"]:
            await status_msg.edit_text("🔍 Inspecting PDF structure...")
            info = PDFService.inspect_pdf(data, safe_filename)
            await SubscriptionService.increment_usage(session, user.id)
            await PDFService.log_processed_document(session, user.id, safe_filename, data, "inspect", info["page_count"])

            result_text = (
                "<b>📄 PDF Inspection Result</b>\n\n"
                f"<b>File Name:</b> <code>{safe_filename}</code>\n"
                f"<b>Total Pages:</b> {info['page_count']}\n"
                f"<b>File Size:</b> {info['size_kb']} KB ({info['size_mb']} MB)\n"
                f"<b>Title:</b> {info['title']}\n"
                "<b>Status:</b> Validated & Structurally Sound ✅\n\n"
                "<i>Quota updated.</i>"
            )
            await status_msg.edit_text(result_text, parse_mode="HTML", reply_markup=get_back_button("menu_pdf"))

        elif action == "compress":
            await status_msg.edit_text("🗜️ Compressing PDF streams...")
            compressed_bytes, stats = PDFService.compress_pdf(data)
            await SubscriptionService.increment_usage(session, user.id)
            await PDFService.log_processed_document(session, user.id, safe_filename, compressed_bytes, "compress", stats["pages"])

            out_file = BufferedInputFile(compressed_bytes, filename=f"compressed_{safe_filename}")
            await status_msg.delete()
            caption = (
                "<b>✅ Compression Complete</b>\n\n"
                f"• Original Size: {stats['original_size_kb']} KB\n"
                f"• Compressed Size: {stats['new_size_kb']} KB\n"
                f"• Space Saved: {stats['savings_percent']}%\n"
                f"• Pages: {stats['pages']}"
            )
            await message.answer_document(document=out_file, caption=caption, parse_mode="HTML", reply_markup=get_back_button("menu_pdf"))

        elif action == "extract":
            await status_msg.edit_text("📝 Extracting text content...")
            text_result = PDFService.extract_text(data)
            await SubscriptionService.increment_usage(session, user.id)
            await PDFService.log_processed_document(session, user.id, safe_filename, data, "extract")

            if len(text_result) <= 3000:
                await status_msg.edit_text(
                    f"<b>📝 Extracted Text Preview:</b>\n\n<pre>{text_result[:2500]}</pre>",
                    parse_mode="HTML",
                    reply_markup=get_back_button("menu_pdf")
                )
            else:
                # Text is long, send as a .txt file attachment
                txt_bytes = text_result.encode("utf-8")
                txt_file = BufferedInputFile(txt_bytes, filename=f"extracted_{safe_filename}.txt")
                await status_msg.delete()
                await message.answer_document(
                    document=txt_file,
                    caption="<b>✅ Text Extraction Complete</b>\n\nExtracted content has been formatted into the text file attached above.",
                    parse_mode="HTML",
                    reply_markup=get_back_button("menu_pdf")
                )

    except ValueError as val_err:
        logger.warning(f"PDF validation error for user {user.id}: {val_err}")
        await status_msg.edit_text(f"⚠️ <b>Processing Error:</b> {str(val_err)}", parse_mode="HTML", reply_markup=get_back_button("menu_pdf"))
    except Exception as e:
        logger.error(f"Unexpected error processing PDF: {e}", exc_info=True)
        await status_msg.edit_text(
            "⚠️ Something went wrong while processing your document. Please try again with a different file.",
            reply_markup=get_back_button("menu_pdf")
        )
