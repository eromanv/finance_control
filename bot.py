import logging

import matplotlib

matplotlib.use("Agg")

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)
from charts import build_category_pie_chart
from config import BOT_TOKEN
from database import async_session
from schemas import CategoryENUM, ExpenseCreateSchema
from services import (add_expense, export_expenses_to_csv, get_month_summary,
                      get_today_summary)

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
        [KeyboardButton(text="Скачать отчёт")],
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
        category_totals = [
            (item.category, item.total)
            for item in summary.category_breakdown
            if item.total > 0
        ]
        if category_totals:
            try:
                chart = build_category_pie_chart(
                    category_totals, "Категории трат за сегодня"
                )
                await message.reply_photo(
                    photo=types.BufferedInputFile(
                        chart.getvalue(), filename="today_categories.png"
                    ),
                    caption=text,
                    reply_markup=main_menu,
                )
            except ValueError:
                await message.reply(text, reply_markup=main_menu)
        else:
            await message.reply(text, reply_markup=main_menu)


@dp.message(lambda message: message.text == "Посмотреть траты с начала месяца")
async def view_month_handler(message: types.Message):
    """View month's expenses."""
    async with async_session() as db:
        summary = await get_month_summary(db, message.from_user.id)
    if summary.total == 0:
        await message.reply("В этом месяце трат нет.", reply_markup=main_menu)
    else:
        text = f"Траты с начала месяца: {summary.total:.2f} ₽"
        category_totals = [
            (item.category, item.total)
            for item in summary.category_breakdown
            if item.total > 0
        ]
        if category_totals:
            try:
                chart = build_category_pie_chart(
                    category_totals, "Категории трат за месяц"
                )
                await message.reply_photo(
                    photo=types.BufferedInputFile(
                        chart.getvalue(), filename="month_categories.png"
                    ),
                    caption=text,
                    reply_markup=main_menu,
                )
            except ValueError:
                await message.reply(text, reply_markup=main_menu)
        else:
            await message.reply(text, reply_markup=main_menu)


@dp.message(lambda message: message.text == "Скачать отчёт")
async def download_report_handler(message: types.Message):
    """Download financial report as CSV."""
    # Create inline keyboard for period selection
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="За сегодня", callback_data="report_today"
                ),
                InlineKeyboardButton(
                    text="За месяц", callback_data="report_month"
                ),
            ]
        ]
    )
    await message.reply(
        "Выберите период для отчёта:",
        reply_markup=keyboard,
    )


@dp.callback_query(lambda c: c.data.startswith("report_"))
async def report_period_callback_handler(callback_query: types.CallbackQuery):
    """Handle report period selection."""
    from datetime import date, datetime

    period = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id

    if period == "today":
        today = date.today()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
        filename = f"expenses_today_{today.strftime('%Y%m%d')}.csv"
    else:  # month
        today = date.today()
        start = datetime(today.year, today.month, 1)
        end = datetime.combine(today, datetime.max.time())
        filename = f"expenses_month_{today.strftime('%Y%m')}.csv"

    async with async_session() as db:
        csv_content = await export_expenses_to_csv(db, user_id, start, end)

    if not csv_content or csv_content == "Date,Category,Amount\n":
        await callback_query.message.edit_text("Нет данных для выгрузки.")
        await callback_query.answer()
        return

    # Send CSV file
    await callback_query.message.reply_document(
        document=types.BufferedInputFile(
            csv_content.encode("utf-8-sig"), filename=filename
        ),
        caption="Ваш финансовый отчёт",
        reply_markup=main_menu,
    )
    await callback_query.message.delete()
    await callback_query.answer()


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
