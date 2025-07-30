from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from typing import List, Optional, Dict
from datetime import date
from sqlalchemy import func, extract
import logging

# Assuming schemas.py contains the Pydantic models.
# You would need to add the new response models there, for example:
#
# class CategoryTotal(BaseModel):
#     category: str
#     total: float
#
# class MonthlySummary(BaseModel):
#     year: int
#     month: int
#     total: float
#
from .. import models, schemas
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
)

def handle_db_error(func):
    """Decorator to handle database errors consistently"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OperationalError as e:
            logger.error(f"Database connection error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=503, 
                detail="Database connection unavailable. Please try again later."
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    return wrapper

@router.post("/", response_model=schemas.Expense)
@handle_db_error
def create_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    try:
        db_expense = models.Expense(**expense.model_dump())
        db.add(db_expense)
        db.commit()
        db.refresh(db_expense)
        return db_expense
    except OperationalError as e:
        db.rollback()
        logger.error(f"Database error creating expense: {e}")
        raise HTTPException(
            status_code=503, 
            detail="Database connection unavailable. Please try again later."
        )

@router.get("/", response_model=List[schemas.Expense])
@handle_db_error
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
@handle_db_error
def read_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense

@router.put("/{expense_id}", response_model=schemas.Expense)
@handle_db_error
def update_expense(expense_id: int, expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    try:
        db_expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
        if db_expense is None:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        for key, value in expense.model_dump().items():
            setattr(db_expense, key, value)
        
        db.commit()
        db.refresh(db_expense)
        return db_expense
    except OperationalError as e:
        db.rollback()
        logger.error(f"Database error updating expense: {e}")
        raise HTTPException(
            status_code=503, 
            detail="Database connection unavailable. Please try again later."
        )

@router.delete("/{expense_id}")
@handle_db_error
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    try:
        expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
        if expense is None:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        db.delete(expense)
        db.commit()
        return {"message": "Expense deleted successfully"}
    except OperationalError as e:
        db.rollback()
        logger.error(f"Database error deleting expense: {e}")
        raise HTTPException(
            status_code=503, 
            detail="Database connection unavailable. Please try again later."
        )

# --- REFACTORED AND NEW ENDPOINTS ---

@router.get("/stats/summary", response_model=schemas.ExpenseStatistics)
@handle_db_error
def get_expense_statistics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Provides summary statistics for expenses, calculated efficiently at the database level.
    Allows filtering by a date range.
    """
    query = db.query(models.Expense)
    if start_date:
        query = query.filter(models.Expense.date >= start_date)
    if end_date:
        query = query.filter(models.Expense.date <= end_date)
    
    # Calculate total, average, and highest expense
    stats = query.with_entities(
        func.sum(models.Expense.amount).label("total"),
        func.avg(models.Expense.amount).label("average"),
        func.max(models.Expense.amount).label("highest")
    ).first()

    if not stats or stats.total is None:
        return {
            "total_expenses": 0.0,
            "average_expense": 0.0,
            "highest_expense": 0.0,
            "most_common_category": "None"
        }

    # Find the most common category
    category_query = query.with_entities(models.Expense.category, func.count(models.Expense.id).label('count')) \
                          .group_by(models.Expense.category) \
                          .order_by(func.count(models.Expense.id).desc()) \
                          .first()

    return {
        "total_expenses": stats.total or 0.0,
        "average_expense": stats.average or 0.0,
        "highest_expense": stats.highest or 0.0,
        "most_common_category": category_query[0] if category_query else "None"
    }

@router.get("/categories/all", response_model=Dict[str, List[str]])
@handle_db_error
def get_all_categories(db: Session = Depends(get_db)):
    """
    Retrieves a list of all unique expense categories.
    """
    categories = db.query(models.Expense.category).distinct().all()
    return {"categories": [cat[0] for cat in categories if cat[0]]}

@router.get("/stats/by-category", response_model=List[schemas.CategoryTotal])
@handle_db_error
def get_spending_by_category(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Returns the total spending for each category within an optional date range,
    ordered from the highest total to the lowest.
    """
    query = db.query(
        models.Expense.category,
        func.sum(models.Expense.amount).label('total')
    ).filter(models.Expense.category.isnot(None))

    if start_date:
        query = query.filter(models.Expense.date >= start_date)
    if end_date:
        query = query.filter(models.Expense.date <= end_date)

    results = query.group_by(models.Expense.category).order_by(func.sum(models.Expense.amount).desc()).all()
    
    return [{"category": category, "total": total} for category, total in results]

@router.get("/reports/monthly", response_model=List[schemas.MonthlySummary])
@handle_db_error
def get_monthly_summary(
    year: Optional[int] = Query(None, description="Filter by a specific year"),
    db: Session = Depends(get_db)
):
    """
    Provides a monthly summary of total expenses, grouped by year and month.
    """
    query = db.query(
        extract('year', models.Expense.date).label('year'),
        extract('month', models.Expense.date).label('month'),
        func.sum(models.Expense.amount).label('total')
    )

    if year:
        query = query.filter(extract('year', models.Expense.date) == year)

    results = query.group_by(
        extract('year', models.Expense.date),
        extract('month', models.Expense.date)
    ).order_by(
        extract('year', models.Expense.date).desc(),
        extract('month', models.Expense.date).desc()
    ).all()

    return [{"year": y, "month": m, "total": t} for y, m, t in results]