from aiogram.fsm.state import State, StatesGroup

class PDFStates(StatesGroup):
    waiting_for_file = State()
    choosing_operation = State()

class StudentStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_code = State()

class PaymentStates(StatesGroup):
    waiting_for_proof = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()
