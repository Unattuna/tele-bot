import os
import sqlite3
import random
import asyncio
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = "7753558502:AAFCnmIG38JOyTz6hfN7p5YTh-paoVEn8Wo"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# 📌 Подключение к базе данных
conn = sqlite3.connect("finance.db", check_same_thread=False)
cursor = conn.cursor()

# 📌 Создание таблицы, если её нет
cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT, 
        category TEXT DEFAULT 'без категории',
        amount REAL,
        date TEXT DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()

# 📌 Мотивационные сообщения
MOTIVATION_QUOTES = [
    "🚀 Маленькие шаги ведут к большим победам!",
    "💰 Контроль финансов – первый шаг к богатству!",
    "📊 Веди учёт сегодня, чтобы жить лучше завтра!",
    "🎯 Успех – результат дисциплины и контроля!",
    "🔥 Ты молодец, продолжай в том же духе!"
]

# 📌 Очистка текста от пробелов и приведение к нижнему регистру
def clean_text(text):
    return text.strip().lower()

# 📌 Команда /start
@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 Привет! Я помогу тебе следить за финансами.\n\n"
                         "💰 Доход: 120000 зарплата доход\n"
                         "💸 Расход: 300 такси расход\n"
                         "📊 Баланс: баланс\n"
                         "🔄 Очистка данных: очистить")

# 📌 Функция проверки суммы
def parse_amount(text):
    try:
        return float(text.replace(",", "."))  # Поддержка чисел с запятой
    except ValueError:
        return None

# 📌 Добавление доходов и расходов
@router.message()
async def add_transaction(message: types.Message):
    try:
        text = clean_text(message.text)
        parts = text.split(maxsplit=2)  # Разбиваем на 3 части: сумма, категория, тип (доход/расход)

        if len(parts) < 3:
            await message.answer("❌ Ошибка! Напиши сумму, категорию и доход/расход.\n\n"
                                 "Пример: 300 такси расход или 120000 зарплата доход")
            return

        amount = parse_amount(parts[0])
        category = parts[1].strip()
        transaction_type = parts[2].strip()

        if amount is None:
            await message.answer("❌ Ошибка! Введи корректную сумму, например: 300 такси расход")
            return

        if transaction_type not in ["доход", "расход"]:
            await message.answer("❌ Ошибка! Укажи доход или расход в конце.\n\n"
                                 "Пример: 300 такси расход или 120000 зарплата доход")
            return

        # 📌 Определяем тип транзакции
        transaction_type = "income" if transaction_type == "доход" else "expense"

        cursor.execute("INSERT INTO transactions (type, category, amount) VALUES (?, ?, ?)", 
                       (transaction_type, category, abs(amount)))
        conn.commit()

        emoji = "✅" if transaction_type == "income" else "❌"
        motivation = random.choice(MOTIVATION_QUOTES)

        await message.answer(f"{emoji} {abs(amount)} сом ({category}) записано!\n\n{motivation}")
    except Exception as e:
        await message.answer(f"❌ Ошибка! Проверь ввод.\n\nОшибка: {e}")

# 📌 Проверка баланса (разделение по категориям)
@router.message(Command("баланс"))
async def get_balance(message: types.Message):
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='income'")
    income = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='expense'")
    expense = cursor.fetchone()[0] or 0

    balance = income - expense

    # 📌 Баланс по категориям доходов
    cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE type='income' GROUP BY category")
    income_details = cursor.fetchall()
    income_text = "\n".join([f"💰 {cat.capitalize()}: {amt} сом" for cat, amt in income_details]) if income_details else "💰 Нет доходов"

    # 📌 Баланс по категориям расходов
    cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE type='expense' GROUP BY category")
    expense_details = cursor.fetchall()
    expense_text = "\n".join([f"💸 {cat.capitalize()}: {amt} сом" for cat, amt in expense_details]) if expense_details else "💸 Нет расходов"

    await message.answer(f"Твой баланс: {balance} сом\n\n"
                         f"💰 Доход: {income} сом\n{income_text}\n\n"
                         f"💸 Расход: {expense} сом\n{expense_text}")

# 📌 Очистка всех данных
@router.message(Command("очистить"))
async def clear_data(message: types.Message):
    cursor.execute("DELETE FROM transactions")
    conn.commit()
    await message.answer("🗑 Все данные очищены!")

# 📌 Автоматический отчёт в 9:00 утра
async def send_daily_report():
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='income'")
    income = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='expense'")
    expense = cursor.fetchone()[0] or 0

    balance = income - expense

    cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE type='income' GROUP BY category")
    income_details = cursor.fetchall()
    income_text = "\n".join([f"💰 {cat.capitalize()}: {amt} сом" for cat, amt in income_details]) if income_details else "💰 Нет доходов"

    cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE type='expense' GROUP BY category")
    expense_details = cursor.fetchall()
    expense_text = "\n".join([f"💸 {cat.capitalize()}: {amt} сом" for cat, amt in expense_details]) if expense_details else "💸 Нет расходов"

    report = (f"📅 Ежедневный отчёт\n\n"
              f"Твой баланс: {balance} сом\n\n"
              f"💰 Доход: {income} сом\n{income_text}\n\n"
              f"💸 Расход: {expense} сом\n{expense_text}")

    await bot.send_message(chat_id="ТВОЙ_CHAT_ID", text=report)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
