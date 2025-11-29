from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel


class CategoryENUM(str, Enum):
    FASTFOOD = "фастфуд - съел сам"
    FOOD = "еда"
    CHILD = "ребенку"
    ENTERTAINMENT = "развлечения"
    KINDERGARTEN = "садик"
    UTILITIES = "коммунальные услуги"
    TRANSPORT = "транспорт"
    SCOOTER = "самокат"
    CLOTHING = "одежда"
    RESTAURANTS = "рестораны"
    PHARMACY = "аптека"
    EXTRA_SNACKS = "перекусы лишние"
    CREDITS = "кредиты"
    CARSHARING = "каршеринг"
    MEDICINE = "медицина"
    SUBSCRIPTIONS = "подписки"


class ExpenseCreateSchema(BaseModel):
    user_id: int
    category: CategoryENUM
    amount: float


class ExpenseSchema(BaseModel):
    id: int
    user_id: int
    category: CategoryENUM
    amount: float
    date: datetime

    class Config:
        from_attributes = True


class ExpenseDaySchema(BaseModel):
    date: date
    total: float


class CategorySummarySchema(BaseModel):
    category: str
    total: float


class ExpensePeriodSummarySchema(BaseModel):
    total: float
    daily_totals: list[ExpenseDaySchema]
    category_breakdown: list[CategorySummarySchema]
