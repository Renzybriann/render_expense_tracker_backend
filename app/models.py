from sqlalchemy import Column, Integer, String, Float, Date, Text
from datetime import date
from .database import Base

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    amount = Column(Float)
    date = Column(Date, default=date.today)
    category = Column(String, index=True)
    description = Column(Text, nullable=True)