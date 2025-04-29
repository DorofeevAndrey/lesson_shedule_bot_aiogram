from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_back_to_menu_keyboard():
    keyboard = []
    keyboard.append(
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
