from aiogram.dispatcher.filters.state import State, StatesGroup

class MergingStates(StatesGroup):
    waiting_for_files_to_merge = State()
    waiting_for_a_name = State()
    waiting_for_specific_file = State()

class CompressingStates(StatesGroup):
    waiting_for_files_to_compress = State()
    waiting_for_a_name = State()

class CryptingStates(StatesGroup):
    waiting_for_files_to_encrypt = State()
    waiting_for_en_password = State()
    waiting_for_files_to_decrypt = State()
    waiting_for_de_password = State()

class SplittingStates(StatesGroup):
    waiting_for_files_to_split = State()
    waiting_for_pages = State()
