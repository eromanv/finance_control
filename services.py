from datetime import date, datetime
from typing import List, Tuple

from models import ExpenseModel
from schemas import (ExpenseCreateSchema, ExpenseDaySchema,
                     ExpensePeriodSummarySchema, ExpenseSchema)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def add_expense(db: AsyncSession, expense: ExpenseCreateSchema) -> ExpenseSchema:
    """Add a new expense to the database."""
    db_expense = ExpenseModel(
        user_id=expense.user_id,
        category=expense.category.value,
        amount=expense.amount,
        date=datetime.utcnow(),
    )
    db.add(db_expense)
    await db.commit()
    await db.refresh(db_expense)
    return ExpenseSchema.from_orm(db_expense)


def _today_bounds() -> Tuple[datetime, datetime]:
    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())
    return start, end


def _month_bounds() -> Tuple[datetime, datetime]:
    today = date.today()
    start = datetime(today.year, today.month, 1)
    end = datetime.combine(today, datetime.max.time())
    return start, end


async def _fetch_total_value(
    db: AsyncSession, user_id: int, start: datetime, end: datetime
) -> float:
    query = select(func.coalesce(func.sum(ExpenseModel.amount), 0)).where(
        ExpenseModel.user_id == user_id,
        ExpenseModel.date >= start,
        ExpenseModel.date <= end,
    )
    total = await db.scalar(query)
    return float(total or 0)


async def _fetch_daily_totals(
    db: AsyncSession, user_id: int, start: datetime, end: datetime
) -> List[ExpenseDaySchema]:
    # For SQLite compatibility, use strftime instead of date_trunc
    day_column = func.strftime("%Y-%m-%d", ExpenseModel.date).label("day")
    query = (
        select(day_column, func.sum(ExpenseModel.amount).label("total"))
        .where(
            ExpenseModel.user_id == user_id,
            ExpenseModel.date >= start,
            ExpenseModel.date <= end,
        )
        .group_by(day_column)
        .order_by(day_column)
    )
    result = await db.execute(query)
    rows = result.all()
    return [
        ExpenseDaySchema(
            date=datetime.strptime(row.day, "%Y-%m-%d").date(),
            total=float(row.total)
        )
        for row in rows
    ]


async def get_period_summary(
    db: AsyncSession, user_id: int, start: datetime, end: datetime
) -> ExpensePeriodSummarySchema:
    total = await _fetch_total_value(db, user_id, start, end)
    daily_totals = await _fetch_daily_totals(db, user_id, start, end)
    return ExpensePeriodSummarySchema(total=total, daily_totals=daily_totals)


async def get_today_summary(
    db: AsyncSession, user_id: int
) -> ExpensePeriodSummarySchema:
    start, end = _today_bounds()
    return await get_period_summary(db, user_id, start, end)


async def get_month_summary(
    db: AsyncSession, user_id: int
) -> ExpensePeriodSummarySchema:
    start, end = _month_bounds()
    return await get_period_summary(db, user_id, start, end)


async def get_today_expenses(db: AsyncSession, user_id: int) -> List[ExpenseSchema]:
    """Get expenses for today."""
    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())
    query = select(ExpenseModel).where(
        ExpenseModel.user_id == user_id,
        ExpenseModel.date >= start,
        ExpenseModel.date <= end,
    )
    result = await db.execute(query)
    expenses = result.scalars().all()
    return [ExpenseSchema.from_orm(exp) for exp in expenses]


async def get_month_expenses(db: AsyncSession, user_id: int) -> List[ExpenseSchema]:
    """Get expenses from the start of the month to today."""
    today = date.today()
    start = datetime(today.year, today.month, 1)
    end = datetime.combine(today, datetime.max.time())
    query = select(ExpenseModel).where(
        ExpenseModel.user_id == user_id,
        ExpenseModel.date >= start,
        ExpenseModel.date <= end,
    )
    result = await db.execute(query)
    expenses = result.scalars().all()
    return [ExpenseSchema.from_orm(exp) for exp in expenses]
