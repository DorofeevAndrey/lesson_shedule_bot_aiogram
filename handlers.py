from datetime import datetime
import re
from aiogram import F, types
from sqlalchemy import func
from config import ADMIN_ID
from database import get_db
from keyboards import (
    build_slots_time_keyboard,
    get_admin_calendar_keyboard,
    get_admin_keyboard,
    get_all_user_lesson_keyboard,
    get_back_to_signup_keyboard,
    get_lesson_info_keyboard,
    get_user_calendar_keyboard,
    get_user_keyboard,
)
from bot_instance import dp
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from models import TimeSlot, User
from sqlalchemy.orm import joinedload


# --- States ---
class ScheduleStates(StatesGroup):
    waiting_for_time = State()


# --- USER ---


@dp.callback_query(F.data == "sign_up")
async def add_schedule_handler(callback: types.CallbackQuery):
    await callback.answer()

    await callback.message.edit_text(
        "Выбери свободный день:",
        reply_markup=get_user_calendar_keyboard(),
    )


@dp.callback_query(F.data.startswith("view_calendar:"))
async def process_calendar_navigation(callback: types.CallbackQuery):
    await callback.answer()

    _, date_str = callback.data.split(":")
    year, month = map(int, date_str.split("-"))

    await callback.message.edit_text(
        "Выбери свободный день:",
        reply_markup=get_user_calendar_keyboard(year, month),
    )


@dp.callback_query(F.data.startswith("select_slot_date:"))
async def select_slot_date_handler(callback: types.CallbackQuery):
    await callback.answer()

    date_str = callback.data.split(":")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    db = next(get_db())
    try:

        admin = db.query(User).filter(User.telegram_id == ADMIN_ID).first()

        if not admin:
            await callback.message.answer("Администратор не найден.")
            return

        # Достаем все слоты на выбранную дату у этого админа
        slots = (
            db.query(TimeSlot)
            .filter(
                func.date(TimeSlot.start_time) == selected_date,
                TimeSlot.admin_id == admin.id,
                TimeSlot.is_booked == False,  # Только свободные слоты
            )
            .order_by(TimeSlot.start_time)
            .all()
        )

        if not slots:
            await callback.message.answer("На эту дату нет свободных слотов.")
            return

        # Генерируем клавиатуру времени
        keyboard = build_slots_time_keyboard(slots)

        await callback.message.edit_text(
            "Выбери время:",
            reply_markup=keyboard,
        )
    finally:
        db.close()


@dp.callback_query(F.data.startswith("select_slot:"))
async def select_slot_handler(callback: types.CallbackQuery):
    await callback.answer()

    # Извлекаем ID выбранного слота
    slot_id = int(callback.data.split(":")[1])

    db = next(get_db())
    try:
        # Ищем слот по ID
        slot = db.query(TimeSlot).filter(TimeSlot.id == slot_id).first()

        if not slot:
            await callback.message.answer("Ошибка: слот не найден.")
            return

        # Проверяем, если слот уже забронирован
        if slot.is_booked:
            await callback.message.answer("Этот слот уже забронирован.")
            return

        # Ищем пользователя, который нажал на слот
        student = (
            db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        )

        if not student:
            await callback.message.answer(
                "Ошибка: пользователь не найден в базе данных."
            )
            return

        # Записываем пользователя в поле student_id
        slot.student_id = student.id
        slot.is_booked = True  # Слот теперь забронирован
        db.commit()

        # Отправляем подтверждение
        await callback.message.edit_text(
            f"Вы успешно записались на слот {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}."
        )

    finally:
        db.close()

    # Возвращаемся к меню
    await callback.message.edit_reply_markup(reply_markup=get_user_calendar_keyboard())


