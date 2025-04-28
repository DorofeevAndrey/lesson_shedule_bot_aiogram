import calendar
from datetime import date, datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F, types
from sqlalchemy import func

from config import ADMIN_ID
from database import get_db
from models import TimeSlot, User

from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Добавить расписание", callback_data="add_schedule"
                ),
                InlineKeyboardButton(
                    text="🗓️ Посмотреть расписание", callback_data="view_schedule"
                ),
            ]
        ]
    )
    return keyboard


def get_user_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Записаться", callback_data="sign_up")],
            [InlineKeyboardButton(text="🗓️ Мои занятия", callback_data="my_lessons")],
            [InlineKeyboardButton(text="ℹ️ О нас", callback_data="about_us")],
        ]
    )
    return keyboard


def get_user_calendar_keyboard() -> InlineKeyboardMarkup:
    db = next(get_db())
    now = datetime.now()
    min_date = now.date()
    max_date = (now + timedelta(days=365)).date()
    admin = db.query(User).filter(User.telegram_id == ADMIN_ID).first()

    if not admin:
        db.close()
        raise ValueError("Администратор с таким Telegram ID не найден.")
    # Получаем все уникальные даты, на которые есть слоты
    slots_dates = (
        db.query(func.date(TimeSlot.start_time))
        .filter(
            TimeSlot.start_time >= min_date,
            TimeSlot.start_time <= max_date,
            TimeSlot.admin_id == admin.id,
            TimeSlot.is_booked == False,
        )
        .all()
    )
    db.close()

    # Превращаем в set для удобства поиска
    available_dates = set(d[0] for d in slots_dates)

    # Строим календарь для текущего месяца
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

    # Кнопка назад
    keyboard.append(
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_menu")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_slots_time_keyboard(slots: list[TimeSlot]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for slot in slots:
        time_text = slot.start_time.strftime("%H:%M")
        builder.button(text=time_text, callback_data=f"select_slot:{slot.id}")

    builder.button(text="↩️ Назад", callback_data="sign_up")

    builder.adjust(2)  # например 2 кнопки в ряд

    return builder.as_markup()


def get_all_user_lesson_keyboard(lessons):
    builder = InlineKeyboardBuilder()

    for lesson in lessons:
        start_str = lesson.start_time.strftime("%Y-%m-%d %H:%M")
        end_str = lesson.end_time.strftime("%H:%M")
        builder.button(
            text=f"{start_str} - {end_str}",
            callback_data=f"lesson_info:{lesson.id}",  # Можно потом сделать обработчик подробнее по занятию
        )

    builder.button(text="↩️ Назад", callback_data="back_to_menu")
    builder.adjust(1)  # 1 кнопка в ряд

    return builder.as_markup()


def get_lesson_info_keyboard(lesson_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="❌ Отменить запись", callback_data=f"cancel_lesson:{lesson_id}"
    )
    builder.button(text="↩️ Назад", callback_data="my_lessons")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_calendar_keyboard(
    year: int = None, month: int = None
) -> InlineKeyboardMarkup:
    """Генерация клавиатуры календаря: только с сегодняшнего дня и максимум на год вперёд"""
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    # Ограничения
    min_date = now.date()  # Сегодня
    max_date = (now + timedelta(days=365)).date()  # +1 год

    # Проверяем, что месяц в допустимом диапазоне
    selected_first_day = date(year, month, 1)
    if selected_first_day < min_date.replace(day=1):
        year = now.year
        month = now.month
    if selected_first_day > max_date.replace(day=1):
        year = max_date.year
        month = max_date.month

    # Генерируем календарь
    month_cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    header = f"{month_name} {year}"

    keyboard = []
    keyboard.append([InlineKeyboardButton(text=header, callback_data="ignore")])

    # Дни недели
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.append(
        [InlineKeyboardButton(text=day, callback_data="ignore") for day in week_days]
    )

    # Кнопки дней месяца
    for week in month_cal:
        week_buttons = []
        for day in week:
            if day == 0:
                week_buttons.append(
                    InlineKeyboardButton(text=" ", callback_data="ignore")
                )
            else:
                current_date = date(year, month, day)
                if min_date <= current_date <= max_date:
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    week_buttons.append(
                        InlineKeyboardButton(
                            text=str(day), callback_data=f"select_date:{date_str}"
                        )
                    )
                else:
                    week_buttons.append(
                        InlineKeyboardButton(text=" ", callback_data="ignore")
                    )
        keyboard.append(week_buttons)

    # Кнопки навигации (только вперёд, если не превышаем год)
    nav_buttons = []

    if date(year, month, 1) > min_date.replace(day=1):
        # Листать назад можно, но не до прошлого месяца сегодняшнего
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        if date(prev_year, prev_month, 1) >= min_date.replace(day=1):
            nav_buttons.append(
                InlineKeyboardButton(
                    text="◀️", callback_data=f"change_month:{prev_year}-{prev_month}"
                )
            )

    if date(year, month, 1) < max_date.replace(day=1):
        # Листать вперёд можно
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        if date(next_year, next_month, 1) <= max_date.replace(day=1):
            nav_buttons.append(
                InlineKeyboardButton(
                    text="▶️", callback_data=f"change_month:{next_year}-{next_month}"
                )
            )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопка возврата
    keyboard.append(
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_menu")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
