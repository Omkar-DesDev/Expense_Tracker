from sqlalchemy import func
from app.models import Expense
from app import db

def total_expenses_for_user(user_id):
    res = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)).filter(Expense.user_id==user_id).scalar()
    return float(res or 0.0)

def monthly_totals(user_id):
    rows = db.session.query(func.strftime('%Y-%m', Expense.date).label('ym'), func.coalesce(func.sum(Expense.amount), 0.0))\
        .filter(Expense.user_id==user_id)\
        .group_by('ym')\
        .order_by('ym').all()
    return [{'month': r[0], 'total': float(r[1])} for r in rows]

def category_sums(user_id):
    rows = db.session.query(Expense.category, func.coalesce(func.sum(Expense.amount),0.0))\
        .filter(Expense.user_id==user_id)\
        .group_by(Expense.category).all()
    return [{'category': r[0], 'total': float(r[1])} for r in rows]
