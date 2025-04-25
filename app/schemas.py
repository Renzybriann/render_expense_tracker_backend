from pydantic import BaseModel, Field, validator
from datetime import date
from typing import Optional

class ExpenseBase(BaseModel):
    title: str
    amount: float = Field(gt=0)
    date: date
    category: str
    description: Optional[str] = None

class ExpenseCreate(ExpenseBase):
    pass

class Expense(ExpenseBase):
    id: int
    
    class Config:
        orm_mode = True
        from_attributes = True

class ExpenseStatistics(BaseModel):
    total_expenses: float
    average_expense: float
    highest_expense: float
    most_common_category: str