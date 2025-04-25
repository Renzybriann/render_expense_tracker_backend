from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from sqlalchemy import func
from collections import Counter

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
)

@router.post("/", response_model=schemas.Expense)
def create_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    db_expense = models.Expense(**expense.model_dump())
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@router.get("/", response_model=List[schemas.Expense])
def read_expenses(
    skip: int = 0, 
    limit: int = 100,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Expense)
    
    if category:
        query = query.filter(models.Expense.category == category)
    
    if start_date:
        query = query.filter(models.Expense.date >= start_date)
    
    if end_date:
        query = query.filter(models.Expense.date <= end_date)
        
    return query.order_by(models.Expense.date.desc()).offset(skip).limit(limit).all()

@router.get("/{expense_id}", response_model=schemas.Expense)
def read_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense

@router.put("/{expense_id}", response_model=schemas.Expense)
def update_expense(expense_id: int, expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    db_expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    for key, value in expense.model_dump().items():
        setattr(db_expense, key, value)
    
    db.commit()
    db.refresh(db_expense)
    return db_expense

@router.delete("/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted successfully"}

@router.get("/stats/summary", response_model=schemas.ExpenseStatistics)
def get_expense_statistics(db: Session = Depends(get_db)):
    expenses = db.query(models.Expense).all()
    
    if not expenses:
        return {
            "total_expenses": 0.0,
            "average_expense": 0.0,
            "highest_expense": 0.0,
            "most_common_category": "None"
        }
    
    total = sum(expense.amount for expense in expenses)
    average = total / len(expenses)
    highest = max(expense.amount for expense in expenses)
    
    # Find most common category
    categories = [expense.category for expense in expenses]
    most_common = Counter(categories).most_common(1)[0][0]
    
    return {
        "total_expenses": total,
        "average_expense": average,
        "highest_expense": highest,
        "most_common_category": most_common
    }

@router.get("/categories/all")
def get_all_categories(db: Session = Depends(get_db)):
    categories = db.query(models.Expense.category).distinct().all()
    return {"categories": [cat[0] for cat in categories]}