@dp.callback_query(F.data == "my_lessons")
async def my_lessons_handler(callback: types.CallbackQuery):
    await callback.answer()

    db = next(get_db())
    try:
        # Ищем пользователя по telegram_id
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

        if not user:
            await callback.message.answer(
                "Ошибка: пользователь не найден в базе данных."
            )
            return

        # Получаем все занятия пользователя
        lessons = (
            db.query(TimeSlot)
            .filter(TimeSlot.student_id == user.id)
            .order_by(TimeSlot.start_time)
            .all()
        )

        if not lessons:
            await callback.message.edit_text(
                "У вас пока нет записей на занятия 📚",
                reply_markup=get_back_to_signup_keyboard(),
            )
            return

        # Строим клавиатуру занятий
        keyboard = get_all_user_lesson_keyboard(lessons)

        await callback.message.edit_text("Ваши занятия:", reply_markup=keyboard)

    finally:
        db.close()


@dp.callback_query(F.data.startswith("lesson_info:"))
async def lesson_info_handler(callback: types.CallbackQuery):
    await callback.answer()

    lesson_id = int(callback.data.split(":")[1])

    db = next(get_db())
    try:
        lesson = (
            db.query(TimeSlot)
            .options(joinedload(TimeSlot.admin))
            .filter(TimeSlot.id == lesson_id)
            .first()
        )

        if not lesson:
            await callback.message.answer("Занятие не найдено.")
            return

        start_time = lesson.start_time.strftime("%Y-%m-%d %H:%M")
        end_time = lesson.end_time.strftime("%H:%M")
        subject = lesson.subject if lesson.subject else "Не указана"
        teacher_name = lesson.admin.first_name if lesson.admin else "Неизвестно"

        text = (
            f"📚 <b>Тема:</b> {subject}\n"
            f"👨‍🏫 <b>Преподаватель:</b> {teacher_name}\n"
            f"🗓 <b>Дата:</b> {start_time} - {end_time}\n"
        )

        await callback.message.edit_text(
            text,
            reply_markup=get_lesson_info_keyboard(lesson.id),
            parse_mode="HTML",
        )

    finally:
        db.close()


@dp.callback_query(F.data.startswith("cancel_lesson:"))
async def cancel_lesson_handler(callback: types.CallbackQuery):
    await callback.answer()

    lesson_id = int(callback.data.split(":")[1])
    db = next(get_db())

    try:
        lesson = db.query(TimeSlot).filter(TimeSlot.id == lesson_id).first()

        if not lesson:
            await callback.message.answer("Занятие не найдено.")
            return
        user_id = (
            db.query(User).filter(User.telegram_id == callback.from_user.id).first().id
        )
        # Проверяем, что этот юзер забронировал
        if lesson.student_id != user_id:
            await callback.message.answer("Вы не записаны на это занятие.")
            return

        # Отменяем бронь
        lesson.is_booked = False
        lesson.student_id = None
        db.commit()

        await callback.message.answer("Вы успешно отменили запись ✅")
        await my_lessons_handler(callback)  # Перезапускаем список занятий
    finally:
        db.close()


@dp.callback_query(F.data == "about_us")
async def about_us_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("Мы - команда, которая делает обучение удобным!")


# --- ADMIN ---


@dp.callback_query(F.data == "add_schedule")
async def add_schedule_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "Настрой своё расписание",
        reply_markup=get_admin_calendar_keyboard(),
    )


@dp.callback_query(F.data.startswith("change_month:"))
async def change_month_handler(callback: types.CallbackQuery):
    _, year_month = callback.data.split(":")
    year, month = map(int, year_month.split("-"))
    await callback.message.edit_reply_markup(
        reply_markup=get_admin_calendar_keyboard(year, month)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("select_date:"))
async def select_date_handler(callback: types.CallbackQuery, state: FSMContext):
    _, date_str = callback.data.split(":")
    await state.update_data(selected_date=date_str)
    await callback.message.edit_text(
        f"Введите время для {date_str} в формате HH:MM - HH:MM, например, 12:00 - 13:00.",
        reply_markup=None,
    )
    await state.set_state(ScheduleStates.waiting_for_time)
    await callback.answer()


