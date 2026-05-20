from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    waiting_phone = State()
    waiting_name = State()


class BookingStates(StatesGroup):
    choosing_doctor = State()
    choosing_day = State()
    choosing_time = State()
    choosing_service = State()
    writing_note = State()
    confirming = State()


class AdminStates(StatesGroup):
    adding_doctor_name = State()
    adding_doctor_specialty = State()
    adding_doctor_phone = State()
    adding_doctor_tg = State()
    removing_doctor = State()
    broadcasting = State()
    messaging_user = State()
    messaging_user_text = State()


class DoctorStates(StatesGroup):
    adding_break_date = State()
    adding_break_time = State()
    removing_break_date = State()
