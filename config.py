from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Config:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    admin_ids: List[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip() and x.strip().isdigit()
    ])
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))

    clinic_name: str = field(default_factory=lambda: os.getenv("CLINIC_NAME", "Dental Bot"))
    clinic_address: str = field(default_factory=lambda: os.getenv("CLINIC_ADDRESS", ""))
    clinic_phone: str = field(default_factory=lambda: os.getenv("CLINIC_PHONE", ""))
    clinic_lat: float = field(default_factory=lambda: float(os.getenv("CLINIC_LOCATION_LAT", "41.299496")))
    clinic_lon: float = field(default_factory=lambda: float(os.getenv("CLINIC_LOCATION_LON", "69.240073")))
    clinic_website: str = field(default_factory=lambda: os.getenv("CLINIC_WEBSITE", ""))
    clinic_about: str = field(default_factory=lambda: os.getenv("CLINIC_ABOUT", ""))


config = Config()

SERVICES = [
    "Tish tozalash (Professional)",
    "Plomba qo'yish",
    "Tish oqartirish",
    "Tish qoplama (Veneer)",
    "Implant qo'yish",
    "Bolalar stomatologiyasi",
    "Tish qo'yish (Protez)",
    "Boshqa (Izoh qoldiring)",
]

WEEK_DAYS = {
    "monday": "Dushanba",
    "tuesday": "Seshanba",
    "wednesday": "Chorshanba",
    "thursday": "Payshanba",
    "friday": "Juma",
    "saturday": "Shanba",
    "sunday": "Yakshanba",
}

# Klinika ish vaqti: 08:00 - 23:00
WORK_HOURS = [
    "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00",
    "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00", "23:00"
]