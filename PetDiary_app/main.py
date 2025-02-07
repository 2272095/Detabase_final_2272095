import os
from dotenv import load_dotenv # type: ignore
from werkzeug.utils import secure_filename
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user

# .envファイルから環境変数を読み込む
load_dotenv()

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this in production!
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# PostgreSQLデータベースの設定
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemyオブジェクトの初期化
db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# モデルの定義
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

class DiaryEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('entries', lazy=True))
    image_filename = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<DiaryEntry {self.date} - {self.content[:20]}>'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:  # Replace with proper password hashing
            login_user(user)
            return redirect(url_for('diary'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return 'Username already exists'
        # Create a new user
        new_user = User(username=username, password=password)  # Replace with proper password hashing
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/diary')
@login_required
def diary():
    entries = DiaryEntry.query.filter_by(user_id=current_user.id).all()
    return render_template('diary.html', entries=entries)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'image' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['image']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            filename = None
        date = request.form['date']
        content = request.form['content']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = None
        new_entry = DiaryEntry(date=date, content=content, user_id=current_user.id, image_filename=filename)
        db.session.add(new_entry)
        db.session.commit()
        return redirect(url_for('diary'))
    return render_template('add.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create a default user if one doesn't exist
        if not User.query.filter_by(username='test').first():
            default_user = User(username='test', password='test')  # Replace with proper password hashing
            db.session.add(default_user)
            db.session.commit()
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
