from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean,
    DateTime, Text, Date, Time, ForeignKey, Enum
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class BookingStatus(enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    username = Column(String(100), nullable=True)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bookings = relationship("Booking", back_populates="user", foreign_keys="Booking.user_id")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    full_name = Column(String(100), nullable=False)
    specialty = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    photo_id = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bookings = relationship("Booking", back_populates="doctor")
    breaks = relationship("DoctorBreak", back_populates="doctor")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    booking_date = Column(Date, nullable=False)
    booking_time = Column(Time, nullable=False)
    service = Column(String(200), nullable=False)
    note = Column(Text, nullable=True)
    status = Column(Enum(BookingStatus), default=BookingStatus.pending)
    rating = Column(Integer, nullable=True)
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="bookings", foreign_keys=[user_id])
    doctor = relationship("Doctor", back_populates="bookings")


class DoctorBreak(Base):
    __tablename__ = "doctor_breaks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    break_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    reason = Column(String(200), nullable=True)

    doctor = relationship("Doctor", back_populates="breaks")
