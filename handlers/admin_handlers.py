import asyncio
from aiogram import Router

from datetime import datetime
import re
from aiogram import F, types
from sqlalchemy.orm import joinedload
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from handlers.states import ScheduleStates
from keyboards.admin_keyboards import (
    get_admin_calendar_keyboard,
    get_admin_keyboard,
    get_admin_selected_slot_keyboard,
    get_admin_shedule_slots_keyboard,
)

from database import get_db

from keyboards.common_keyboards import get_back_to_menu_keyboard
from models import TimeSlot, User


admin_router = Router()


@admin_router.callback_query(F.data == "add_schedule")
async def add_schedule_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "Настрой своё расписание",
        reply_markup=get_admin_calendar_keyboard(),
    )


@admin_router.callback_query(F.data.startswith("change_month:"))
async def change_month_handler(callback: types.CallbackQuery):
    _, year_month = callback.data.split(":")
    year, month = map(int, year_month.split("-"))
    await callback.message.edit_reply_markup(
        reply_markup=get_admin_calendar_keyboard(year, month)
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("select_date:"))
async def select_date_handler(callback: types.CallbackQuery, state: FSMContext):
    _, date_str = callback.data.split(":")
    await state.update_data(selected_date=date_str)

    await callback.message.edit_text(
        f"Введите время для {date_str} в формате HH:MM - HH:MM, например, 12:00 - 13:00.",
        reply_markup=get_back_to_menu_keyboard(),
    )
    await state.set_state(ScheduleStates.waiting_for_time)
    await callback.answer()


@admin_router.message(ScheduleStates.waiting_for_time)
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

        date_format = "%d-%m-%Y %H:%M"

        start_datetime = datetime.strptime(f"{date_str} {start_time_str}", date_format)
        end_datetime = datetime.strptime(f"{date_str} {end_time_str}", date_format)

        # Сохраняем в базу данных
        db = next(get_db())
        # admin_id = (
        #     db.query(User).filter(User.telegram_id == message.from_user.id).first().id
        # )
        new_slot = TimeSlot(
            start_time=start_datetime,
            end_time=end_datetime,
            is_booked=False,
            admin_id=ADMIN_ID,
        )
        db.add(new_slot)
        db.commit()

        await message.answer(
            f"Слот успешно добавлен: {date_str} {message.text} ✅",
            reply_markup=get_admin_keyboard(),
        )
    except ValueError as e:
        await message.answer(
            f"Ошибка: {str(e)}. Пожалуйста, проверьте правильность введенных данных."
        )
    finally:
        await state.clear()


@admin_router.callback_query(F.data == "view_schedule")
async def view_schedule_handler(callback: types.CallbackQuery):
    await callback.answer()

    db = next(get_db())

    try:
        # Находим текущего администратора
        # admin = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

        # if not admin:
        #     await callback.message.answer(
        #         "Ошибка: администратор не найден в базе данных."
        #     )
        #     return

        # Получаем все слоты, которые создал этот админ
        slots = (
            db.query(TimeSlot)
            .options(joinedload(TimeSlot.student))
            .filter(TimeSlot.admin_id == ADMIN_ID)
            .order_by(TimeSlot.start_time)
            .all()
        )

        if not slots:
            await callback.message.edit_text(
                "У вас пока нет созданных слотов.",
                reply_markup=get_back_to_menu_keyboard(),
            )
            return

        await callback.message.edit_text(
            "Ваше текущее расписание (нажмите, чтобы посмотреть информацию):",
            reply_markup=get_admin_shedule_slots_keyboard(slots),
        )

    finally:
        db.close()


@admin_router.callback_query(F.data.startswith("selected_slot:"))
async def delete_slot_handler(callback: types.CallbackQuery):
    await callback.answer()

    slot_id = int(callback.data.split(":")[1])

    db = next(get_db())

    try:
        slot = (
            db.query(TimeSlot)
            .options(joinedload(TimeSlot.student))
            .filter(TimeSlot.id == slot_id)
            .first()
        )
        start = slot.start_time.strftime("%d-%m-%Y %H:%M")
        end = slot.end_time.strftime("%H:%M")
        date_str = f"{start} - {end}"
        has_student = slot.student
        if not slot:
            await callback.message.answer("Ошибка: слот не найден.")
            return

        if has_student:
            # Если слот занят студентом
            student_info = f" @{slot.student.username}"

            await callback.message.edit_text(
                f"Запись на {date_str}\n" f"Студент: {student_info}",
                reply_markup=get_admin_selected_slot_keyboard(slot_id),
            )
        else:
            # Если слот свободен
            await callback.message.edit_text(
                f"Запись на {date_str}\n" f"Статус: Свободен",
                reply_markup=get_admin_selected_slot_keyboard(slot_id),
            )

    finally:
        db.close()


@admin_router.callback_query(F.data.startswith("delete_slot:"))
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

        temp_message = await callback.message.answer("Слот успешно удалён ✅")
        await asyncio.sleep(1)
        await temp_message.delete()

    finally:
        db.close()
    await view_schedule_handler(callback)
