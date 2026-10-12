import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# ReportLab kutubxonasi - PDF yaratish uchun
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# Telegram Bot Tokeningizni quyidagi o'zgaruvchiga yozing yoki Environment Variable (Railway) orqali bering
BOT_TOKEN = os.getenv("TOKEN", "8677645400:AAF9QNkolKBHUc2rbCqxZpruAcJyXRn3TvY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Bot bosqichlari (FSM States)
class HandwritingForm(StatesGroup):
    waiting_for_sample = State()
    waiting_for_pen_color = State()
    waiting_for_text = State()

# PDF yaratuvchi funksiya
def create_handwritten_pdf(text: str, pen_color: str, filename: str = "konspekt.pdf") -> str:
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Ruchka rangini belgilash
    if pen_color.lower() == "qora":
        text_color = colors.HexColor("#1A1A1A")
    elif pen_color.lower() == "qizil":
        text_color = colors.HexColor("#C0392B")
    elif pen_color.lower() == "yashil":
        text_color = colors.HexColor("#27AE60")
    else:  # Sukut bo'yicha Ko'k
        text_color = colors.HexColor("#1D4ED8")

    # Katakli daftar fonini chizish (A4 o'lchami uchun)
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.setLineWidth(0.5)
    grid_size = 20  # Kataklar hajmi

    for x in range(0, int(width), grid_size):
        c.line(x, 0, x, height)
    for y in range(0, int(height), grid_size):
        c.line(0, y, width, y)

    # Matnni chizish
    c.setFillColor(text_color)
    # Eslatma: Standart ReportLab da 'Courier-Oblique' qo'l yozmasiga o'xshash qiya shrift beradi
    c.setFont("Courier-Oblique", 14)

    margin_x = 40
    y_position = height - 50
    line_height = 22

    # Matnni qatorma-qator PDF ga joylash
    lines = text.split('\n')
    for line in lines:
        # Uzun satrlarni bo'lish (A4 varag'iga sig'ishi uchun)
        words = line.split(' ')
        current_line = ""
        for word in words:
            if c.stringWidth(current_line + " " + word, "Courier-Oblique", 14) < (width - margin_x * 2):
                current_line += (" " if current_line else "") + word
            else:
                c.drawString(margin_x, y_position, current_line)
                y_position -= line_height
                current_line = word
                if y_position < 50:  # Yangi sahifaga o'tish
                    c.showPage()
                    y_position = height - 50

        if current_line:
            c.drawString(margin_x, y_position, current_line)
            y_position -= line_height

        if y_position < 50:
            c.showPage()
            y_position = height - 50

    c.save()
    return filename

# --- HANDLERLAR (BUYRUQLAR VA XABARLAR) ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "👋 Salom! **Konspekt Botiga** xush kelibsiz.\n\n"
        "Matningizni qo'l yozmasiga o'xshatib PDF qilib beraman.\n"
        "Iltimos, boshlash uchun **qo'l yozmangiz namunasini (rasmini)** yuboring:"
    )
    await state.set_state(HandwritingForm.waiting_for_sample)

# Rasm namunasini qabul qilish
@dp.message(HandwritingForm.waiting_for_sample, F.photo)
async def process_sample(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(sample_photo=photo_id)

    # Ruchka rangini tanlash uchun tugmalar
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Ko'k"), KeyboardButton(text="Qora")],
            [KeyboardButton(text="Qizil"), KeyboardButton(text="Yashil")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "✅ Rasm namunasi qabul qilindi!\n\n"
        "Endi konspekt uchun **ruchka rangini** tanlang:",
        reply_markup=keyboard
    )
    await state.set_state(HandwritingForm.waiting_for_pen_color)

# Ruchka rangini qabul qilish
@dp.message(HandwritingForm.waiting_for_pen_color)
async def process_pen_color(message: types.Message, state: FSMContext):
    selected_color = message.text
    await state.update_data(pen_color=selected_color)

    await message.answer(
        f"🎨 Rang: **{selected_color}** tanlandi.\n\n"
        "Endi qo'l yozmaga aylantirmoqchi bo'lgan **matningizni yuboring**:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(HandwritingForm.waiting_for_text)

# Matnni qabul qilib, PDF yaratish va yuborish
@dp.message(HandwritingForm.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    user_text = message.text
    data = await state.get_data()
    pen_color = data.get("pen_color", "Ko'k")

    status_msg = await message.answer("⏳ Matningiz qayta ishlanib, PDF konspekt tayyorlanmoqda...")

    # PDF fayl joylashuvi va nomi
    pdf_filename = f"konspekt_{message.from_user.id}.pdf"

    try:
        # PDF generatsiya qilamiz
        generated_file = create_handwritten_pdf(user_text, pen_color, pdf_filename)

        # PDF ni Telegram'ga yuklaymiz
        document = FSInputFile(generated_file)

        # Hujjatni yuboramiz
        await message.answer_document(
            document=document,
            caption="✅ **Konspektingiz tayyor!**\n\nQayta ishlatish uchun /start bosing."
        )

        # Vaqtinchalik PDF faylni serverdan o'chiramiz
        if os.path.exists(generated_file):
            os.remove(generated_file)

    except Exception as e:
        logging.error(f"Xatolik yuz berdi: {e}")
        await message.answer("❌ PDF yaratishda xatolik yuz berdi. Qaytadan urinib ko'ring.")

    finally:
        await status_msg.delete()
        await state.clear()

# Botni ishga tushirish
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
