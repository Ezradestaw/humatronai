import pytest
from bot.keyboards import (
    get_main_keyboard,
    get_account_keyboard,
    get_pdf_tools_keyboard,
    get_subscription_keyboard,
    get_payment_order_keyboard,
    get_admin_payment_approval_keyboard,
    get_student_keyboard,
    get_help_keyboard,
    get_settings_keyboard,
    get_admin_keyboard,
)
from bot.handlers.admin import is_authorized_admin
from bot.handlers.help import HELP_ARTICLES
from bot.handlers.usage import format_usage_text
from core.models import User

def test_keyboards_structure():
    # Main keyboard for normal user
    kb_user = get_main_keyboard(is_admin=False)
    assert any("PDF Tools" in btn.text for row in kb_user.inline_keyboard for btn in row)
    assert not any("Admin" in btn.text for row in kb_user.inline_keyboard for btn in row)

    # Main keyboard for admin user
    kb_admin = get_main_keyboard(is_admin=True)
    assert any("Admin Dashboard" in btn.text for row in kb_admin.inline_keyboard for btn in row)

    # PDF keyboard
    pdf_kb = get_pdf_tools_keyboard()
    assert any("Compress PDF" in btn.text for row in pdf_kb.inline_keyboard for btn in row)
    assert any("Extract Text" in btn.text for row in pdf_kb.inline_keyboard for btn in row)

    # Subscription keyboard
    sub_kb = get_subscription_keyboard()
    assert any("Student Plan" in btn.text for row in sub_kb.inline_keyboard for btn in row)
    assert any("Pro Plan" in btn.text for row in sub_kb.inline_keyboard for btn in row)

    # Payment order keyboard
    order_kb = get_payment_order_keyboard("HUMA-12345")
    assert any("Submit Payment Proof" in btn.text for row in order_kb.inline_keyboard for btn in row)

    # Admin approval keyboard
    admin_pay_kb = get_admin_payment_approval_keyboard("HUMA-12345")
    assert any("Approve Payment" in btn.text for row in admin_pay_kb.inline_keyboard for btn in row)
    assert any("Reject Payment" in btn.text for row in admin_pay_kb.inline_keyboard for btn in row)

def test_admin_authorization():
    admin_user = User(is_admin=True)
    normal_user = User(is_admin=False)

    assert is_authorized_admin(99999, admin_user) is True
    assert is_authorized_admin(99999, normal_user) is False

def test_help_articles_content():
    assert "start" in HELP_ARTICLES
    assert "account" in HELP_ARTICLES
    assert "pdf" in HELP_ARTICLES
    assert "payments" in HELP_ARTICLES
    assert "support" in HELP_ARTICLES
    assert "zuhuraengineering@gmail.com" in HELP_ARTICLES["support"]

def test_usage_formatting():
    sample_data = {
        "plan_name": "Student Discount",
        "used": 12,
        "limit": 50,
        "remaining": 38,
        "renewal": "15 October 2026"
    }
    rendered = format_usage_text(sample_data)
    assert "Student Discount" in rendered
    assert "12 / 50 files" in rendered
    assert "38 files" in rendered
