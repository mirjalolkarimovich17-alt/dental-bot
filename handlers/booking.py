from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import datetime

from database.connection import AsyncSessionLocal
from database.crud import (
    get_user, get_all_doctors, get_doctor,
    get_booked_times, create_booking
)
from keyboards.all_kb import (
    doctors_kb, days_kb, times_kb, services_kb,
    confirm_booking_kb, skip_note_kb, client_main_kb, booking_action_kb
)
from states.booking_states import BookingStates
from config import SERVICES, config

router = Router()


@router.message(F.text == "📅 Navbat olish")
async def start_booking(message: Message, state: FSMContext):
    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0
    async with AsyncSessionLocal() as session:
        # BUG FIX: get_user telegram_id bilan chaqiriladi, user.id emas
        user = await get_user(session, user_id)
        if not user:
            await message.answer("Avval /start ni bosing.")
            return
        doctors = await get_all_doctors(session)

    if not doctors:
        await message.answer(
            "📋 <b>Navbat olish</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            f"😔 Kechirasiz, hozircha shifokorlar mavjud emas.\n\n"
            f"📞 Yordam uchun: {config.clinic_phone}",  # BUG FIX: f-string
            parse_mode="HTML"
        )
        return

    await state.update_data(user_id=user.id)
    await message.answer(
        "👨‍⚕️ <b>Shifokorni tanlang</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        "🏆 Eng tajribali mutaxassislarimiz siz uchun tayyor!\n"
        "Qulay shifokorni tanlang — navbat bir daqiqada rasmiylashadi.",
        reply_markup=doctors_kb(doctors)
    )
    await state.set_state(BookingStates.choosing_doctor)


@router.callback_query(F.data.startswith("doctor:"))
async def choose_doctor(callback: CallbackQuery, state: FSMContext):
    doctor_id = int(callback.data.split(":")[1])
    await state.update_data(doctor_id=doctor_id)
    await callback.message.edit_text(
        "📅 <b>Qaysi kuni kelasiz?</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        "⏰ Keyingi 14 kun ichida o'zingizga qulay sanani tanlang:",
        reply_markup=days_kb(doctor_id)
    )
    await callback.answer()
    await state.set_state(BookingStates.choosing_day)


@router.callback_query(F.data == "back_to_doctors")
async def back_to_doctors(callback: CallbackQuery, state: FSMContext):
    async with AsyncSessionLocal() as session:
        doctors = await get_all_doctors(session)
    await callback.message.edit_text(
        "👨‍⚕️ <b>Shifokorni tanlang</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        "🏆 Har bir shifokorimiz yuqori malakali mutaxassis:",
        reply_markup=doctors_kb(doctors)
    )
    await callback.answer()
    await state.set_state(BookingStates.choosing_doctor)


