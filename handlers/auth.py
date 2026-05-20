from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart

from database.connection import AsyncSessionLocal
from database.crud import get_user, create_user, get_doctor_by_telegram
from keyboards.all_kb import phone_kb, client_main_kb, doctor_main_kb
from states.booking_states import AuthStates
from config import config

router = Router()


async def send_main_menu(message: Message, telegram_id):
    try:
        telegram_id = int(telegram_id)
    except (ValueError, TypeError):
        telegram_id = 0
    async with AsyncSessionLocal() as session:
        doctor = await get_doctor_by_telegram(session, telegram_id)
        if telegram_id in config.admin_ids:
            from keyboards.all_kb import admin_main_kb
            await message.answer(
                "🔐 <b>Admin panel</b>\n\nSizning maxsus bo'limingizga xush kelibsiz!",
                reply_markup=admin_main_kb()
            )
        elif doctor:
            await message.answer(
                f"👨‍⚕️ <b>Dr. {doctor.full_name}</b>\n\nSizga qayta xush kelibsiz! Boshqaruv paneli tayyor.",
                reply_markup=doctor_main_kb()
            )
        else:
            user = await get_user(session, telegram_id)
            await message.answer(
                f"👋 <b>Assalomu alaykum, {user.full_name}!</b>\n\n"
                "🏥 Klinika hizmatlaridan foydalanish uchun quyidagi bo'limlardan birini tanlang:",
                reply_markup=client_main_kb()
            )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0
    async with AsyncSessionLocal() as session:
        user = await get_user(session, user_id)

    if user:
        await send_main_menu(message, user_id)
        return

    await message.answer(
        f"🏥 <b>{config.clinic_name}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        "💎 <b>Xush kelibsiz!</b>\n\n"
        "Sog'lom tish — sog'lom hayot! Bizning zamonaviy klinikamizda\n"
        "eng ilg'or texnologiyalar va tajribali shifokorlar siz uchun tayyor.\n\n"
        "🔐 To'liq foydalanish uchun bir marta ro'yxatdan o'ting:\n\n"
        "📱 <b>Telefon raqamingizni ulashing:</b>",
        parse_mode="HTML",
        reply_markup=phone_kb()
    )
    await state.set_state(AuthStates.waiting_phone)


@router.message(AuthStates.waiting_phone, F.contact)
async def got_phone(message: Message, state: FSMContext):
    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0
    await state.update_data(user_id=user_id)
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await message.answer(
        "👤 <b>Ajoyib! Endi ismingizni kiriting:</b>\n\n"
        "Familiya va ismingizni to'liq yozing\n"
        "<i>(masalan: Aliyev Jasur)</i>",
        parse_mode="HTML",
        reply_markup=None
    )
    await state.set_state(AuthStates.waiting_name)


@router.message(AuthStates.waiting_phone)
async def phone_not_shared(message: Message):
    await message.answer(
        "📱 <b>Telefon raqamingizni ulashing!</b>\n\n"
        "Bu faqat bir marta so'raladi va xavfsiz saqlanadi 🔒\n\n"
        "Quyidagi tugmani bosing 👇",
        reply_markup=phone_kb()
    )


@router.message(AuthStates.waiting_name, F.text)
async def got_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Iltimos, to'liq ismingizni kiriting.")
        return

    data = await state.get_data()
    phone = data.get("phone")
    if not phone:
        await message.answer("Xatolik yuz berdi. Iltimos, qayta /start bosing.")
        await state.clear()
        return

    try:
        user_id = int(message.from_user.id)
    except (ValueError, TypeError):
        user_id = 0

    async with AsyncSessionLocal() as session:
        await create_user(
            session,
            telegram_id=user_id,
            full_name=name,
            phone=phone,
            username=message.from_user.username
        )

    await state.clear()
    await message.answer(
        f"🎉 <b>Tabriklaymiz, {name}!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Profilingiz muvaffaqiyatli yaratildi!\n"
        f"👤 Ism: <b>{name}</b>\n"
        f"📱 Tel: <b>{phone}</b>\n\n"
        f"🦷 Endi bizning barcha xizmatlarimizdan bemalol foydalanishingiz mumkin!\n"
        f"Sog'lom tishlar — chiroyli tabassum 😊",
        parse_mode="HTML",
        reply_markup=client_main_kb()
    )
