from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database.connection import AsyncSessionLocal
from database.crud import get_tomorrow_bookings, mark_reminder_sent, get_all_users
import logging
import asyncio

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
db_available = True


def setup_scheduler(bot):
    global db_available

    async def send_reminders():
        if not db_available:
            logger.warning("Database not available, skipping reminders")
            return
        try:
            async with AsyncSessionLocal() as session:
                bookings = await get_tomorrow_bookings(session)
                for b in bookings:
                    try:
                        await bot.send_message(
                            b.user.telegram_id,
                            f"🔔 <b>Navbat eslatmasi!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
                            f"⏰ Ertaga <b>{b.booking_date.strftime('%d.%m.%Y')}</b> kuni\n"
                            f"soat <b>{b.booking_time.strftime('%H:%M')}</b> da navbatingiz bor!\n\n"
                            f"👨‍⚕️ Shifokor: <b>Dr. {b.doctor.full_name}</b>\n"
                            f"🦷 Xizmat: <b>{b.service}</b>\n\n"
                            f"✅ Vaqtdan oldin kelishingizni so'raymiz!\n"
                            f"❌ Kelolmasangiz, iltimos oldindan xabar bering.",
                            parse_mode="HTML"
                        )
                        await mark_reminder_sent(session, b.id)
                    except Exception as e:
                        logger.error(f"Reminder send error: {e}")
        except Exception as e:
            logger.error(f"Daily reminders job error: {e}")

    async def evening_health_msg():
        if not db_available:
            logger.warning("Database not available, skipping health message")
            return
        try:
            import random
            messages = [
                "🦷 <b>Tishlaringiz sog'liqmi?</b>\n\nYiliga kamida 2 marta stomatolog tekshiruvi — katta muammolarning oldini oladi! Bugun navbat oling 👇",
                "😊 <b>Sog'lom tish — chiroyli tabassum!</b>\n\nO'z sog'lig'ingizga e'tibor bering. Tishlaringizni parvarish qiling — ular sizning tashabbusingizni boshqalarga ko'rsatadi!",
                "🪥 <b>Kuniga 2 marta tish tozalashni unutmang!</b>\n\nErtalab uyg'onib va kechasi uxlashdan oldin — bu oddiy odatlar hayotingizni yaxshilaydi!",
                "💧 <b>Ko'proq suv iching!</b>\n\nSuv tishlaringizni himoya qiladi va og'iz bo'shlig'ini tozalaydi. Sog'liq — bu har kuni qilinadigan kichik tanlovlar!",
                "⚡ <b>Og'riq boshlanishidan kuting!</b>\n\nProfilaktika davolashdan arzonroq va ogonoqsiz. Bugun navbat oling — ertaga sog'lom bo'ling!",
            ]
            msg = random.choice(messages)
            async with AsyncSessionLocal() as session:
                users = await get_all_users(session)
            sent_count = 0
            for user in users:
                if sent_count >= 50:
                    break
                try:
                    await bot.send_message(user.telegram_id, msg)
                    sent_count += 1
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Evening health msg job error: {e}")

    scheduler.add_job(
        send_reminders,
        CronTrigger(hour=10, minute=0),
        id="daily_reminders",
        replace_existing=True
    )
    scheduler.add_job(
        evening_health_msg,
        CronTrigger(hour=20, minute=0),
        id="evening_health_check",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler ishga tushdi")
