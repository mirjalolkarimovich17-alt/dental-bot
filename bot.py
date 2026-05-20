print(">>> [0] Importlar boshlanmoqda...")
import asyncio
import logging
from datetime import timezone, timedelta

print(">>> [0.1] aiogram import qilinmoqda...")
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

print(">>> [0.2] config import qilinmoqda...")
from config import config
print(">>> [0.3] database.connection import qilinmoqda...")
from database.connection import init_db
print(">>> [0.4] handlers import qilinmoqda...")
from handlers import auth, client, booking, doctor, admin
print(">>> [0.5] services.scheduler import qilinmoqda...")
from services.scheduler import setup_scheduler, db_available
print(">>> [0.6] Barcha importlar tugadi!")

# Silence excessive logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("aiogram").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def main():
    print(">>> [1] Bot boshlanmoqda...")
    tz = timezone(timedelta(hours=5))  # Asia/Tashkent
    print(">>> [2] Bot obyektini yaratmoqda...")
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    print(">>> [3] Dispatcher yaratmoqda...")
    dp = Dispatcher(storage=MemoryStorage())

    # Tartib muhim: admin eng oxirida
    print(">>> [4] Routerlarni qo'shmoqda...")
    dp.include_router(auth.router)
    dp.include_router(booking.router)
    dp.include_router(doctor.router)
    dp.include_router(client.router)
    dp.include_router(admin.router)

    print(">>> [5] Database init qilmoqda...")
    logger.info("Ma'lumotlar bazasi ulanmoqda...")
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Database init failed: {e}")
        import services.scheduler
        services.scheduler.db_available = False
        logger.warning("Bot ishga tushdi AMMO database muammolari bor!")

    print(">>> [6] Scheduler sozlamoqda...")
    logger.info("Bot ishga tushmoqda...")

    setup_scheduler(bot)

    print(">>> [7] Polling boshlanmoqda (Telegramga ulanmoqda)...")
    logger.info("Bot ishga tushmoqda...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        print(">>> Bot to'xtadi, session yopilmoqda...")
        await bot.session.close()


if __name__ == "__main__":
    print(">>> Bot ishga tushishga tayyor...")
    asyncio.run(main())
