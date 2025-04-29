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
    get_admin_accept_or_reject_slot_keyboard,
    get_admin_calendar_keyboard,
    get_admin_cancel_selected_slot_keyboard,
    get_admin_delete_selected_slot_keyboard,
    get_admin_keyboard,
    get_admin_shedule_slots_keyboard,
)

from database import get_db

from keyboards.common_keyboards import (
    get_back_to_menu_keyboard,
    get_ok_to_menu_keyboard,
)
from models import TimeSlot, User

from bot_instance import bot


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


# @admin_router.message(ScheduleStates.waiting_for_time)
# async def process_time_input(message: types.Message, state: FSMContext):
#     time_pattern = re.compile(r"^\d{2}:\d{2} - \d{2}:\d{2}$")
#     if not time_pattern.match(message.text):
#         await message.answer(
#             "Неверный формат времени. Пожалуйста, введите время в формате HH:MM - HH:MM, например, 12:00 - 13:00.",
#             reply_markup=get_back_to_menu_keyboard(),
#         )
#         # Состояние остается активным для повторного ввода
#         return

#     try:
#         # Получаем сохраненную дату из состояния
#         data = await state.get_data()
#         date_str = data["selected_date"]

#         # Разбираем введенное время
#         start_time_str, end_time_str = message.text.split(" - ")

#         date_format = "%d-%m-%Y %H:%M"

#         start_datetime = datetime.strptime(f"{date_str} {start_time_str}", date_format)
#         end_datetime = datetime.strptime(f"{date_str} {end_time_str}", date_format)

#         if end_datetime <= start_datetime:
#             await message.answer(
#                 "Ошибка: время окончания должно быть позже времени начала."
#             )
#             return

#         # Сохраняем в базу данных
#         db = next(get_db())
#         # admin = db.query(User).filter(User.telegram_id == message.from_user.id).first()
#         admin = db.query(User).filter(User.telegram_id == ADMIN_ID).first()
#         existing_slot = (
#             db.query(TimeSlot)
#             .filter(
#                 TimeSlot.start_time == start_datetime,
#                 TimeSlot.end_time == end_datetime,
#                 TimeSlot.admin_id == admin.id,
#             )
#             .first()
#         )
#         if existing_slot:
#             await message.answer(
#                 "⚠️ Такой временной слот уже существует!\n"
#                 f"Дата: {date_str}\n"
#                 f"Время: {message.text}",
#             )
#             return

#         new_slot = TimeSlot(
#             start_time=start_datetime,
#             end_time=end_datetime,
#             is_booked=False,
#             admin_id=admin.id,
#         )
#         db.add(new_slot)
#         db.commit()

#         await message.answer(
#             f"Слот успешно добавлен: {date_str} {message.text} ✅",
#             reply_markup=get_admin_keyboard(),
#         )
#     except ValueError as e:
#         await message.answer(
#             f"Ошибка: {str(e)}. Пожалуйста, проверьте правильность введенных данных."
#         )
#     finally:
#         await state.clear()


@admin_router.message(ScheduleStates.waiting_for_time)
async def process_time_input(message: types.Message, state: FSMContext):
    time_pattern = re.compile(r"^\d{2}:\d{2} - \d{2}:\d{2}$")

    # Сохраняем состояние перед проверками
    data = await state.get_data()
    date_str = data["selected_date"]

    if not time_pattern.match(message.text):
        await message.answer(
            "Неверный формат времени. Пожалуйста, введите время в формате HH:MM - HH:MM, например, 12:00 - 13:00.",
            reply_markup=get_back_to_menu_keyboard(),
        )
        # Состояние остается активным для повторного ввода
        return

    try:
        # Разбираем введенное время
        start_time_str, end_time_str = message.text.split(" - ")
        date_format = "%d-%m-%Y %H:%M"

        start_datetime = datetime.strptime(f"{date_str} {start_time_str}", date_format)
        end_datetime = datetime.strptime(f"{date_str} {end_time_str}", date_format)

        # Проверяем, что время окончания позже времени начала
        if end_datetime <= start_datetime:
            await message.answer(
                "Ошибка: время окончания должно быть позже времени начала.\n"
                "Пожалуйста, введите время заново:",
                reply_markup=get_back_to_menu_keyboard(),
            )
            # Состояние остается активным для повторного ввода
            return

        db = next(get_db())
        try:
            admin = db.query(User).filter(User.telegram_id == ADMIN_ID).first()
            # Проверяем на существующий слот
            existing_slot = (
                db.query(TimeSlot)
                .filter(
                    TimeSlot.start_time == start_datetime,
                    TimeSlot.end_time == end_datetime,
                    TimeSlot.admin_id == admin.id,
                )
                .first()
            )

            if existing_slot:
                await message.answer(
                    "⚠️ Такой временной слот уже существует!\n"
                    f"Дата: {date_str}\n"
                    f"Время: {message.text}\n\n"
                    "Пожалуйста, введите другое время:",
                    reply_markup=get_back_to_menu_keyboard(),
                )
                # Состояние остается активным для повторного ввода
                return

            # Создаем новый слот

            new_slot = TimeSlot(
                start_time=start_datetime,
                end_time=end_datetime,
                is_booked=False,
                admin_id=admin.id,
            )
            db.add(new_slot)
            db.commit()

            await message.answer(
                f"Слот успешно добавлен: {date_str} {message.text} ✅",
                reply_markup=get_admin_keyboard(),
            )
            await state.clear()  # Очищаем состояние только при успешном добавлении

        except Exception as e:
            await message.answer(
                f"Произошла ошибка: {str(e)}\n" "Пожалуйста, попробуйте еще раз:",
                reply_markup=get_back_to_menu_keyboard(),
            )
            # Состояние остается активным для повторного ввода
            return
        finally:
            db.close()

    except ValueError as e:
        await message.answer(
            f"Ошибка формата: {str(e)}\n"
            "Пожалуйста, введите время заново в формате HH:MM - HH:MM:",
            reply_markup=get_back_to_menu_keyboard(),
        )
        # Состояние остается активным для повторного ввода
        return


