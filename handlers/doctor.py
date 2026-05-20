from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import datetime

from database.connection import AsyncSessionLocal
from database.crud import (
    get_doctor_by_telegram, get_doctor_bookings,
    update_booking_status, add_doctor_break, remove_doctor_breaks
)
from database.models import BookingStatus
from keyboards.all_kb import doctor_main_kb, client_main_kb
from states.booking_states import DoctorStates

router = Router()

STATUS_MAP = {
    "pending": "⏳ Kutilmoqda",
    "confirmed": "✅ Tasdiqlangan",
    "cancelled": "❌ Bekor",
    "completed": "🏁 Yakunlangan",
}


@router.message(F.text == "📋 Navbatlarim")
async def doctor_bookings(message: Message):
    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0
    async with AsyncSessionLocal() as session:
        doctor = await get_doctor_by_telegram(session, user_id)
        if not doctor:
            return
        today = datetime.date.today()
        bookings = await get_doctor_bookings(session, doctor.id, today)

    if not bookings:
        await message.answer(
            "📭 <b>Bugun navbat yo'q</b>\n\n"
            "Dam olish vaqti! 😊 Yangi navbatlar kelganda xabar olasiz.",
            parse_mode="HTML"
        )
        return

    text = f"📋 <b>Bugungi navbatlar — {today.strftime('%d.%m.%Y')}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for b in bookings:
        status = STATUS_MAP.get(b.status.value, "")
        text += (
            f"⏰ <b>{b.booking_time.strftime('%H:%M')}</b> — {b.user.full_name}\n"
            f"📞 {b.user.phone}  |  🦷 {b.service}\n"
            f"Holat: {status}\n\n"
        )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "👥 Mening mijozlarim")
