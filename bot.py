import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from database import init_db, save_city, save_breed, get_user, get_all_users, is_sent, save_sent_if_new
from parser import search_puppies_smart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

TOKEN = "8541930429:AAGvy5sBo_HGNi6diprKYKa3bt05AxHOB74"

bot = Bot(token=TOKEN)
dp = Dispatcher()

class Form(StatesGroup):
    city = State()
    breed = State()

BREEDS = [
    "шпиц",
    "пудель",
    "болонка",
    "лабрадор",
    "овчарка",
    "чихуахуа",
]

@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Минск"), KeyboardButton(text="Гомель")],
            [KeyboardButton(text="Брест")]
        ],
        resize_keyboard=True
    )

    await state.set_state(Form.city)
    await message.answer("Выбери город:", reply_markup=keyboard)

@dp.message(Form.city)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)

    await state.set_state(Form.breed)

    text = "Выбери породу (напиши номер):\n\n"

    for i, breed in enumerate(BREEDS, start=1):
        text += f"{i}) {breed}\n"

    await message.answer(text)

@dp.message(Form.breed)
async def process_breed(message: Message, state: FSMContext):
    data = await state.get_data()
    city = data["city"]

    text = message.text.strip() #пользователь ввёл

    if not text.isdigit():
        await message.answer("❗ Введи только номер (например 1, 2, 3)")
        return

    idx = int(text) - 1

    if idx < 0 or idx >= len(BREEDS):
        await message.answer("❗ Неверный номер")
        return

    breed = BREEDS[idx]

    user_id = message.from_user.id

    save_city(user_id, city)
    save_breed(user_id, breed)

    results = search_puppies_smart(breed, city)

    if not results:
        await message.answer("Ничего не найдено 😢")
        await state.clear()
        return

    text = "Вот что я нашёл:\n\n"

    filtered = []

    for title, link in results:
        if save_sent_if_new(user_id, link):
            filtered.append((title, link))

        if len(filtered) >= 5:
            break

    if not filtered:
        await message.answer("Ничего нового 😢")
        await state.clear()
        return

    text = "Вот что я нашёл:\n\n"
    for title, link in filtered:
        text += f"🐶 {title}\n🔗 {link}\n\n"

    await message.answer(text)
    await state.clear()
    
async def check_new_ads(bot): #Фоновая функция
    while True: #Бесконечный цикл
        users = get_all_users() #Получение всех пользователей

        for user_id, city, breed in users: #Перебор пользователей
            results = search_puppies_smart(breed, city) #вызываем парсер

            sent_count = 0

            for title, link in results:
                if sent_count >= 5:
                    break

                if save_sent_if_new(user_id, link):
                    text = f"Найден новый щенок 🐶\n\n{title}\n{link}"
                    
                    try:
                        await bot.send_message(user_id, text)
                        sent_count += 1
                    except Exception as e:
                        print("Send error:", e)

        await asyncio.sleep(300)  # 5 минут

async def main():
    init_db() #создаём БД (если её нет)

    asyncio.create_task(check_new_ads(bot))  #бот отвечает пользователям и проверяет объявления

    await dp.start_polling(bot) #запускаем бота


if __name__ == "__main__":
    asyncio.run(main())