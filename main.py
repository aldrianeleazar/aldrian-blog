from flask import Flask, render_template, redirect, url_for, flash, abort, request, jsonify
from functools import wraps
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm, EditCommentForm, SendMessage
from flask_gravatar import Gravatar
import smtplib
import os

my_email = os.getenv("EMAIL")
my_password = os.getenv("PASSWORD")

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("APP_SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    blog_comments = relationship("Comment", back_populates="parent_post")

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="blog_comments")
    text = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

db.create_all()


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route("/all_user")
def get_all_user():
    api_key_auth = request.args.get("guest-api-key")
    users = User.query.all()
    if api_key_auth == "Admin_api_key_only":
        return jsonify(users=[user.to_dict() for user in users]), 200
    else:
        return jsonify(response={"error": "Sorry, only admins can access this. Make sure you have the correct admin api_key"}), 403


@app.route("/all_post")
def get_all_post():
    api_key_auth = request.args.get("guest-api-key")
    posts = BlogPost.query.all()
    if api_key_auth == "Admin_api_key_only":
        return jsonify(posts=[post.to_dict() for post in posts]), 200
    else:
        return jsonify(response={"error": "Sorry, only admins can access this. Make sure you have the correct admin api_key"}), 403


@app.route("/all_comment")
def get_all_comment():
    api_key_auth = request.args.get("guest-api-key")
    comments = Comment.query.all()
    if api_key_auth == "Admin_api_key_only":
        return jsonify(comments=[comment.to_dict() for comment in comments]), 200
    else:
        return jsonify(response={"error": "Sorry, only admins can access this. Make sure you have the correct admin api_key"}), 403


@app.route('/register', methods=["GET", "POST"])
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        new_user = User()
        new_user.email = register_form.email.data
        hash_password = generate_password_hash(password=register_form.password.data)
        new_user.password = hash_password
        new_user.name = register_form.name.data.title()
        find_email = User.query.filter_by(email=new_user.email).first()
        if find_email:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        else:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=register_form)


@app.route('/login', methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = login_form.email.data
        password = login_form.password.data

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(pwhash=user.password, password=password):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash('Password incorrect, please try again.')
                return redirect(url_for('login'))
        else:
            flash('The email does not exist, please try again.')
            return redirect(url_for('login'))

    return render_template("login.html", form=login_form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                text=form.comment.data,
                post_id=post_id,
                author_id=current_user.id
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(f"/post/{post_id}")
        else:
            flash('You need to login or register to comment.')
            return redirect(url_for('login'))
    return render_template("post.html", post=requested_post, form=form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    send_form = SendMessage()
    if send_form.validate_on_submit():
        name = send_form.name.data
        email = send_form.email.data
        if send_form.number.data == '':
            phone = 'No data input'
        else:
            phone = send_form.number.data
        message = send_form.message.data
        with smtplib.SMTP("smtp.gmail.com", 587) as connection:
            connection.starttls()
            connection.login(user=my_email, password=my_password)
            connection.sendmail(
                from_addr=my_email,
                to_addrs=my_email,
                msg=f"Subject:Msg From Blog\n"
                    f"\nName: {name}"
                    f"\nEmail: {email}"
                    f"\nPhone: {phone}"
                    f"\nMessage: {message}"
            )
        flash('Your message has been successfully sent.')
        return redirect(url_for('contact'))
    return render_template("contact.html", form=send_form)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/edit_comment", methods=["GET", "POST"])
@login_required
def edit_your_comment():
    post_id = request.args.get("post_id")
    requested_post = BlogPost.query.get(post_id)
    comment_id = request.args.get("comment_id")
    comment = Comment.query.get(comment_id)
    edit_form = EditCommentForm(
        edit_comment=comment.text
    )
    if edit_form.validate_on_submit():
        comment.text = edit_form.edit_comment.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post_id))
    return render_template("edit-comment.html", post=requested_post, com_id=int(comment_id), form=edit_form)


@app.route("/delete_comment", methods=["GET", "POST"])
@login_required
def delete_your_comment():
    post_id = request.args.get("post_id")
    comment_id = request.args.get("comment_id")
    delete_comment = Comment.query.get(comment_id)
    db.session.delete(delete_comment)
    db.session.commit()
    return redirect(url_for("show_post", post_id=post_id))

if __name__ == "__main__":
    app.run(host='192.168.254.126', port=5000, debug=True)
