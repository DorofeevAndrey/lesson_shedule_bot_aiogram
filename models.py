from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    # Связи
    created_slots = relationship(
        "TimeSlot", back_populates="admin", foreign_keys="TimeSlot.admin_id"
    )
    booked_slots = relationship(
        "TimeSlot", back_populates="student", foreign_keys="TimeSlot.student_id"
    )


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_booked = Column(Boolean, default=False)
    subject = Column(
        String, nullable=True
    )  # Тема/предмет (может быть пустым для свободных слотов)

    # Кто создал слот (админ/преподаватель)
    admin_id = Column(Integer, ForeignKey("users.id"))
    admin = relationship(
        "User", back_populates="created_slots", foreign_keys=[admin_id]
    )

    # Кто забронировал слот (студент)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    student = relationship(
        "User", back_populates="booked_slots", foreign_keys=[student_id]
    )
