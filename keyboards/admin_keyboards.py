import calendar
from datetime import date, datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Добавить расписание", callback_data="add_schedule")
    builder.button(text="🗓️ Посмотреть расписание", callback_data="view_schedule")
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
                    date_str = f"{day:02d}-{month:02d}-{year}"
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


def get_admin_shedule_slots_keyboard(slots):
    # Создаем клавиатуру с кнопками для каждого слота
    builder = InlineKeyboardBuilder()

    for slot in slots:
        start = slot.start_time.strftime("%d-%m-%Y %H:%M")
        end = slot.end_time.strftime("%H:%M")
        if slot.student:
            if slot.is_booked:
                student_info = f"Забронировано"
            else:
                student_info = f"В ожидании"

        else:
            student_info = "Свободно"

        button_text = f"{start} - {end} | {student_info}"
        builder.button(
            text=button_text,
            callback_data=f"selected_slot:{slot.id}",  # Передаем id слота
        )

    # Кнопка "Назад"
    builder.button(text="↩️ Назад", callback_data="back_to_menu")

    builder.adjust(1)
    return builder.as_markup()


def get_admin_delete_selected_slot_keyboard(slot_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Удалить слот", callback_data=f"delete_slot:{slot_id}")
    builder.button(text="↩️ Назад", callback_data="view_schedule")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_cancel_selected_slot_keyboard(slot_id):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Отменить урок", callback_data=f"cansel_user_selected_slot:{slot_id}"
    )
    builder.button(text="↩️ Назад", callback_data="view_schedule")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_accept_or_reject_slot_keyboard(slot_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Принять", callback_data=f"is_booked_slot:{slot_id}")
    builder.button(text="Отклонить", callback_data=f"cancel_booked_slot:{slot_id}")
    builder.adjust(1)
    return builder.as_markup()
