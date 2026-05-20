from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.orm import selectinload
from database.models import User, Doctor, Booking, DoctorBreak, BookingStatus
from datetime import date, time, datetime, timedelta
from typing import Optional, List


# ─── USER ────────────────────────────────────────────────────────────────────

async def get_user(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, telegram_id: int, full_name: str,
                      phone: str, username: str = None) -> User:
    user = User(telegram_id=telegram_id, full_name=full_name,
                phone=phone, username=username)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_all_users(session: AsyncSession) -> List[User]:
    result = await session.execute(select(User).where(User.is_blocked == False))
    return result.scalars().all()


async def count_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(User.id)))
    return result.scalar()


# ─── DOCTOR ──────────────────────────────────────────────────────────────────

async def get_all_doctors(session: AsyncSession, active_only=True) -> List[Doctor]:
    q = select(Doctor)
    if active_only:
        q = q.where(Doctor.is_active == True)
    result = await session.execute(q)
    return result.scalars().all()


async def get_doctor(session: AsyncSession, doctor_id: int) -> Optional[Doctor]:
    result = await session.execute(select(Doctor).where(Doctor.id == doctor_id))
    return result.scalar_one_or_none()


async def get_doctor_by_telegram(session: AsyncSession, telegram_id: int) -> Optional[Doctor]:
    result = await session.execute(select(Doctor).where(Doctor.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def create_doctor(session: AsyncSession, full_name: str, specialty: str,
                        phone: str = None, telegram_id: int = None) -> Doctor:
    doctor = Doctor(full_name=full_name, specialty=specialty,
                    phone=phone, telegram_id=telegram_id)
    session.add(doctor)
    await session.commit()
    await session.refresh(doctor)
    return doctor


async def deactivate_doctor(session: AsyncSession, doctor_id: int):
    await session.execute(
        update(Doctor).where(Doctor.id == doctor_id).values(is_active=False)
    )
    await session.commit()


async def count_doctors(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(Doctor.id)).where(Doctor.is_active == True)
    )
    return result.scalar()


# ─── BOOKING ─────────────────────────────────────────────────────────────────

async def create_booking(session: AsyncSession, user_id: int, doctor_id: int,
                         booking_date: date, booking_time: time,
                         service: str, note: str = None) -> Booking:
    booking = Booking(user_id=user_id, doctor_id=doctor_id,
                      booking_date=booking_date, booking_time=booking_time,
                      service=service, note=note)
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


async def get_booked_times(session: AsyncSession, doctor_id: int,
                            booking_date: date) -> List[time]:
    # Band navbatlar
    result = await session.execute(
        select(Booking.booking_time).where(
            and_(
                Booking.doctor_id == doctor_id,
                Booking.booking_date == booking_date,
                Booking.status != BookingStatus.cancelled
            )
        )
    )
    booked = [r[0] for r in result.all()]

    # Tanaffus vaqtlari
    breaks = await get_doctor_breaks(session, doctor_id, booking_date)
    for brk in breaks:
        # Tanaffus orasidagi barcha 1 soatlik slotlarni qo'shish
        current = brk.start_time
        while current < brk.end_time:
            if current not in booked:
                booked.append(current)
            # 1 soat qo'shish
            current = (datetime.combine(date.today(), current) + timedelta(hours=1)).time()

    return booked


async def get_user_bookings(session: AsyncSession, user_id: int) -> List[Booking]:
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.doctor))
        .where(Booking.user_id == user_id)
        .order_by(Booking.booking_date.desc(), Booking.booking_time.desc())
    )
    return result.scalars().all()


async def get_doctor_bookings(session: AsyncSession, doctor_id: int,
                               booking_date: date = None) -> List[Booking]:
    q = (select(Booking)
         .options(selectinload(Booking.user))
         .where(Booking.doctor_id == doctor_id,
                Booking.status != BookingStatus.cancelled))
    if booking_date:
        q = q.where(Booking.booking_date == booking_date)
    q = q.order_by(Booking.booking_date, Booking.booking_time)
    result = await session.execute(q)
    return result.scalars().all()


async def get_all_bookings(session: AsyncSession) -> List[Booking]:
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.user), selectinload(Booking.doctor))
        .order_by(Booking.created_at.desc())
    )
    return result.scalars().all()


async def update_booking_status(session: AsyncSession, booking_id: int,
                                 status: BookingStatus):
    await session.execute(
        update(Booking).where(Booking.id == booking_id).values(status=status)
    )
    await session.commit()


async def cancel_booking(session: AsyncSession, booking_id: int):
    await update_booking_status(session, booking_id, BookingStatus.cancelled)


async def count_bookings(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(Booking.id)))
    return result.scalar()


async def count_today_bookings(session: AsyncSession) -> int:
    today = date.today()
    result = await session.execute(
        select(func.count(Booking.id)).where(
            and_(Booking.booking_date == today,
                 Booking.status != BookingStatus.cancelled)
        )
    )
    return result.scalar()


# ─── DOCTOR BREAK ────────────────────────────────────────────────────────────

async def add_doctor_break(session: AsyncSession, doctor_id: int, break_date: date,
                            start_time: time, end_time: time, reason: str = None):
    brk = DoctorBreak(doctor_id=doctor_id, break_date=break_date,
                      start_time=start_time, end_time=end_time, reason=reason)
    session.add(brk)
    await session.commit()


async def get_doctor_breaks(session: AsyncSession, doctor_id: int,
                             break_date: date) -> List[DoctorBreak]:
    result = await session.execute(
        select(DoctorBreak).where(
            and_(DoctorBreak.doctor_id == doctor_id,
                 DoctorBreak.break_date == break_date)
        )
    )
    return result.scalars().all()


async def remove_doctor_breaks(session: AsyncSession, doctor_id: int, break_date: date):
    await session.execute(
        delete(DoctorBreak).where(
            and_(DoctorBreak.doctor_id == doctor_id,
                 DoctorBreak.break_date == break_date)
        )
    )
    await session.commit()


# ─── REMINDERS ───────────────────────────────────────────────────────────────

async def get_tomorrow_bookings(session: AsyncSession) -> List[Booking]:
    from datetime import timedelta
    tomorrow = date.today() + timedelta(days=1)
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.user), selectinload(Booking.doctor))
        .where(
            and_(Booking.booking_date == tomorrow,
                 Booking.status == BookingStatus.confirmed,
                 Booking.reminder_sent == False)
        )
    )
    return result.scalars().all()


async def mark_reminder_sent(session: AsyncSession, booking_id: int):
    await session.execute(
        update(Booking).where(Booking.id == booking_id).values(reminder_sent=True)
    )
    await session.commit()
