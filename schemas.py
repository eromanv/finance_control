from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class CategoryENUM(str, Enum):
    FASTFOOD = "фастфуд"
    FOOD = "еда"
    CHILD = "ребенку"
    ENTERTAINMENT = "развлечения"
    KINDERGARTEN = "садик"
    UTILITIES = "коммунальные услуги"
    TRANSPORT = "транспорт"
    SCOOTER = "самокат"
    CLOTHING = "одежда"
    RESTAURANTS = "рестораны"


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
