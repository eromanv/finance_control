from datetime import date, datetime
from typing import List, Tuple

from models import ExpenseModel
from schemas import (CategorySummarySchema, ExpenseCreateSchema,
                     ExpenseDaySchema, ExpensePeriodSummarySchema,
                     ExpenseSchema)
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
    day_column = _build_daily_group_expr(db).label("day")
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
        ExpenseDaySchema(date=_normalize_day_value(row.day), total=float(row.total))
        for row in rows
    ]


def _build_daily_group_expr(db: AsyncSession):
    bind = getattr(db, "bind", None)
    dialect_name = None
    if bind is not None and getattr(bind, "dialect", None) is not None:
        dialect_name = bind.dialect.name
    if dialect_name == "sqlite":
        return func.strftime("%Y-%m-%d", ExpenseModel.date)
    if dialect_name == "postgresql":
        return func.date_trunc("day", ExpenseModel.date)
    return func.date(ExpenseModel.date)


def _normalize_day_value(value):
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d").date()
    return value


async def _fetch_category_breakdown(
    db: AsyncSession, user_id: int, start: datetime, end: datetime
) -> list[CategorySummarySchema]:
    query = (
        select(
            ExpenseModel.category,
            func.sum(ExpenseModel.amount).label("total"),
        )
        .where(
            ExpenseModel.user_id == user_id,
            ExpenseModel.date >= start,
            ExpenseModel.date <= end,
        )
        .group_by(ExpenseModel.category)
        .order_by(func.sum(ExpenseModel.amount).desc())
    )
    result = await db.execute(query)
    rows = result.all()
    return [
        CategorySummarySchema(category=row.category or "Неизвестная", total=float(row.total))
        for row in rows
    ]


async def get_period_summary(
    db: AsyncSession, user_id: int, start: datetime, end: datetime
) -> ExpensePeriodSummarySchema:
    total = await _fetch_total_value(db, user_id, start, end)
    daily_totals = await _fetch_daily_totals(db, user_id, start, end)
    category_breakdown = await _fetch_category_breakdown(db, user_id, start, end)
    return ExpensePeriodSummarySchema(
        total=total,
        daily_totals=daily_totals,
        category_breakdown=category_breakdown,
    )


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