@dp.message(ScheduleStates.waiting_for_time)
async def process_time_input(message: types.Message, state: FSMContext):
    time_pattern = re.compile(r"^\d{2}:\d{2} - \d{2}:\d{2}$")
    if not time_pattern.match(message.text):
        await message.answer(
            "Неверный формат времени. Пожалуйста, введите время в формате HH:MM - HH:MM, например, 12:00 - 13:00."
        )
        return

    try:
        # Получаем сохраненную дату из состояния
        data = await state.get_data()
        date_str = data["selected_date"]

        # Разбираем введенное время
        start_time_str, end_time_str = message.text.split(" - ")
        date_format = "%Y-%m-%d %H:%M"

        start_datetime = datetime.strptime(f"{date_str} {start_time_str}", date_format)
        end_datetime = datetime.strptime(f"{date_str} {end_time_str}", date_format)

        # Сохраняем в базу данных
        db = next(get_db())
        admin_id = (
            db.query(User).filter(User.telegram_id == message.from_user.id).first().id
        )
        new_slot = TimeSlot(
            start_time=start_datetime,
            end_time=end_datetime,
            is_booked=False,
            admin_id=admin_id,
        )
        db.add(new_slot)
        db.commit()

        await message.answer(
            f"Слот успешно добавлен: {date_str} {message.text}",
            reply_markup=get_admin_keyboard(),
        )
    except ValueError as e:
        await message.answer(
            f"Ошибка: {str(e)}. Пожалуйста, проверьте правильность введенных данных."
        )
    finally:
        await state.clear()


@dp.callback_query(F.data == "view_schedule")
async def view_schedule_handler(callback: types.CallbackQuery):
    await callback.answer()

    db = next(get_db())

    try:
        # Находим текущего администратора
        admin = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

        if not admin:
            await callback.message.answer(
                "Ошибка: администратор не найден в базе данных."
            )
            return

        # Получаем все слоты, которые создал этот админ
        slots = (
            db.query(TimeSlot)
            .options(joinedload(TimeSlot.student))
            .filter(TimeSlot.admin_id == admin.id)
            .order_by(TimeSlot.start_time)
            .all()
        )

        if not slots:
            await callback.message.answer("У вас пока нет созданных слотов.")
            return

        # Создаем клавиатуру с кнопками для каждого слота
        builder = InlineKeyboardBuilder()

        for slot in slots:
            start = slot.start_time.strftime("%Y-%m-%d %H:%M")
            end = slot.end_time.strftime("%H:%M")
            if slot.is_booked and slot.student:
                student_info = (
                    f"Забронировано {slot.student.first_name} @{slot.student.username}"
                )
            else:
                student_info = "Свободно"

            button_text = f"{start} - {end} | {student_info}"
            builder.button(
                text=button_text,
                callback_data=f"delete_slot:{slot.id}",  # Передаем id слота
            )

        # Кнопка "Назад"
        builder.button(text="↩️ Назад", callback_data="back_to_menu")

        builder.adjust(1)

        await callback.message.answer(
            "Ваше текущее расписание (нажмите, чтобы удалить слот):",
            reply_markup=builder.as_markup(),
        )

    finally:
        db.close()


@dp.callback_query(F.data.startswith("delete_slot:"))
async def delete_slot_handler(callback: types.CallbackQuery):
    await callback.answer()

    slot_id = int(callback.data.split(":")[1])

    db = next(get_db())

    try:
        slot = db.query(TimeSlot).filter(TimeSlot.id == slot_id).first()

        if not slot:
            await callback.message.answer("Ошибка: слот не найден.")
            return

        db.delete(slot)
        db.commit()

        await callback.message.answer("Слот успешно удалён ✅")
    finally:
        db.close()

    await view_schedule_handler(callback)


# --- ALL ---


@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: types.CallbackQuery):
    await callback.answer()

    # Вернуть на главное меню с кнопками
    if callback.from_user.id == ADMIN_ID:
        await callback.message.edit_text(
            "Вы вернулись в главное меню администратора:",
            reply_markup=get_admin_keyboard(),
        )
    else:
        await callback.message.edit_text(
            "Добро пожаловать обратно!", reply_markup=get_user_keyboard()
        )


@dp.callback_query(F.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    await callback.answer()
