from aiogram import Router
from bot.handlers.start import router as start_router
from bot.handlers.account import router as account_router
from bot.handlers.pdf import router as pdf_router
from bot.handlers.usage import router as usage_router
from bot.handlers.subscription import router as subscription_router
from bot.handlers.student import router as student_router
from bot.handlers.help import router as help_router
from bot.handlers.settings import router as settings_router
from bot.handlers.admin import router as admin_router

def get_main_router() -> Router:
    main_router = Router(name="main_bot_router")
    main_router.include_router(start_router)
    main_router.include_router(account_router)
    main_router.include_router(pdf_router)
    main_router.include_router(usage_router)
    main_router.include_router(subscription_router)
    main_router.include_router(student_router)
    main_router.include_router(help_router)
    main_router.include_router(settings_router)
    main_router.include_router(admin_router)
    return main_router
