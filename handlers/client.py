from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.connection import AsyncSessionLocal
from database.crud import get_user, get_user_bookings, cancel_booking
from keyboards.all_kb import client_main_kb, my_bookings_kb
from config import config, SERVICES

router = Router()

STATUS_EMOJI = {
    "pending": "⏳ <i>Kutilmoqda</i>",
    "confirmed": "✅ <i>Tasdiqlangan</i>",
    "cancelled": "❌ <i>Bekor qilingan</i>",
    "completed": "🏁 <i>Yakunlangan</i>",
}


@router.message(F.text == "🏥 Xizmatlar")
async def show_services(message: Message):
    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0
    async with AsyncSessionLocal() as session:
        user = await get_user(session, user_id)
    if not user:
        await message.answer("Avval /start ni bosing.")
        return

    text = "🦷 <b>Bizning xizmatlar:</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for s in SERVICES:
        if s != "Boshqa (Izoh qoldiring)":
            text += f"✓ {s}\n"
    text += (
        "\n💡 <i>Har bir xizmatimizda zamonaviy uskunalar va\n"
        "yuqori malakali shifokorlar sizga xizmat qiladi!</i>\n\n"
        f"📞 <b>Batafsil ma'lumot uchun:</b> {config.clinic_phone}"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "📍 Manzil / Lokatsiya")
async def show_location(message: Message):
    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0
    async with AsyncSessionLocal() as session:
        user = await get_user(session, user_id)
    if not user:
        await message.answer("Avval /start ni bosing.")
        return

    await message.answer(
        f"📍 <b>Bizni osongina toping!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"🏥 <b>{config.clinic_name}</b>\n"
        f"📌 {config.clinic_address}\n\n"
        f"📞 <b>Telefon:</b> {config.clinic_phone}\n\n"
        f"🗺️ <i>Xaritada ko'rish uchun quyidagi joylashuvga bosing 👇</i>",
        parse_mode="HTML"
    )
    try:
        await message.bot.send_location(
            message.chat.id,
            latitude=config.clinic_lat,
            longitude=config.clinic_lon
        )
    except Exception:
        pass


@router.message(F.text == "ℹ️ Biz haqimizda")
async def show_about(message: Message):
    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0
    async with AsyncSessionLocal() as session:
        user = await get_user(session, user_id)
    if not user:
        await message.answer("Avval /start ni bosing.")
        return

    text = (
        f"🏥 <b>{config.clinic_name}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"<i>{config.clinic_about}</i>\n\n"
        f"🌟 <b>Nima uchun biz?</b>\n"
        f"✓ Tajribali va mehribon shifokorlar\n"
        f"✓ Zamonaviy asbob-uskunalar\n"
        f"✓ Qulay narxlar va chegirmalar\n"
        f"✓ Tez va aniq navbat tizimi\n\n"
        f"📞 <b>Telefon:</b> {config.clinic_phone}\n"
        f"📍 <b>Manzil:</b> {config.clinic_address}"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🌐 Web saytimiz")
async def show_website(message: Message):
    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0
    async with AsyncSessionLocal() as session:
        user = await get_user(session, user_id)
    if not user:
        await message.answer("Avval /start ni bosing.")
        return

    await message.answer(
        f"🌐 <b>Rasmiy veb-saytimiz</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"Barcha xizmatlar, narxlar va aksiyalar haqida to'liq ma'lumot:\n\n"
        f"<a href=\"{config.clinic_website}\">🔗 {config.clinic_website}</a>\n\n"
        f"<i>Sahifamizga tashrif buyuring — foydali ma'lumotlar siz uchun!</i>",
        parse_mode="HTML"
    )


@router.message(F.text == "📋 Mening navbatlarim")
async def my_bookings(message: Message):
    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0
    async with AsyncSessionLocal() as session:
        user = await get_user(session, user_id)
        if not user:
            await message.answer("Avval /start ni bosing.")
            return
        bookings = await get_user_bookings(session, user.id)

    if not bookings:
        await message.answer(
            "📋 <b>Mening navbatlarim</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "📭 Hozircha navbatlaringiz yo'q.\n\n"
            "💡 Sog'lig'ingizga e'tibor bering — bugun navbat oling!\n"
            "👇 <b>«Navbat olish»</b> tugmasini bosing.",
            parse_mode="HTML"
        )
        return

    text = "📋 <b>Sizning navbatlaringiz:</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    active = []
    for b in bookings[:10]:
        status = STATUS_EMOJI.get(b.status.value, b.status.value)
        doctor_name = b.doctor.full_name if b.doctor else "Noma'lum"
        text += (
            f"#{b.id} — <b>{doctor_name}</b>\n"
            f"📅 {b.booking_date.strftime('%d.%m.%Y')} ⏰ {b.booking_time.strftime('%H:%M')}\n"
            f"🦷 {b.service}\n"
            f"Holat: {status}\n\n"
        )
        if b.status.value in ("pending", "confirmed"):
            active.append(b)

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=my_bookings_kb(active) if active else None
    )


@router.callback_query(F.data.startswith("cancel:"))
async def cancel_my_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as session:
        await cancel_booking(session, booking_id)
    await callback.answer("✅ Navbat bekor qilindi!")
    await callback.message.edit_text(
        f"✅ <b>Navbat bekor qilindi</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"#{booking_id} raqamli navbatingiz bekor qilindi.\n\n"
        f"🔄 Yangi navbat olish uchun <b>«Navbat olish»</b> tugmasini bosing.",
        parse_mode="HTML"
    )
