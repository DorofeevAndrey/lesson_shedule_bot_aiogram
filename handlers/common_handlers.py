from aiogram import F, types
from aiogram import Router

from config import ADMIN_ID
from keyboards.admin_keyboards import get_admin_keyboard
from keyboards.user_keyboards import get_user_keyboard

from aiogram.fsm.context import FSMContext

common_router = Router()


@common_router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
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


@common_router.callback_query(F.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    await callback.answer()
