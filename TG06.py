import ssl
import asyncio
import random
import aiohttp
import aiosqlite
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Предполагается, что у вас есть файл config.py с TOKEN
from config import TOKEN

# Настройка логирования
logging.basicConfig(level=logging.INFO)
#logging.info(f"Полученные данные: {data}")

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Клавиатура
keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Регистрация в телеграм боте"), KeyboardButton(text="Курс валют")],
    [KeyboardButton(text="Советы по экономии"), KeyboardButton(text="Личные финансы")]
], resize_keyboard=True)


# Определение состояний для FSM
class FinancesForm(StatesGroup):
    category1 = State()
    expenses1 = State()
    category2 = State()
    expenses2 = State()
    category3 = State()
    expenses3 = State()


# Функция для создания таблицы пользователей
async def create_table():
    async with aiosqlite.connect('user.db') as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            category1 TEXT,
            category2 TEXT,
            category3 TEXT,
            expenses1 REAL,
            expenses2 REAL,
            expenses3 REAL
        )
        ''')
        await db.commit()


# Обработчик команды /start
@dp.message(CommandStart())
async def send_start(message: Message):
    await message.answer("Привет! Я ваш личный финансовый помощник. Выберите одну из опций в меню:",
                         reply_markup=keyboard)


# Обработчик регистрации
@dp.message(F.text == "Регистрация в телеграм боте")
async def registration(message: Message):
    telegram_id = message.from_user.id
    name = message.from_user.full_name
    async with aiosqlite.connect('user.db') as db:
        cursor = await db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user = await cursor.fetchone()
        if user:
            await message.answer("Вы уже зарегистрированы!")
        else:
            await db.execute('INSERT INTO users (telegram_id, name) VALUES (?, ?)', (telegram_id, name))
            await db.commit()
            await message.answer("Вы успешно зарегистрированы!")


# Обработчик запроса курса валют
@dp.message(F.text == "Курс валют")
async def exchange_rates(message: Message):
    url = "https://v6.exchangerate-api.com/v6/56b6889b4e784e73e452d1e0/latest/USD"

    # Создаем собственный контекст SSL без проверки
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    await message.answer("Не удалось получить данные о курсе валют!")
                    return
                data = await response.json()
                logging.info(f"Полученные данные: {data}")

                usd_to_rub = data['conversion_rates']['RUB']
                eur_to_usd = data['conversion_rates']['EUR']
                euro_to_rub = eur_to_usd * usd_to_rub

                await message.answer(f"1 USD - {usd_to_rub:.2f} RUB\n"
                                     f"1 EUR - {euro_to_rub:.2f} RUB")
        except aiohttp.ClientError as e:
            logging.error(f"Ошибка при запросе к API: {e}")
            await message.answer("Произошла ошибка при получении данных")
        except KeyError as e:
            logging.error(f"Ошибка в структуре данных: {e}")
            await message.answer("Ошибка в структуре полученных данных")
        except Exception as e:
            logging.error(f"Неожиданная ошибка: {e}")
            await message.answer("Произошла непредвиденная ошибка")


# Обработчик советов по экономии
@dp.message(F.text == "Советы по экономии")
async def send_tips(message: Message):
    tips = [
        "Совет 1: Ведите бюджет и следите за своими расходами.",
        "Совет 2: Откладывайте часть доходов на сбережения.",
        "Совет 3: Покупайте товары по скидкам и распродажам."
    ]
    tip = random.choice(tips)
    await message.answer(tip)


# Обработчики для ввода личных финансов
@dp.message(F.text == "Личные финансы")
async def finances_start(message: Message, state: FSMContext):
    await state.set_state(FinancesForm.category1)
    await message.reply("Введите первую категорию расходов:")


@dp.message(FinancesForm.category1)
async def process_category1(message: Message, state: FSMContext):
    await state.update_data(category1=message.text)
    await state.set_state(FinancesForm.expenses1)
    await message.reply("Введите расходы для категории 1:")


@dp.message(FinancesForm.expenses1)
async def process_expenses1(message: Message, state: FSMContext):
    await state.update_data(expenses1=float(message.text))
    await state.set_state(FinancesForm.category2)
    await message.reply("Введите вторую категорию расходов:")


@dp.message(FinancesForm.category2)
async def process_category2(message: Message, state: FSMContext):
    await state.update_data(category2=message.text)
    await state.set_state(FinancesForm.expenses2)
    await message.reply("Введите расходы для категории 2:")


@dp.message(FinancesForm.expenses2)
async def process_expenses2(message: Message, state: FSMContext):
    await state.update_data(expenses2=float(message.text))
    await state.set_state(FinancesForm.category3)
    await message.reply("Введите третью категорию расходов:")


@dp.message(FinancesForm.category3)
async def process_category3(message: Message, state: FSMContext):
    await state.update_data(category3=message.text)
    await state.set_state(FinancesForm.expenses3)
    await message.reply("Введите расходы для категории 3:")


@dp.message(FinancesForm.expenses3)
async def process_expenses3(message: Message, state: FSMContext):
    data = await state.get_data()
    data['expenses3'] = float(message.text)
    telegram_id = message.from_user.id

    async with aiosqlite.connect('user.db') as db:
        await db.execute('''
        UPDATE users SET 
        category1 = ?, expenses1 = ?, 
        category2 = ?, expenses2 = ?, 
        category3 = ?, expenses3 = ? 
        WHERE telegram_id = ?
        ''', (data['category1'], data['expenses1'],
              data['category2'], data['expenses2'],
              data['category3'], data['expenses3'],
              telegram_id))
        await db.commit()

    await state.clear()
    await message.answer("Категории и расходы сохранены!")


# Основная функция для запуска бота
async def main():
    await create_table()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())