from flask import Flask, render_template, redirect, url_for, request, flash, abort, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import event, text
import logging, os
from extensions import db, migrate, login_manager, csrf
from forms import LoginForm, RegisterForm, PostForm
from models import User, Post



# 파일 다운로드 import
#from flask import send_file, send_from_directory, safe_join, abort
from flask import send_file, send_from_directory, abort




app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate.init_app(app, db)
csrf.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# 설정된 쿼리 로깅을 위한 로거 설정
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 이벤트 리스너 설정 함수
def setup_event_listeners():
    @event.listens_for(db.engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        logging.info("Start Query: %s", statement)

    @event.listens_for(db.engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        logging.info("End Query: %s", statement)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # SQL Injection을 시연하기 위해 사용된 쿼리
        query = text(f"SELECT * FROM user WHERE email='{email}' AND password='{password}'")
        result = db.session.execute(query).fetchone()

        if result:
            user = User.query.get(result.id)
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', form=form)


@app.route('/download/')
def list_files():
    try:
        # 파일이 저장된 디렉터리 경로
        directory = os.path.join(app.root_path, 'files')

        # 디렉토리 내의 파일 리스트 가져오기
        files = os.listdir(directory)
        
        # 파일 리스트를 템플릿에 전달
        return render_template('files_list.html', files=files)
    except FileNotFoundError:
        abort(404)


@app.route('/download/<filename>')
def download_file(filename):
    try:
        # 파일이 저장된 디렉터리 경로
        directory = os.path.join(app.root_path, 'files')
        # 파일을 반환
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)




@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # 비밀번호를 평문으로 저장
        user = User(username=form.username.data, email=form.email.data, password=form.password.data)
        try:
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created!', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('Username already exists. Please choose a different username.', 'danger')
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        app.logger.info('Form validated successfully')
        post = Post(title=form.title.data, content=form.content.data, user_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        app.logger.info('Post saved to database')
        return redirect(url_for('index'))
    else:
        app.logger.warning('Form validation failed')
        for field_name, field in form._fields.items():
            value = field.data
            errors = form.errors.get(field_name, [])
            app.logger.warning(f"Field: {field_name}, Value: {value}, Errors: {errors}")
        app.logger.warning(f"CSRF token: {form.csrf_token.data}")

    posts = Post.query.all()
    app.logger.info(f"Loaded posts: {posts}")
    for post in posts:
        app.logger.info(f"Post: {post.title}, Content: {post.content}, Author: {post.author.username}")

    return render_template('index.html', form=form, posts=posts)

@app.route('/post/<int:post_id>', methods=['GET'])
@login_required
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post)

@app.route('/delete_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('index'))

@app.route('/users')
def users():
    user_id = request.args.get('Email')
    query = text(f"SELECT email, password FROM user WHERE id = {user_id}")
    result = db.session.execute(query).fetchall()
    return render_template_string('''
        <h1>Users</h1>
        <ul>
        {% for row in result %}
            <li>{{ row.email }} - {{ row.password }}</li>
        {% endfor %}
        </ul>
    ''', result=result)

if __name__ == '__main__':
    with app.app_context():
        setup_event_listeners()  # 애플리케이션 컨텍스트 내에서 이벤트 리스너 설정
    app.run(host="0.0.0.0", port=5000)

