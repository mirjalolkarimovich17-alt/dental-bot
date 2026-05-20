from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config import SERVICES, WORK_HOURS
from typing import List
from database.models import Doctor
import datetime


# ─── CLIENT KEYBOARD (reply) ─────────────────────────────────────────────────

def client_main_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📅 Navbat olish")
    kb.button(text="📋 Mening navbatlarim")
    kb.button(text="🏥 Xizmatlar")
    kb.button(text="📍 Manzil / Lokatsiya")
    kb.button(text="ℹ️ Biz haqimizda")
    kb.button(text="🌐 Web saytimiz")
    kb.adjust(2, 2, 2)
    return kb.as_markup(resize_keyboard=True)


def phone_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📱 Telefon raqamimni yuborish",
              request_contact=True)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def cancel_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="❌ Bekor qilish")
    return kb.as_markup(resize_keyboard=True)


# ─── BOOKING INLINE KEYBOARDS ─────────────────────────────────────────────────

def doctors_kb(doctors: List[Doctor]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for doc in doctors:
        builder.button(
            text=f"👨‍⚕️ {doc.full_name} — {doc.specialty}",
            callback_data=f"doctor:{doc.id}"
        )
    builder.button(text="❌ Bekor qilish", callback_data="cancel_booking")
    builder.adjust(1)
    return builder.as_markup()


def days_kb(doctor_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    today = datetime.date.today()
    day_names = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
    for i in range(14):
        d = today + datetime.timedelta(days=i)
        label = f"{day_names[d.weekday()]} {d.day}.{d.month}"
        builder.button(
            text=label,
            callback_data=f"day:{doctor_id}:{d.isoformat()}"
        )
    builder.button(text="⬅️ Orqaga", callback_data="back_to_doctors")
    builder.adjust(7)
    return builder.as_markup()


def times_kb(doctor_id: int, day: str, booked: List) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    booked_strs = [t.strftime("%H:%M") for t in booked]
    for t in WORK_HOURS:
        if t in booked_strs:
            builder.button(text=f"🔴 {t}", callback_data="booked")
        else:
            builder.button(text=f"🟢 {t}", callback_data=f"time:{doctor_id}:{day}:{t}")
    builder.button(text="⬅️ Orqaga", callback_data=f"change_doctor:{doctor_id}")
    builder.adjust(4)
    return builder.as_markup()


def services_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, s in enumerate(SERVICES):
        builder.button(text=s, callback_data=f"service:{i}")
    builder.button(text="⬅️ Orqaga", callback_data="back_to_time")
    builder.adjust(1)
    return builder.as_markup()


def confirm_booking_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data="confirm_booking")
    builder.button(text="❌ Bekor qilish", callback_data="cancel_booking")
    builder.adjust(2)
    return builder.as_markup()


def skip_note_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ Davom etish", callback_data="skip_note")
    builder.adjust(1)
    return builder.as_markup()


# ─── MY BOOKINGS ─────────────────────────────────────────────────────────────

def my_bookings_kb(bookings) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for b in bookings:
        if b.status.value in ("pending", "confirmed"):
            label = f"❌ #{b.id} ni bekor qilish"
            builder.button(text=label, callback_data=f"cancel:{b.id}")
    builder.adjust(1)
    return builder.as_markup()


# ─── DOCTOR KEYBOARD (reply) ─────────────────────────────────────────────────

def doctor_main_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="👥 Mening mijozlarim")
    kb.button(text="📋 Navbatlarim")
    kb.button(text="⏸️ Tanaffus qo'shish")
    kb.button(text="▶️ Tanaffusni o'chirish")
    kb.button(text="🏠 Bosh menyu")
    kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True)


def booking_action_kb(booking_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"doc_confirm:{booking_id}")
    builder.button(text="❌ Rad etish", callback_data=f"doc_cancel:{booking_id}")
    builder.adjust(2)
    return builder.as_markup()


# ─── ADMIN KEYBOARD (reply) ──────────────────────────────────────────────────

def admin_main_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Shifokor qo'shish")
    kb.button(text="🗑️ Shifokor o'chirish")
    kb.button(text="📊 Statistika")
    kb.button(text="📋 Barcha buyurtmalar")
    kb.button(text="📥 Excel yuklash")
    kb.button(text="💌 Eslatma yuborish")
    kb.button(text="💬 Xabar yozish")
    kb.button(text="🏠 Bosh menyu")
    kb.adjust(2, 2, 2, 2)
    return kb.as_markup(resize_keyboard=True)


def doctors_remove_kb(doctors: List[Doctor]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for doc in doctors:
        builder.button(
            text=f"🗑️ {doc.full_name}",
            callback_data=f"remove_doctor:{doc.id}"
        )
    builder.button(text="❌ Bekor qilish", callback_data="cancel_admin")
    builder.adjust(1)
    return builder.as_markup()


def confirm_remove_kb(doctor_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, o'chirish", callback_data=f"confirm_remove:{doctor_id}")
    builder.button(text="❌ Yo'q", callback_data="cancel_admin")
    builder.adjust(2)
    return builder.as_markup()
