import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import init_db, save_city, save_breed, get_all_users, save_sent_if_new
from parser import search_puppies_smart

TOKEN = "8541930429:AAGvy5sBo_HGNi6diprKYKa3bt05AxHOB74"

bot = Bot(token=TOKEN) #через него отправляются сообщения
dp = Dispatcher()      #управляет обработчиками


# ---------------- FSM -- математическая модель системы, которая может находиться строго в одном из нескольких заранее определенных состояний в любой конкретный момент времени

class Form(StatesGroup):
    city = State()
    breed = State()


BREEDS = ["шпиц", "пудель", "болонка", "лабрадор", "овчарка", "чихуа-хуа"]


# ---------------- HANDLERS ----------------
@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    print(f"USER START: {message.from_user.id} | @{message.from_user.username}")
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Минск"), KeyboardButton(text="Гомель")],
            [KeyboardButton(text="Брест")]
        ],
        resize_keyboard=True
    )

    await state.set_state(Form.city) #переводит пользователя в состояние "ждём город"
    await message.answer("Выбери город:", reply_markup=keyboard)


@dp.message(Form.city) #Срабатывает, когда пользователь в состоянии city
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text) #сохраняет город во временную память FSM
    await state.set_state(Form.breed) #переключает на следующий шаг

    text = "Выбери породу (напиши номер):\n\n"
    for i, breed in enumerate(BREEDS, start=1): #формирует список пород с номерами
        text += f"{i}) {breed}\n"

    await message.answer(text)


@dp.message(Form.breed) #Обработка породы
async def process_breed(message: Message, state: FSMContext):
    data = await state.get_data()
    city = data["city"]

    if not message.text.isdigit(): #разрешены только цифры
        await message.answer("❗ Введи номер")
        return

    idx = int(message.text) - 1

    if idx < 0 or idx >= len(BREEDS): #защита от неверных чисел
        await message.answer("❗ Неверный номер")
        return

    breed = BREEDS[idx]
    user_id = message.from_user.id

    #запись в базу данных
    save_city(user_id, city)
    save_breed(user_id, breed)

    results = await search_puppies_smart(breed, city) #запускается парсер

    filtered = []

    for title, link in results:
        if save_sent_if_new(user_id, link): #Фильтр “не отправляли ли уже”
            filtered.append((title, link))
        if len(filtered) >= 5: #максимум 5 объявлений
            break

    if not filtered:
        await message.answer("Ничего нового 😢")
        await state.clear() #FSM сбрасывается
        return

    text = "Вот что я нашёл:\n\n"
    for title, link in filtered:
        text += f"🐶 {title}\n🔗 {link}\n\n"

    await message.answer(text)
    await state.clear()


# ---------------- BACKGROUND ----------------
async def check_new_ads():
    while True: #Работает бесконечно
        try:
            users = get_all_users() #Получаем всех пользователей

            for user_id, city, breed in users:
                results = await search_puppies_smart(breed, city)

                sent = 0

                for title, link in results:
                    if sent >= 5:
                        break

                    if save_sent_if_new(user_id, link): #Проверка новизны
                        try:
                            await bot.send_message(
                                user_id,
                                f"🐶 Новый щенок!\n\n{title}\n{link}"
                            )
                            sent += 1
                        except:
                            pass

        except Exception as e:
            print("Loop error:", e)

        await asyncio.sleep(900) #Пауза каждые 15 минут


# ---------------- WEB SERVER ----------------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self): #отвечает OK на любой запрос
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


def run_web():
    server = HTTPServer(("0.0.0.0", 10000), Handler)
    server.serve_forever()


# ---------------- MAIN ----------------
async def main():
    init_db() #создаёт БД

    # web server (Render ping fix)
    threading.Thread(target=run_web, daemon=True).start() #нужно для Render, чтобы бот не “засыпал”

    # background task
    asyncio.create_task(check_new_ads()) #запускает фоновый парсер

    await dp.start_polling(bot) #бот начинает работать


if __name__ == "__main__":
    asyncio.run(main())