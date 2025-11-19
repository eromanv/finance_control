import logging

import matplotlib

matplotlib.use("Agg")

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)
from charts import build_period_snapshot_chart
from config import BOT_TOKEN
from database import async_session
from schemas import CategoryENUM, ExpenseCreateSchema
from services import add_expense, get_month_summary, get_today_summary

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class ExpenseState(StatesGroup):
    waiting_for_category = State()
    waiting_for_amount = State()


# Main menu keyboard
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Внести трату")],
        [KeyboardButton(text="Посмотреть траты сегодня")],
        [KeyboardButton(text="Посмотреть траты с начала месяца")],
    ],
    resize_keyboard=True,
)


# Category inline keyboard
def get_category_keyboard():
    """Generate inline keyboard with categories in multiple rows."""
    categories = list(CategoryENUM)
    keyboard = []

    # Split categories into rows of 2 buttons each
    for i in range(0, len(categories), 2):
        row = []
        for j in range(2):
            if i + j < len(categories):
                category = categories[i + j]
                row.append(
                    InlineKeyboardButton(
                        text=category.value, callback_data=f"category_{category.value}"
                    )
                )
        keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    """Handle /start command."""
    await message.reply(
        "Добро пожаловать в бот финансового учёта!", reply_markup=main_menu
    )


@dp.message(lambda message: message.text == "Внести трату")
async def add_expense_handler(message: types.Message, state: FSMContext):
    """Start adding expense."""
    await message.reply("Выберите категорию:", reply_markup=get_category_keyboard())
    await state.set_state(ExpenseState.waiting_for_category)


@dp.callback_query(lambda c: c.data.startswith("category_"))
async def category_callback_handler(
    callback_query: types.CallbackQuery, state: FSMContext
):
    """Handle category selection."""
    category_value = callback_query.data.split("_", 1)[
        1
    ]  # Get everything after first underscore
    try:
        # Find category by value
        category = next(cat for cat in CategoryENUM if cat.value == category_value)
        await state.update_data(category=category)
        await callback_query.message.edit_text("Введите сумму траты:")
        await state.set_state(ExpenseState.waiting_for_amount)
        await callback_query.answer()
    except StopIteration:
        await callback_query.message.edit_text(
            "Категория не найдена. Попробуйте снова."
        )
        await callback_query.answer()


@dp.message(ExpenseState.waiting_for_amount)
async def amount_handler(message: types.Message, state: FSMContext):
    """Handle amount input."""
    try:
        amount = float(message.text)
        data = await state.get_data()
        category = data["category"]
        user_id = message.from_user.id
        expense_data = ExpenseCreateSchema(
            user_id=user_id, category=category, amount=amount
        )
        async with async_session() as db:
            await add_expense(db, expense_data)
        await message.reply("Трата добавлена!", reply_markup=main_menu)
        await state.clear()
    except ValueError:
        await message.reply("Введите корректную сумму.")


@dp.message(lambda message: message.text == "Посмотреть траты сегодня")
async def view_today_handler(message: types.Message):
    """View today's expenses."""
    async with async_session() as db:
        summary = await get_today_summary(db, message.from_user.id)
    if summary.total == 0:
        await message.reply("Сегодня трат нет.", reply_markup=main_menu)
    else:
        text = f"Траты сегодня: {summary.total:.2f} ₽"
        # Generate chart comparing today vs month
        month_summary = await get_month_summary(db, message.from_user.id)
        chart = build_period_snapshot_chart(summary.total, month_summary.total)
        await message.reply_photo(
            photo=types.BufferedInputFile(chart.getvalue(), filename="chart.png"),
            caption=text,
            reply_markup=main_menu
        )


@dp.message(lambda message: message.text == "Посмотреть траты с начала месяца")
async def view_month_handler(message: types.Message):
    """View month's expenses."""
    async with async_session() as db:
        summary = await get_month_summary(db, message.from_user.id)
    if summary.total == 0:
        await message.reply("В этом месяце трат нет.", reply_markup=main_menu)
    else:
        text = f"Траты с начала месяца: {summary.total:.2f} ₽"
        # Generate chart showing daily totals
        if len(summary.daily_totals) > 1:
            # Create a line chart for daily expenses
            from io import BytesIO

            from matplotlib import pyplot as plt
            
            dates = [day.date.strftime("%d.%m") for day in summary.daily_totals]
            totals = [day.total for day in summary.daily_totals]
            
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(dates, totals, marker='o', color='#2196F3')
            ax.set_title("Дневные траты за месяц")
            ax.set_xlabel("Дата")
            ax.set_ylabel("Сумма, ₽")
            plt.xticks(rotation=45)
            fig.tight_layout()
            
            buffer = BytesIO()
            fig.savefig(buffer, format="png")
            buffer.seek(0)
            plt.close(fig)
            
            await message.reply_photo(
                photo=types.BufferedInputFile(buffer.getvalue(), filename="month_chart.png"),
                caption=text,
                reply_markup=main_menu
            )
        else:
            await message.reply(text, reply_markup=main_menu)


async def main():
    """Start the bot."""
    # Create tables
    from database import engine
    from models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
