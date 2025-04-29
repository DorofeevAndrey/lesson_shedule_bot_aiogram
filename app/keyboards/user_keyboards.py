import calendar
from datetime import date, datetime, timedelta

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func

from config import ADMIN_ID
from database import get_db
from models import TimeSlot, User


def get_user_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Записаться", callback_data="sign_up")
    builder.button(text="🗓️ Мои занятия", callback_data="my_lessons")
    builder.button(text="ℹ️ О нас", callback_data="about_us")
    builder.adjust(1)
    return builder.as_markup()


def get_user_calendar_keyboard(
    year: int = None, month: int = None
) -> InlineKeyboardMarkup:
    db = next(get_db())
    now = datetime.now()
    min_date = now.date()
    max_date = (now + timedelta(days=365)).date()
    admin = db.query(User).filter(User.telegram_id == ADMIN_ID).first()

    if not admin:
        db.close()
        raise ValueError("Администратор с таким Telegram ID не найден.")

    # Получаем все уникальные даты, на которые есть свободные слоты
    slots_dates = (
        db.query(func.date(TimeSlot.start_time))
        .filter(
            TimeSlot.start_time >= min_date,
            TimeSlot.start_time <= max_date,
            TimeSlot.admin_id == admin.id,
            TimeSlot.is_booked == False,
            TimeSlot.student_id == None,
        )
        .all()
    )
    db.close()

    available_dates = set(d[0] for d in slots_dates)

    # Если год и месяц не переданы - берем текущие
    if year is None or month is None:
        year = now.year
        month = now.month

    month_cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    header = f"{month_name} {year}"

    keyboard = []
    keyboard.append([InlineKeyboardButton(text=header, callback_data="ignore")])

    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.append(
        [InlineKeyboardButton(text=day, callback_data="ignore") for day in week_days]
    )

    for week in month_cal:
        week_buttons = []
        for day in week:
            if day == 0:
                week_buttons.append(
                    InlineKeyboardButton(text=" ", callback_data="ignore")
                )
            else:
                current_date = date(year, month, day)
                if current_date in available_dates:
                    week_buttons.append(
                        InlineKeyboardButton(
                            text=str(day),
                            callback_data=f"select_slot_date:{current_date}",
                        )
                    )
                else:
                    week_buttons.append(
                        InlineKeyboardButton(text=" ", callback_data="ignore")
                    )
        keyboard.append(week_buttons)

    # Определяем наличие предыдущего и следующего месяца со слотами
    available_months = set((d.year, d.month) for d in available_dates)

    prev_month = (month - 1) or 12
    prev_year = year if month != 1 else year - 1

    next_month = (month + 1) if month != 12 else 1
    next_year = year if month != 12 else year + 1

    has_prev = (prev_year, prev_month) in available_months
    has_next = (next_year, next_month) in available_months

    navigation_buttons = []
    if has_prev:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="◀️", callback_data=f"view_calendar:{prev_year}-{prev_month}"
            )
        )
    navigation_buttons.append(InlineKeyboardButton(text="📅", callback_data="ignore"))
    if has_next:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="▶️", callback_data=f"view_calendar:{next_year}-{next_month}"
            )
        )

    keyboard.append(navigation_buttons)

    # Кнопка назад
    keyboard.append(
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_menu")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_slots_time_user_keyboard(slots: list[TimeSlot]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for slot in slots:
        start_time = slot.start_time.strftime("%d-%m-%Y %H:%M")
        end_time = slot.end_time.strftime("%H:%M")
        builder.button(
            text=f"{start_time} - {end_time}", callback_data=f"select_slot:{slot.id}"
        )

    builder.button(text="↩️ Назад", callback_data="sign_up")

    builder.adjust(1)  # например 2 кнопки в ряд

    return builder.as_markup()


def get_all_user_lesson_keyboard(lessons):
    builder = InlineKeyboardBuilder()

    for lesson in lessons:
        start_str = lesson.start_time.strftime("%d-%m-%Y %H:%M")
        end_str = lesson.end_time.strftime("%H:%M")
        builder.button(
            text=f"{start_str} - {end_str}",
            callback_data=f"lesson_info:{lesson.id}",  # Можно потом сделать обработчик подробнее по занятию
        )

    builder.button(text="↩️ Назад", callback_data="back_to_menu")
    builder.adjust(1)  # 1 кнопка в ряд

    return builder.as_markup()


def get_user_lesson_info_keyboard(lesson_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="❌ Отменить запись", callback_data=f"cancel_lesson:{lesson_id}"
    )
    builder.button(text="↩️ Назад", callback_data="my_lessons")
    builder.adjust(1)
    return builder.as_markup()


def get_back_to_user_signup_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Записаться на занятие", callback_data="sign_up")
    builder.button(text="↩️ Назад", callback_data="back_to_menu")  # если хочешь
    builder.adjust(1)
    return builder.as_markup()