@admin_router.callback_query(F.data == "view_schedule")
async def view_schedule_handler(callback: types.CallbackQuery):
    await callback.answer()

    db = next(get_db())

    try:
        # Находим текущего администратора
        admin = db.query(User).filter(User.telegram_id == callback.from_user.id).first()

        # admin = db.query(User).filter(User.telegram_id == ADMIN_ID).first()
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

        has_student = slot.student_id != None
        if not slot:
            await callback.message.answer("Ошибка: слот не найден.")
            return
        # Если есть студент
        if has_student:
            student = slot.student

            student_info = (
                f"@{student.username}"
                if student.username
                else f"{student.full_name} (ID: {student.id})"
            )
            # Если слот занят студентом
            if slot.is_booked == True:
                await callback.message.edit_text(
                    f"Запись на {date_str}\n Студент: {student_info}",
                    reply_markup=get_admin_cancel_selected_slot_keyboard(slot_id),
                )
            else:
                # Если слот в ожидании
                await callback.message.edit_text(
                    f"Запись на {date_str}\n"
                    f"Статус: В ожидании\n Студент: @{student_info}",
                    reply_markup=get_admin_accept_or_reject_slot_keyboard(slot_id),
                )

        else:
            # Если слот свободен
            await callback.message.edit_text(
                f"Запись на {date_str}\n" f"Статус: Свободна",
                reply_markup=get_admin_delete_selected_slot_keyboard(slot_id),
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

        await callback.message.edit_text(
            "Слот успешно удалён ✅", reply_markup=get_ok_to_menu_keyboard()
        )

    finally:
        db.close()
    # await view_schedule_handler(callback)


@admin_router.callback_query(F.data.startswith("is_booked_slot:"))
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

        if not slot:
            await callback.message.answer("Ошибка: слот не найден.")
            return

        chat_id = slot.student.telegram_id
        start = slot.start_time.strftime("%d-%m-%Y %H:%M")
        end = slot.end_time.strftime("%H:%M")
        date_str = f"{start} - {end}"

        slot.is_booked = True
        db.commit()

        await callback.message.edit_text(
            f"Отлично! Вы приняли слот на {date_str}, удачной работы)",
            reply_markup=get_ok_to_menu_keyboard(),
        )

        print(chat_id)
        await bot.send_message(
            chat_id=chat_id,
            text=f"Администратор одобрил ващу заявку на {date_str}, хороших уроков",
            reply_markup=get_ok_to_menu_keyboard(),
        )
    finally:
        db.close()


@admin_router.callback_query(F.data.startswith("cancel_booked_slot:"))
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

        if not slot:
            await callback.message.answer("Ошибка: слот не найден.")
            return

        chat_id = slot.student.telegram_id
        start = slot.start_time.strftime("%d-%m-%Y %H:%M")
        end = slot.end_time.strftime("%H:%M")
        date_str = f"{start} - {end}"

        slot.student_id = None
        db.commit()

        await callback.message.edit_text(
            f"Вы отменили слот на {date_str}\n На него все ещё могут записаться другие пользователи!",
            reply_markup=get_ok_to_menu_keyboard(),
        )
        print(chat_id)
        await bot.send_message(
            chat_id=chat_id,
            text=f"Администратор отменил ващу заявку на {date_str}",
            reply_markup=get_ok_to_menu_keyboard(),
        )

    finally:
        db.close()


@admin_router.callback_query(F.data.startswith("cansel_user_selected_slot:"))
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

        if not slot:
            await callback.message.answer("Ошибка: слот не найден.")
            return

        chat_id = slot.student.telegram_id
        start = slot.start_time.strftime("%d-%m-%Y %H:%M")
        end = slot.end_time.strftime("%H:%M")
        date_str = f"{start} - {end}"

        slot.student_id = None
        slot.is_booked = False
        db.commit()

        await callback.message.edit_text(
            f"Вы отменили занятие на {date_str}\n На него все ещё могут записаться другие пользователи!",
            reply_markup=get_ok_to_menu_keyboard(),
        )
        print(chat_id)
        await bot.send_message(
            chat_id=chat_id,
            text=f"Администратор отменил ваще занятие на {date_str}",
            reply_markup=get_ok_to_menu_keyboard(),
        )

    finally:
        db.close()
