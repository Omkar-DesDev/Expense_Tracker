import io
import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, make_response
from flask_login import current_user, login_user, logout_user, login_required
from app import db
from app.models import User, Expense
from app.forms import RegisterForm, LoginForm, ExpenseForm
from app.utils import total_expenses_for_user, monthly_totals, category_sums
import pandas as pd
from markupsafe import Markup

# reportlab for PDF generation
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet

auth_bp = Blueprint('auth', __name__)
main_bp = Blueprint('main', __name__)
expense_bp = Blueprint('expense', __name__, url_prefix='/expenses')


# ----------------------
# AUTH ROUTES
# ----------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RegisterForm()
    if form.validate_on_submit():
        existing = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
        if existing:
            flash('Username or email already exists', 'danger')
            return render_template('register.html', form=form)
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter((User.username == form.username.data) | (User.email == form.username.data)).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username/email or password', 'danger')
            return render_template('login.html', form=form)
        login_user(user)
        flash('Logged in successfully', 'success')
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.dashboard'))
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))


# ----------------------
# MAIN ROUTES
# ----------------------
@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    q = Expense.query.filter_by(user_id=current_user.id)
    category = request.args.get('category')
    start = request.args.get('start')
    end = request.args.get('end')
    sort = request.args.get('sort')

    if category:
        q = q.filter(Expense.category == category)
    if start:
        # try to parse ISO date string, otherwise use raw
        try:
            start_date = datetime.fromisoformat(start).date()
            q = q.filter(Expense.date >= start_date)
        except Exception:
            q = q.filter(Expense.date >= start)
    if end:
        try:
            end_date = datetime.fromisoformat(end).date()
            q = q.filter(Expense.date <= end_date)
        except Exception:
            q = q.filter(Expense.date <= end)

    if sort == 'amount_asc':
        q = q.order_by(Expense.amount.asc())
    elif sort == 'amount_desc':
        q = q.order_by(Expense.amount.desc())
    elif sort == 'date_asc':
        q = q.order_by(Expense.date.asc())
    else:
        q = q.order_by(Expense.date.desc())

    expenses = q.all()

    # total of all user expenses (unfiltered)
    total = total_expenses_for_user(current_user.id)
    # analytics helpers (lists of dicts)
    monthly = monthly_totals(current_user.id)
    categories = category_sums(current_user.id)

    # JSON-safe strings for JS (dates converted to str by default=str)
    monthly_json = Markup(json.dumps(monthly, default=str))
    categories_json = Markup(json.dumps(categories, default=str))

    # visible_total = sum of currently displayed (filtered) expenses
    visible_total = float(sum([e.amount for e in expenses]) if expenses else 0.0)

    return render_template(
        'dashboard.html',
        expenses=expenses,
        total=total,
        monthly=monthly,
        categories=categories,
        visible_total=visible_total,
        monthly_json=monthly_json,
        categories_json=categories_json
    )


# ----------------------
# EXPORT ROUTE
# ----------------------
@main_bp.route('/export')
@login_required
def export_expenses():
    """
    Export current user's (filtered) expenses.
    Query params:
      - format=csv|xlsx|pdf
      - category, start (YYYY-MM-DD), end (YYYY-MM-DD), sort
    """
    fmt = (request.args.get('format') or 'csv').lower()

    # Build same filtered query as dashboard
    q = Expense.query.filter_by(user_id=current_user.id)
    category = request.args.get('category')
    start = request.args.get('start')
    end = request.args.get('end')
    sort = request.args.get('sort')

    if category:
        q = q.filter(Expense.category == category)
    if start:
        try:
            start_date = datetime.fromisoformat(start).date()
            q = q.filter(Expense.date >= start_date)
        except Exception:
            q = q.filter(Expense.date >= start)
    if end:
        try:
            end_date = datetime.fromisoformat(end).date()
            q = q.filter(Expense.date <= end_date)
        except Exception:
            q = q.filter(Expense.date <= end)

    if sort == 'amount_asc':
        q = q.order_by(Expense.amount.asc())
    elif sort == 'amount_desc':
        q = q.order_by(Expense.amount.desc())
    elif sort == 'date_asc':
        q = q.order_by(Expense.date.asc())
    else:
        q = q.order_by(Expense.date.desc())

    expenses = q.all()

    # Build rows list
    rows = []
    for e in expenses:
        rows.append({
            'Date': e.date.strftime('%Y-%m-%d') if e.date else '',
            'Title': e.title or '',
            'Category': e.category or '',
            'Amount': float(e.amount) if e.amount is not None else 0.0,
            'Description': e.description or ''
        })

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_base = f"expenses_{current_user.username}_{timestamp}"

    # CSV export
    if fmt == 'csv':
        df = pd.DataFrame(rows)
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        csv_buf.seek(0)
        return send_file(
            io.BytesIO(csv_buf.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"{filename_base}.csv"
        )

    # Excel export (.xlsx)
    elif fmt in ('xlsx', 'excel'):
        df = pd.DataFrame(rows)
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Expenses')
        out.seek(0)
        return send_file(
            out,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"{filename_base}.xlsx"
        )

    # PDF export
    elif fmt == 'pdf':
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        title = Paragraph(f"Expenses for {current_user.username}", styles['Heading2'])
        elements.append(title)
        elements.append(Spacer(1, 12))

        if rows:
            table_data = [['Date', 'Title', 'Category', 'Amount', 'Description']]
            for r in rows:
                table_data.append([r['Date'], r['Title'], r['Category'], f"{r['Amount']:.2f}", r['Description']])
            t = Table(table_data, repeatRows=1, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("No expenses found for the selected filters.", styles['Normal']))

        doc.build(elements)
        buffer.seek(0)
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"{filename_base}.pdf"
        )

    else:
        return make_response("Unsupported format", 400)


# ----------------------
# EXPENSE CRUD
# ----------------------
@expense_bp.route('/')
@login_required
def list_expenses():
    return redirect(url_for('main.dashboard'))


@expense_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_expense():
    form = ExpenseForm()
    if form.validate_on_submit():
        exp = Expense(
            title=form.title.data,
            category=form.category.data,
            amount=form.amount.data,
            date=form.date.data,
            description=form.description.data,
            user_id=current_user.id
        )
        db.session.add(exp)
        db.session.commit()
        flash('Expense added', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('expenses/create_edit.html', form=form)


@expense_bp.route('/<int:expense_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    exp = Expense.query.get_or_404(expense_id)
    if exp.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('main.dashboard'))
    form = ExpenseForm(obj=exp)
    if form.validate_on_submit():
        form.populate_obj(exp)
        db.session.commit()
        flash('Expense updated', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('expenses/create_edit.html', form=form)


@expense_bp.route('/<int:expense_id>/delete', methods=['POST'])
@login_required
def delete_expense(expense_id):
    exp = Expense.query.get_or_404(expense_id)
    if exp.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('main.dashboard'))
    db.session.delete(exp)
    db.session.commit()
    flash('Expense deleted', 'info')
    return redirect(url_for('main.dashboard'))
