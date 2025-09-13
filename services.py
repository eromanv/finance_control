from datetime import date, datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ExpenseModel
from schemas import ExpenseCreateSchema, ExpenseSchema


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
