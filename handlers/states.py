from aiogram.fsm.state import State, StatesGroup


class ScheduleStates(StatesGroup):
    waiting_for_time = State()
