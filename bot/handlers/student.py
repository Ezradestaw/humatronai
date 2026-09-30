from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import User
from core.services.student_service import StudentService
from bot.keyboards import get_student_keyboard, get_cancel_keyboard, get_back_button
from bot.states import StudentStates

router = Router(name="student_router")

STUDENT_INTRO = (
    "<b>🎓 Humatron Student Discount Program</b>\n\n"
    "Humatron is built for university and college students. Verified students receive:\n"
    "• <b>50 files/month</b> (5x standard free tier)\n"
    "• Access to specialized academic document tools\n"
    "• 90% discount on extended processing capacity\n\n"
    "<b>Eligibility:</b> Any currently enrolled student with an active university/college email "
    "address (.edu, .edu.et, .ac.*).\n\n"
    "<i>Note: Sensitive verification documents (e.g. Student ID cards) must only be submitted "
    "through our encrypted web portal to ensure strict student privacy.</i>"
)

@router.message(Command("student"))
async def handle_student_command(message: Message, session: AsyncSession, user: User, state: FSMContext):
    await state.clear()
    status_info = await StudentService.get_student_status(session, user.id)
    await message.answer(
        text=STUDENT_INTRO,
        parse_mode="HTML",
        reply_markup=get_student_keyboard(status_info["is_verified"])
    )

@router.callback_query(F.data == "menu_student")
async def handle_student_callback(callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext):
    await state.clear()
    status_info = await StudentService.get_student_status(session, user.id)
    await callback.message.edit_text(
        text=STUDENT_INTRO,
        parse_mode="HTML",
        reply_markup=get_student_keyboard(status_info["is_verified"])
    )
    await callback.answer()

@router.callback_query(F.data == "student_enter_email")
async def handle_enter_email_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(StudentStates.waiting_for_email)
    await callback.message.edit_text(
        text=(
            "✉️ <b>Enter Your Educational Email</b>\n\n"
            "Please send your official college or university email address (e.g., <code>student@aau.edu.et</code> or <code>user@university.edu</code>):\n\n"
            "<i>We will send a 6-digit confirmation code to verify your active student status.</i>"
        ),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(StudentStates.waiting_for_email, F.text)
async def handle_student_email_submission(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User
):
    email = message.text.strip()
    success, msg, rec = await StudentService.request_student_verification(
        session=session,
        user_id=user.id,
        educational_email=email,
        institution_name="University/College"
    )

    if not success:
        await message.answer(
            f"⚠️ {msg}\n\nPlease try again with an accredited student email.",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(educational_email=email)
    await state.set_state(StudentStates.waiting_for_code)

    await message.answer(
        text=(
            "📬 <b>Verification Code Dispatched!</b>\n\n"
            f"We have registered your verification request for <code>{email}</code>.\n\n"
            "Please check your university inbox and reply with the <b>6-digit code</b>.\n"
            f"(Demo / Test Verification Code: <code>{rec.verification_code}</code>)"
        ),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.callback_query(F.data == "student_enter_code")
async def handle_enter_code_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(StudentStates.waiting_for_code)
    await callback.message.edit_text(
        text="🔢 <b>Enter 6-Digit Code</b>\n\nPlease reply with the verification code sent to your academic email:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(StudentStates.waiting_for_code, F.text)
async def handle_student_code_verification(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User
):
    code = message.text.strip()
    success, msg = await StudentService.confirm_student_code(session, user.id, code)

    if not success:
        await message.answer(
            f"⚠️ {msg}",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.clear()
    await message.answer(
        text=f"🎓 <b>{msg}</b>\n\nYour account has been upgraded to the Student Discount Tier with 50 monthly files!",
        parse_mode="HTML",
        reply_markup=get_back_button("main_menu")
    )