async def doctor_clients(message: Message):
    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0
    async with AsyncSessionLocal() as session:
        doctor = await get_doctor_by_telegram(session, user_id)
        if not doctor:
            return
        bookings = await get_doctor_bookings(session, doctor.id)

    seen = {}
    for b in bookings:
        if b.user.telegram_id not in seen:
            seen[b.user.telegram_id] = b.user

    if not seen:
        await message.answer(
            "📭 <b>Hali mijozlar yo'q</b>\n\n"
            "Birinchi navbat kelganda bu yerda ko'rinadi!",
            parse_mode="HTML"
        )
        return

    text = f"👥 <b>Sizning mijozlaringiz: {len(seen)} ta</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for user in list(seen.values())[:30]:
        text += f"• {user.full_name} — {user.phone}\n"
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("doc_confirm:"))
async def doctor_confirm(callback: CallbackQuery, bot: Bot):
    booking_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        await update_booking_status(session, booking_id, BookingStatus.confirmed)
        from sqlalchemy import select
        from database.models import Booking
        from sqlalchemy.orm import selectinload
        result = await session.execute(
            select(Booking)
            .options(selectinload(Booking.user), selectinload(Booking.doctor))
            .where(Booking.id == booking_id)
        )
        booking = result.scalar_one_or_none()

    await callback.answer("✅ Tasdiqlandi!")
    await callback.message.edit_text(
        f"✅ <b>Navbat #{booking_id} tasdiqlandi!</b>",
        parse_mode="HTML"
    )

    if booking:
        try:
            await bot.send_message(
                booking.user.telegram_id,
                f"🎊 <b>Navbatingiz tasdiqlandi!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
                f"👨‍⚕️ Shifokor: <b>{booking.doctor.full_name}</b>\n"
                f"📅 {booking.booking_date.strftime('%d.%m.%Y')} ⏰ {booking.booking_time.strftime('%H:%M')}\n"
                f"🦷 Xizmat: {booking.service}\n\n"
                f"⚡ Vaqtdan oldin kelishingizni unutmang!",
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("doc_cancel:"))
async def doctor_cancel(callback: CallbackQuery, bot: Bot):
    booking_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        await update_booking_status(session, booking_id, BookingStatus.cancelled)
        from sqlalchemy import select
        from database.models import Booking
        from sqlalchemy.orm import selectinload
        result = await session.execute(
            select(Booking)
            .options(selectinload(Booking.user), selectinload(Booking.doctor))
            .where(Booking.id == booking_id)
        )
        booking = result.scalar_one_or_none()

    await callback.answer("❌ Rad etildi.")
    await callback.message.edit_text(
        f"❌ <b>Navbat #{booking_id} rad etildi.</b>",
        parse_mode="HTML"
    )

    if booking:
        try:
            await bot.send_message(
                booking.user.telegram_id,
                f"😔 <b>Navbatingiz bekor qilindi.</b>\n━━━━━━━━━━━━━━━━━━\n\n"
                f"#{booking_id} — {booking.service}\n\n"
                f"Boshqa qulay vaqtga <b>qayta navbat oling</b> — biz doimo siz uchun tayyormiz!",
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.message(F.text == "⏸️ Tanaffus qo'shish")
async def add_break_start(message: Message, state: FSMContext):
    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0
    async with AsyncSessionLocal() as session:
        doc = await get_doctor_by_telegram(session, user_id)
        if not doc:
            return
        await state.update_data(doctor_id=doc.id)

    await message.answer(
        "📅 <b>Tanaffus sanasini kiriting:</b>\n\n"
        "Format: <b>DD.MM.YYYY</b>\n"
        "Masalan: <code>15.06.2025</code>",
        parse_mode="HTML"
    )
    await state.set_state(DoctorStates.adding_break_date)


@router.message(DoctorStates.adding_break_date)
async def got_break_date(message: Message, state: FSMContext):
    try:
        d = datetime.datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Masalan: <code>15.06.2025</code>", parse_mode="HTML")
        return
    await state.update_data(break_date=d.isoformat())
    await message.answer(
        "⏰ <b>Tanaffus vaqtini kiriting:</b>\n\n"
        "Format: <b>HH:MM-HH:MM</b>\n"
        "Masalan: <code>13:00-14:00</code>",
        parse_mode="HTML"
    )
    await state.set_state(DoctorStates.adding_break_time)


@router.message(DoctorStates.adding_break_time)
async def got_break_time(message: Message, state: FSMContext):
    try:
        parts = message.text.strip().split("-")
        start = datetime.datetime.strptime(parts[0].strip(), "%H:%M").time()
        end = datetime.datetime.strptime(parts[1].strip(), "%H:%M").time()
    except Exception:
        await message.answer("❌ Noto'g'ri format. Masalan: <code>13:00-14:00</code>", parse_mode="HTML")
        return

    data = await state.get_data()
    break_date = datetime.date.fromisoformat(data["break_date"])

    async with AsyncSessionLocal() as session:
        await add_doctor_break(session, data["doctor_id"], break_date, start, end)

    await state.clear()
    await message.answer(
        f"✅ <b>Tanaffus qo'shildi!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 {break_date.strftime('%d.%m.%Y')}\n"
        f"⏰ {start.strftime('%H:%M')} — {end.strftime('%H:%M')}\n\n"
        f"Bu vaqt mijozlarga ko'rinmaydi.",
        parse_mode="HTML",
        reply_markup=doctor_main_kb()
    )


@router.message(F.text == "▶️ Tanaffusni o'chirish")
async def remove_break_start(message: Message, state: FSMContext):
    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0
    async with AsyncSessionLocal() as session:
        doc = await get_doctor_by_telegram(session, user_id)
        if not doc:
            return
        await state.update_data(doctor_id=doc.id)
    await message.answer(
        "📅 <b>Qaysi sana tanaffusini o'chirish kerak?</b>\n\n"
        "Format: <b>DD.MM.YYYY</b>\nMasalan: <code>15.06.2025</code>",
        parse_mode="HTML"
    )
    await state.set_state(DoctorStates.removing_break_date)


@router.message(DoctorStates.removing_break_date)
async def remove_break_date(message: Message, state: FSMContext):
    try:
        d = datetime.datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Masalan: <code>15.06.2025</code>", parse_mode="HTML")
        return
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        await remove_doctor_breaks(session, data["doctor_id"], d)
    await state.clear()
    await message.answer(
        f"✅ <b>{d.strftime('%d.%m.%Y')}</b> sanasidagi barcha tanaffuslar o'chirildi.\n\n"
        f"Endi bu kuni to'liq band deb hisoblanadi.",
        parse_mode="HTML",
        reply_markup=doctor_main_kb()
    )


@router.message(F.text == "🏠 Bosh menyu")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0
    async with AsyncSessionLocal() as session:
        doc = await get_doctor_by_telegram(session, user_id)
    if doc:
        await message.answer("🏠 Asosiy menyu:", reply_markup=doctor_main_kb())
    else:
        await message.answer("🏠 Asosiy menyu:", reply_markup=client_main_kb())
