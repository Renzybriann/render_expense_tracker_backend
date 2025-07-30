from pydantic import BaseModel, Field, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)
    
    id: int

class ExpenseStatistics(BaseModel):
    total_expenses: float
    average_expense: float
    highest_expense: float
    most_common_category: str