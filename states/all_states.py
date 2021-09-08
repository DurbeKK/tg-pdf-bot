from aiogram.dispatcher.filters.state import State, StatesGroup

class MergingStates(StatesGroup):
    waiting_for_files_to_merge = State()
    waiting_for_a_name = State()
    waiting_for_specific_file = State()

class CompressingStates(StatesGroup):
    waiting_for_files_to_compress = State()
    waiting_for_a_name = State()
