import asyncio
from aiogram import Router

from datetime import datetime

from aiogram import F, types
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from config import ADMIN_ID
from database import get_db
from keyboards.admin_keyboards import get_admin_accept_or_reject_slot_keyboard
from keyboards.common_keyboards import (
    get_back_to_menu_keyboard,
    get_ok_to_menu_keyboard,
)
from models import TimeSlot, User
from bot_instance import bot


from keyboards.user_keyboards import (
    get_all_user_lesson_keyboard,
    get_back_to_user_signup_keyboard,
    get_slots_time_user_keyboard,
    get_user_calendar_keyboard,
    get_user_lesson_info_keyboard,
)

user_router = Router()


@user_router.callback_query(F.data == "sign_up")
async def add_schedule_handler(callback: types.CallbackQuery):
    await callback.answer()

    await callback.message.edit_text(
        "Выбери свободный день:",
        reply_markup=get_user_calendar_keyboard(),
    )


@user_router.callback_query(F.data.startswith("view_calendar:"))
async def process_calendar_navigation(callback: types.CallbackQuery):
    await callback.answer()

    _, date_str = callback.data.split(":")
    year, month = map(int, date_str.split("-"))

    await callback.message.edit_text(
        "Выбери свободный день:",
        reply_markup=get_user_calendar_keyboard(year, month),
    )


@user_router.callback_query(F.data.startswith("select_slot_date:"))
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
        keyboard = get_slots_time_user_keyboard(slots)

        await callback.message.edit_text(
            "Выбери время:",
            reply_markup=keyboard,
        )
    finally:
        db.close()


@user_router.callback_query(F.data.startswith("select_slot:"))
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
        slot.is_booked = False  # Нужно подтвреждение
        db.commit()
        await callback.message.edit_text(
            f"✅ Ваша заявка на слот {slot.start_time.strftime('%d-%m-%Y %H:%M')} - {slot.end_time.strftime('%H:%M')} отправлена.\n"
            "Ожидайте подтверждения от администратора. Вы получите уведомление, когда заявка будет обработана.",
            reply_markup=get_ok_to_menu_keyboard(),
        )
        user_link = f"tg://openmessage?user_id={1387661016}"
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Новая заявка на слот:\n"
            f"Дата: {slot.start_time.strftime('%d-%m-%Y %H:%M')}\n"
            f"👤 Студент: @{student.username}\n",
            reply_markup=get_admin_accept_or_reject_slot_keyboard(slot_id),
        )
        # # Отправляем подтверждение
        # await callback.message.edit_text(
        #     f"Вы успешно записались на слот {slot.start_time.strftime('%d-%m-%Y %H:%M')} - {slot.end_time.strftime('%H:%M')}."
        # )

    finally:
        db.close()

    # Возвращаемся к меню
    # await callback.message.edit_reply_markup(reply_markup=get_user_calendar_keyboard())


@user_router.callback_query(F.data == "my_lessons")
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
            .filter(TimeSlot.is_booked == True)
            .order_by(TimeSlot.start_time)
            .all()
        )

        if not lessons:
            await callback.message.edit_text(
                "У вас пока нет записей на занятия 📚",
                reply_markup=get_back_to_user_signup_keyboard(),
            )
            return

        # Строим клавиатуру занятий
        keyboard = get_all_user_lesson_keyboard(lessons)

        await callback.message.edit_text("Ваши занятия:", reply_markup=keyboard)

    finally:
        db.close()


@user_router.callback_query(F.data.startswith("lesson_info:"))
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
            await callback.message.edit_text(
                "Занятие не найдено.", reply_markup=get_back_to_menu_keyboard()
            )
            return

        start_time = lesson.start_time.strftime("%d-%m-%Y %H:%M")
        end_time = lesson.end_time.strftime("%H:%M")
        subject = lesson.subject if lesson.subject else "Не указана"
        teacher_name = lesson.admin.first_name if lesson.admin else "Неизвестно"

        text = (
            # f"📚 <b>Тема:</b> {subject}\n"
            # f"👨‍🏫 <b>Преподаватель:</b> {teacher_name}\n"
            f"🗓 <b>Дата:</b> {start_time} - {end_time}\n"
        )

        await callback.message.edit_text(
            text,
            reply_markup=get_user_lesson_info_keyboard(lesson.id),
            parse_mode="HTML",
        )

    finally:
        db.close()


@user_router.callback_query(F.data.startswith("cancel_lesson:"))
async def cancel_lesson_handler(callback: types.CallbackQuery):
    await callback.answer()

    lesson_id = int(callback.data.split(":")[1])
    db = next(get_db())

    try:
        lesson = db.query(TimeSlot).filter(TimeSlot.id == lesson_id).first()

        if not lesson:
            await callback.message.answer("Занятие не найдено.")
            return
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        # Проверяем, что этот юзер забронировал
        if lesson.student_id != user.id:
            await callback.message.answer("Вы не записаны на это занятие.")
            return
        start = lesson.start_time.strftime("%d-%m-%Y %H:%M")
        end = lesson.end_time.strftime("%H:%M")
        date_str = f"{start} - {end}"

        # Отменяем бронь
        lesson.is_booked = False
        lesson.student_id = None
        db.commit()

        await callback.message.edit_text(
            "Вы успешно отменили запись ✅", reply_markup=get_ok_to_menu_keyboard()
        )

        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"@{user.username} отменил запись на {date_str}",
        )

        # await my_lessons_handler(callback)  # Перезапускаем список занятий
    finally:
        db.close()


@user_router.callback_query(F.data == "about_us")
async def about_us_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer("Мы - команда, которая делает обучение удобным!")
