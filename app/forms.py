from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, IntegerField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Length, URL
from app.models import User
from flask import request

class SendMessageForm(FlaskForm):
    receiver = StringField('To', validators=[DataRequired()])
    body = StringField('Body', validators=[DataRequired(), Length(min=1,max=140)])
    submit = SubmitField('Submit')

class EditItemForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    image = StringField('image', validators=[DataRequired(), URL()])
    body = TextAreaField('Body', validators=[DataRequired(), Length(min=1,max=140)])
    submit = SubmitField('Submit')

class SearchForm(FlaskForm):
    q = StringField('search', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)

class CommentForm(FlaskForm):
    comment = TextAreaField('Comment', validators=[DataRequired(), Length(min=1,max=140)])
    score = SelectField('Score', choices=[('1','1'),('2','2'),('3','3'),('4','4'),('5','5')], validators=[DataRequired()]); 
    submit = SubmitField('Submit')

class PostForm(FlaskForm):
    post = TextAreaField('Post', validators=[DataRequired(), Length(min=1,max=140)])
    submit = SubmitField('Submit')

class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    introduction = TextAreaField('Introduction', validators=[Length(min=0, max=140)])
    avatar = FileField('Avatar')
    submit = SubmitField('Submit')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    passwordrep = PasswordField('Repeat Password', validators=[DataRequired(),
        EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('This username already exists.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('This email have been used.')

