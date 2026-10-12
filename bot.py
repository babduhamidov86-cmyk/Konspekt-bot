import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Bot tokeningizni shu yerga yozasiz
TOKEN = "8631321883:AAGaCZRr6R5xIBsQWsC0lprVZxjhVwKBpgA"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Bot bosqichlari (FSM States)
class HandwritingForm(StatesGroup):
    waiting_for_sample = State()
    waiting_for_pen_color = State()
    waiting_for_text = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "Salom! Talabalar uchun konspekt botiga xush kelibsiz.\n\n"
        "Iltimos, qo'l yozmangiz o'xshashi uchun menga **qo'lda yozilgan matningiz namunasini** (rasmini) yuboring:"
    )
    await state.set_state(HandwritingForm.waiting_for_sample)

@dp.message(HandwritingForm.waiting_for_sample, F.photo)
async def process_sample(message: types.Message, state: FSMContext):
    # Rasmni saqlab qolish yoki ID sini olish
    photo_id = message.photo[-1].file_id
    await state.update_data(sample_photo=photo_id)
    
    await message.answer(
        "Rasm qabul qilindi! Endi ruchka rangini tanlang (masalan: ko'k yoki qora):"
    )
    await state.set_state(HandwritingForm.waiting_for_pen_color)

@dp.message(HandwritingForm.waiting_for_pen_color)
async def process_pen_color(message: types.Message, state: FSMContext):
    await state.update_data(pen_color=message.text)
    
    await message.answer(
        "Zo'r! Endi qo'l yozmaga aylantirmoqchi bo'lgan **matningizni** yuboring:"
    )
    await state.set_state(HandwritingForm.waiting_for_text)

@dp.message(HandwritingForm.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    user_text = message.text
    data = await state.get_data()
    
    await message.answer("⏳ Matningiz qo'l yozmaga o'girilmoqda, biroz kuting...")
    
    # Bu yerda Pillow / ReportLab orqali matnni PDF ga o'girish kodi yoziladi
    # Hozircha misol tariqasida habar yuboramiz:
    
    await message.answer("✅ Tayyor! Siz so'ragan konspekt PDF fayli shaklida tayyorlandi.")
    # Bot orqali PDF yuborish kodi shu yerga qo'shiladi
    
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
