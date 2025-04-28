import asyncio
from bot_instance import bot, dp
from database import SessionLocal, create_tables
import handlers

from aiogram.filters import Command
from config import ADMIN_ID
from keyboards import get_admin_keyboard, get_user_keyboard
from aiogram import types

from models import User


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    db = SessionLocal()

    try:
        # Проверяем, есть ли пользователь в базе
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

        if not user:
            # Если нет — создаем нового
            new_user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username or "",
                first_name=message.from_user.first_name or "",
                last_name=message.from_user.last_name or "",
            )
            db.add(new_user)
            db.commit()

        # Ответ пользователю
        if message.from_user.id == ADMIN_ID:
            await message.answer(
                f"Добро пожаловать, {message.from_user.username}, вы админ! Выберите действие:",
                reply_markup=get_admin_keyboard(),
            )
        else:
            await message.answer(
                f"Добро пожаловать, {message.from_user.username}, Выберите действие:",
                reply_markup=get_user_keyboard(),
            )
    finally:
        db.close()


@dp.message(Command("admin"))
async def start_handler(message: types.Message):
    await message.answer(
        "Вы вошли как администратор:", reply_markup=get_admin_keyboard()
    )


@dp.message(Command("user"))
async def start_handler(message: types.Message):
    await message.answer("Вы вошли как пользователь:", reply_markup=get_user_keyboard())


@dp.message(Command("id"))
async def start_handler(message: types.Message):
    current_user_id = message.from_user.id
    await message.answer(f"Ваш id: {current_user_id}")


async def main():
    create_tables()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