@router.callback_query(F.data == "back_to_time")
async def back_to_time(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    doctor_id = data.get("doctor_id")
    day_str = data.get("booking_date")
    if doctor_id and day_str:
        async with AsyncSessionLocal() as session:
            try:
                booked = await get_booked_times(session, doctor_id, datetime.date.fromisoformat(day_str))
            except (ValueError, TypeError):
                booked = []
        await callback.message.edit_text(
            "⏰ <b>Vaqtni tanlang</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "🟢 Bo'sh  |  🔴 Band\n\n"
            "O'zingizga eng qulay vaqtni belgilang:",
            reply_markup=times_kb(doctor_id, day_str, booked)
        )
        await callback.answer()
        await state.set_state(BookingStates.choosing_time)
    else:
        await callback.message.edit_text("Qayta boshlash uchun /start bosing.")
        await callback.answer()
        await state.clear()


@router.callback_query(F.data.startswith("day:"))
async def choose_day(callback: CallbackQuery, state: FSMContext):
    _, doctor_id, day_str = callback.data.split(":")
    doctor_id = int(doctor_id)
    booking_date = datetime.date.fromisoformat(day_str)

    async with AsyncSessionLocal() as session:
        booked = await get_booked_times(session, doctor_id, booking_date)

    await state.update_data(doctor_id=doctor_id, booking_date=day_str)
    await callback.message.edit_text(
        f"⏰ <b>{booking_date.strftime('%d.%m.%Y')} — vaqtni tanlang</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        "🟢 Bo'sh  |  🔴 Band",
        reply_markup=times_kb(doctor_id, day_str, booked)
    )
    await callback.answer()
    await state.set_state(BookingStates.choosing_time)


@router.callback_query(F.data.startswith("change_doctor:"))
async def back_from_time(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    doctor_id = data.get("doctor_id")
    if doctor_id:
        await callback.message.edit_text(
            "📅 <b>Kunni tanlang</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "Keyingi 14 kun ichidan qulay sanani belgilang:",
            reply_markup=days_kb(doctor_id)
        )
        await callback.answer()
        await state.set_state(BookingStates.choosing_day)
    else:
        await callback.message.edit_text("Qayta boshlash uchun /start bosing.")
        await callback.answer()
        await state.clear()


@router.callback_query(F.data == "booked")
async def slot_booked(callback: CallbackQuery):
    await callback.answer("⛔ Bu vaqt band! Iltimos, boshqa vaqtni tanlang.", show_alert=True)


@router.callback_query(F.data.startswith("time:"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    # format: time:doctor_id:2025-01-01:09:00
    parts = callback.data.split(":")
    time_str = parts[3] + ":" + parts[4]
    await state.update_data(booking_time=time_str)
    await callback.message.edit_text(
        "🦷 <b>Xizmat turini tanlang</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        "Qaysi muammo bilan kelmoqchisiz?",
        reply_markup=services_kb()
    )
    await callback.answer()
    await state.set_state(BookingStates.choosing_service)


@router.callback_query(F.data.startswith("service:"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[1])
    service = SERVICES[idx]
    await state.update_data(service=service)
    await callback.message.edit_text(
        "📝 <b>Qo'shimcha izoh</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        "Shifokorga aytmoqchi bo'lgan narsangiz bormi?\n"
        "<i>(masalan: og'riq qaysi tomonda, qancha vaqtdan beri)</i>\n\n"
        "Izoh qoldirsangiz, shifokor sizga yanada yaxshi tayyorlanadi! 💪",
        parse_mode="HTML",
        reply_markup=skip_note_kb()
    )
    await callback.answer()
    await state.set_state(BookingStates.writing_note)


@router.callback_query(F.data == "skip_note")
async def skip_note(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.update_data(note=None)
    data = await state.get_data()

    required_fields = ["booking_date", "booking_time", "doctor_id", "service", "user_id"]
    missing_fields = [f for f in required_fields if not data.get(f)]

    if missing_fields:
        await callback.answer("Xatolik: ma'lumotlar yo'q. Qaytadan boshlang.", show_alert=True)
        await state.clear()
        return

    booking_date = datetime.date.fromisoformat(data["booking_date"])
    h, m = data["booking_time"].split(":")
    booking_time = datetime.time(int(h), int(m))

    async with AsyncSessionLocal() as session:
        booking = await create_booking(
            session,
            user_id=data["user_id"],
            doctor_id=data["doctor_id"],
            booking_date=booking_date,
            booking_time=booking_time,
            service=data["service"],
            note=data.get("note")
        )
        doctor = await get_doctor(session, data["doctor_id"])
        user = await get_user(session, data["user_id"])  # BUG: user_id DB id, lekin get_user telegram_id oladi
        # get_user_by_id kerak - hozir doctor.full_name dan foydalaniladi, user uchun alohida query
        from database.crud import get_user_by_id
        user = await get_user_by_id(session, data["user_id"])

    await callback.answer("✅ Navbat olindi!")
    await callback.message.answer(
        f"🎉 <b>Navbat muvaffaqiyatli rasmiylashdi!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Navbat raqami: <b>#{booking.id}</b>\n"
        f"👨‍⚕️ Shifokor: <b>{doctor.full_name}</b>\n"
        f"📅 Sana: <b>{booking_date.strftime('%d.%m.%Y')}</b>\n"
        f"⏰ Vaqt: <b>{data['booking_time']}</b>\n"
        f"🦷 Xizmat: <b>{data['service']}</b>\n\n"
        f"⚡ Eslatma: belgilangan vaqtdan 10 daqiqa oldin kelishingizni so'raymiz!\n"
        f"📞 Savol bo'lsa: {doctor.phone or config.clinic_phone}",
        parse_mode="HTML",
        reply_markup=client_main_kb()
    )

    if doctor.telegram_id:
        try:
            await bot.send_message(
                doctor.telegram_id,
                f"🔔 <b>Yangi navbat keldi!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 Mijoz: {callback.from_user.full_name}\n"
                f"📅 {booking_date.strftime('%d.%m.%Y')} ⏰ {data['booking_time']}\n"
                f"🦷 Xizmat: {data['service']}\n"
                f"📝 Izoh: {data.get('note', '—')}",
                parse_mode="HTML",
                reply_markup=booking_action_kb(booking.id)
            )
        except Exception:
            pass

    for admin_id in config.admin_ids:
        try:
            if doctor.telegram_id:
                admin_text = (
                    f"📋 <b>Yangi navbat #{booking.id}</b>\n"
                    f"👨‍⚕️ Shifokor: {doctor.full_name}\n"
                    f"👤 Mijoz: {callback.from_user.full_name}\n"
                    f"📅 {booking_date.strftime('%d.%m.%Y')} ⏰ {data['booking_time']}\n"
                    f"🦷 Xizmat: {data['service']}"
                )
            else:
                admin_text = (
                    f"⚠️ <b>Yangi navbat (shifokor Telegram bog'lamagan!)</b>\n━━━━━━━━━━━━━━━━━━\n\n"
                    f"👨‍⚕️ Shifokor: {doctor.full_name}\n"
                    f"👤 Mijoz: {callback.from_user.full_name}\n"
                    f"📞 {user.phone if user else '—'}\n"
                    f"📅 {booking_date.strftime('%d.%m.%Y')} ⏰ {data['booking_time']}\n"
                    f"🦷 Xizmat: {data['service']}\n"
                    f"📝 Izoh: {data.get('note', '—')}\n\n"
                    f"Navbat raqami: #{booking.id}"
                )
            await bot.send_message(
                admin_id,
                admin_text,
                parse_mode="HTML",
                reply_markup=booking_action_kb(booking.id)
            )
        except Exception:
            pass

    await state.clear()


@router.message(BookingStates.writing_note)
async def got_note(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(note=message.text.strip())
    data = await state.get_data()

    required_fields = ["booking_date", "booking_time", "doctor_id", "service", "user_id"]
    missing_fields = [f for f in required_fields if not data.get(f)]

    if missing_fields:
        await message.answer(f"Xatolik: quyidagi ma'lumotlar yo'q: {', '.join(missing_fields)}. Iltimos, qaytadan boshlashingiz mumkin.")
        await state.clear()
        return

    booking_date = datetime.date.fromisoformat(data["booking_date"])
    h, m = data["booking_time"].split(":")
    booking_time = datetime.time(int(h), int(m))

    async with AsyncSessionLocal() as session:
        booking = await create_booking(
            session,
            user_id=data["user_id"],
            doctor_id=data["doctor_id"],
            booking_date=booking_date,
            booking_time=booking_time,
            service=data["service"],
            note=data.get("note")
        )
        doctor = await get_doctor(session, data["doctor_id"])
        from database.crud import get_user_by_id
        user = await get_user_by_id(session, data["user_id"])

    await state.clear()

    await message.answer(
        f"🎉 <b>Navbat muvaffaqiyatli rasmiylashdi!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Navbat raqami: <b>#{booking.id}</b>\n"
        f"👨‍⚕️ Shifokor: <b>{doctor.full_name}</b>\n"
        f"📅 Sana: <b>{booking_date.strftime('%d.%m.%Y')}</b>\n"
        f"⏰ Vaqt: <b>{data['booking_time']}</b>\n"
        f"🦷 Xizmat: <b>{data['service']}</b>\n"
        f"📝 Izoh: {data.get('note', '—')}\n\n"
        f"⚡ Eslatma: belgilangan vaqtdan 10 daqiqa oldin kelishingizni so'raymiz!\n"
        f"📞 Savol bo'lsa: {doctor.phone or config.clinic_phone}",
        parse_mode="HTML",
        reply_markup=client_main_kb()
    )

    if doctor.telegram_id:
        try:
            await bot.send_message(
                doctor.telegram_id,
                f"🔔 <b>Yangi navbat keldi!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 Mijoz: {message.from_user.full_name}\n"
                f"📅 {booking_date.strftime('%d.%m.%Y')} ⏰ {data['booking_time']}\n"
                f"🦷 Xizmat: {data['service']}\n"
                f"📝 Izoh: {data.get('note', '—')}",
                parse_mode="HTML",
                reply_markup=booking_action_kb(booking.id)
            )
        except Exception:
            pass

    for admin_id in config.admin_ids:
        try:
            if doctor.telegram_id:
                admin_text = (
                    f"📋 <b>Yangi navbat #{booking.id}</b>\n"
                    f"👨‍⚕️ Shifokor: {doctor.full_name}\n"
                    f"👤 Mijoz: {message.from_user.full_name}\n"
                    f"📅 {booking_date.strftime('%d.%m.%Y')} ⏰ {data['booking_time']}\n"
                    f"🦷 Xizmat: {data['service']}\n"
                    f"📝 Izoh: {data.get('note', '—')}"
                )
            else:
                admin_text = (
                    f"⚠️ <b>Yangi navbat (shifokor Telegram bog'lamagan!)</b>\n━━━━━━━━━━━━━━━━━━\n\n"
                    f"👨‍⚕️ Shifokor: {doctor.full_name}\n"
                    f"👤 Mijoz: {message.from_user.full_name}\n"
                    f"📞 {user.phone if user else '—'}\n"
                    f"📅 {booking_date.strftime('%d.%m.%Y')} ⏰ {data['booking_time']}\n"
                    f"🦷 Xizmat: {data['service']}\n"
                    f"📝 Izoh: {data.get('note', '—')}\n\n"
                    f"Navbat raqami: #{booking.id}"
                )
            await bot.send_message(
                admin_id,
                admin_text,
                parse_mode="HTML",
                reply_markup=booking_action_kb(booking.id)
            )
        except Exception:
            pass


@router.callback_query(F.data == "confirm_booking")
async def confirm_booking_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    required_fields = ["booking_date", "booking_time", "doctor_id", "service", "user_id"]
    missing_fields = [f for f in required_fields if not data.get(f)]

    if missing_fields:
        await callback.answer("Xatolik: ma'lumotlar yo'q. Qaytadan boshlang.", show_alert=True)
        await state.clear()
        return

    booking_date = datetime.date.fromisoformat(data["booking_date"])
    h, m = data["booking_time"].split(":")
    booking_time = datetime.time(int(h), int(m))

    async with AsyncSessionLocal() as session:
        booking = await create_booking(
            session,
            user_id=data["user_id"],
            doctor_id=data["doctor_id"],
            booking_date=booking_date,
            booking_time=booking_time,
            service=data["service"],
            note=data.get("note")
        )
        doctor = await get_doctor(session, data["doctor_id"])
        from database.crud import get_user_by_id
        user = await get_user_by_id(session, data["user_id"])

    await state.clear()
    await callback.answer("✅ Navbat olindi!")

    await callback.message.edit_text(
        f"🎉 <b>Navbat muvaffaqiyatli rasmiylashdi!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Navbat raqami: <b>#{booking.id}</b>\n"
        f"👨‍⚕️ Shifokor: <b>{doctor.full_name}</b>\n"
        f"📅 Sana: <b>{booking_date.strftime('%d.%m.%Y')}</b>\n"
        f"⏰ Vaqt: <b>{data['booking_time']}</b>\n\n"
        f"⚡ Eslatma: belgilangan vaqtdan 10 daqiqa oldin kelishingizni so'raymiz!\n"
        f"📞 Savol bo'lsa: {doctor.phone or config.clinic_phone}",
        parse_mode="HTML",
        reply_markup=client_main_kb()
    )

    if doctor.telegram_id:
        try:
            await bot.send_message(
                doctor.telegram_id,
                f"🔔 <b>Yangi navbat keldi!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 Mijoz: {callback.from_user.full_name}\n"
                f"📅 {booking_date.strftime('%d.%m.%Y')} ⏰ {data['booking_time']}\n"
                f"🦷 Xizmat: {data['service']}\n"
                f"📝 Izoh: {data.get('note', '—')}",
                parse_mode="HTML",
                reply_markup=booking_action_kb(booking.id)
            )
        except Exception:
            pass

    for admin_id in config.admin_ids:
        try:
            if doctor.telegram_id:
                admin_text = (
                    f"📋 <b>Yangi navbat #{booking.id}</b>\n"
                    f"👨‍⚕️ Shifokor: {doctor.full_name}\n"
                    f"👤 Mijoz: {callback.from_user.full_name}\n"
                    f"📅 {booking_date.strftime('%d.%m.%Y')} ⏰ {data['booking_time']}\n"
                    f"🦷 Xizmat: {data['service']}"
                )
            else:
                admin_text = (
                    f"⚠️ <b>Yangi navbat (shifokor Telegram bog'lamagan!)</b>\n━━━━━━━━━━━━━━━━━━\n\n"
                    f"👨‍⚕️ Shifokor: {doctor.full_name}\n"
                    f"👤 Mijoz: {callback.from_user.full_name}\n"
                    f"📞 {user.phone if user else '—'}\n"
                    f"📅 {booking_date.strftime('%d.%m.%Y')} ⏰ {data['booking_time']}\n"
                    f"🦷 Xizmat: {data['service']}\n"
                    f"📝 Izoh: {data.get('note', '—')}\n\n"
                    f"Navbat raqami: #{booking.id}"
                )
            await bot.send_message(
                admin_id,
                admin_text,
                parse_mode="HTML",
                reply_markup=booking_action_kb(booking.id)
            )
        except Exception:
            pass


@router.callback_query(F.data == "cancel_booking")
async def cancel_booking_flow(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "❌ <b>Navbat olish bekor qilindi.</b>\n\n"
        "Istalgan vaqtda qaytib kelishingiz mumkin! 😊",
        parse_mode="HTML"
    )
    await callback.message.answer("🏠 Asosiy menyu:", reply_markup=client_main_kb())
