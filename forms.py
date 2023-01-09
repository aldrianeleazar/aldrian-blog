from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, URL, Email, Length
from flask_ckeditor import CKEditorField


##WTForm
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    name = StringField("Name", validators=[DataRequired()])
    signup = SubmitField("SIGN ME UP!")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password",  validators=[DataRequired()])
    login = SubmitField("LET ME IN!")


class CommentForm(FlaskForm):
    comment = CKEditorField("Comment", validators=[DataRequired()])
    submit_comment = SubmitField("SUBMIT COMMENT")


class SendMessage(FlaskForm):
    name = StringField("", validators=[DataRequired()], render_kw={"placeholder": "Name"})
    email = StringField("", validators=[DataRequired(), Email()], render_kw={"placeholder": "Email"})
    number = StringField("", render_kw={"placeholder": "Phone Number(Optional)"})
    message = TextAreaField("", validators=[DataRequired()], render_kw={"placeholder": "Message"})
    send = SubmitField("Send")