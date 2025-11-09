from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, TextAreaField, SelectField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange

CATEGORIES = ['Food', 'Transport', 'Shopping', 'Bills', 'Entertainment', 'Other']

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3,64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(6,128)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ExpenseForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=140)])
    category = SelectField('Category', choices=[(c,c) for c in CATEGORIES], validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0)])
    date = DateField('Date', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Save')
