import sqlite3
from aiogram import Bot, Dispatcher, types, Router, F
import asyncio

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
        amount REAL
    )
''')
conn.commit()

# 📌 Функция для обработки команд (убирает пробелы и делает текст в нижнем регистре)
def clean_text(text):
    return text.strip().lower()

# 📌 Команда "старт"
@router.message()
async def start(message: types.Message):
    if clean_text(message.text) in ["старт", "/start"]:
        await message.answer("👋 Привет! Я помогу тебе следить за финансами.\n\n"
                             "💰 **Доход:** Просто напиши **1000 зарплата**\n"
                             "💸 **Расход:** Например, **500 такси**\n"
                             "📊 **Баланс:** Напиши **баланс**\n"
                             "🔄 **Сбросить данные:** **очистить**")
        return

    # 📌 Проверка баланса
    if clean_text(message.text) in ["баланс", "/баланс"]:
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

        await message.answer(f"📊 **Твой баланс:** {balance} сом\n\n"
                             f"💰 **Доход:** {income} сом\n{income_text}\n\n"
                             f"💸 **Расход:** {expense} сом\n{expense_text}")
        return

    # 📌 Очистка всех данных
    if clean_text(message.text) in ["очистить", "/очистить"]:
        cursor.execute("DELETE FROM transactions")
        conn.commit()
        await message.answer("🗑️ Все данные очищены!")
        return

    # 📌 Функция проверки суммы
    def parse_amount(text):
        try:
            return float(text.replace(",", "."))  # Поддержка чисел с запятой
        except ValueError:
            return None

    # 📌 Обработчик доходов и расходов (например, "500 доставка" или "1000 зарплата")
    try:
        parts = message.text.strip().split(maxsplit=1)  # Разделяем только на 2 части: сумма + категория

        if len(parts) < 2:
            await message.answer("❌ Ошибка! Напиши сумму и категорию, например: **500 такси** или **1000 зарплата**")
            return

        amount = parse_amount(parts[0])
        category = parts[1].strip().lower()

        if amount is None:
            await message.answer("❌ Ошибка! Введи правильную сумму, например: **500 такси** или **1000 зарплата**")
            return

        transaction_type = "income" if amount > 0 else "expense"

        cursor.execute("INSERT INTO transactions (type, category, amount) VALUES (?, ?, ?)", 
                       (transaction_type, category, abs(amount)))
        conn.commit()

        emoji = "✅" if transaction_type == "income" else "❌"
        await message.answer(f"{emoji} **{abs(amount)} сом** ({category}) записано!")
    except Exception as e:
        await message.answer(f"❌ Ошибка! Проверь ввод.\n\nОшибка: {e}")

# 📌 Добавляем `router` в `Dispatcher`
dp.include_router(router)

# 📌 Запуск бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
