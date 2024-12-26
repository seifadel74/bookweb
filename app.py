from flask import Flask, render_template, request, redirect, url_for, flash, abort, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from config import Config
from PIL import Image, ImageDraw, ImageFont
import io
from sqlalchemy import Table

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///library.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Association table
book_categories = db.Table('book_categories',
    db.Column('book_id', db.Integer, db.ForeignKey('book.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    books = db.relationship('Book', backref='added_by', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    genre = db.Column(db.String(100))
    description = db.Column(db.Text)
    cover_image = db.Column(db.String(200))
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_available = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    categories = db.relationship('Category', 
                               secondary=book_categories,
                               backref=db.backref('books', lazy='dynamic'))

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful!')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    books = Book.query.order_by(Book.added_date.desc()).all()
    return render_template('index.html', books=books)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        genre = request.form['genre']
        description = request.form['description']
        
        book = Book(
            title=title,
            author=author,
            genre=genre,
            description=description,
            user_id=current_user.id
        )

        if 'cover' in request.files:
            file = request.files['cover']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                book.cover_image = filename

        db.session.add(book)
        db.session.commit()
        flash('Book added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_book.html')

@app.route('/search')
def search():
    query = request.args.get('query', '').lower()
    if query:
        results = Book.query.filter(
            db.or_(
                Book.title.ilike(f'%{query}%'),
                Book.author.ilike(f'%{query}%')
            )
        ).all()
    else:
        results = []
    return render_template('search.html', results=results, query=query)

@app.route('/toggle_availability/<int:book_id>')
@login_required
def toggle_availability(book_id):
    book = Book.query.get_or_404(book_id)
    if current_user.is_admin or book.user_id == current_user.id:
        book.is_available = not book.is_available
        db.session.commit()
        status = "available" if book.is_available else "checked out"
        flash(f'Book is now {status}!', 'success')
    else:
        flash('You do not have permission to perform this action.', 'error')
    return redirect(url_for('index'))

@app.route('/static/book_covers/default_cover.png')
def default_cover():
    # Create a new image with a white background
    img = Image.new('RGB', (400, 600), color='white')
    d = ImageDraw.Draw(img)
    
    # Add text
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    d.text((100, 250), "No Cover\nAvailable", font=font, fill='gray', align='center')
    
    # Save to bytes
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

def add_sample_books(admin_user_id):
    # First, create categories
    categories_data = [
        {'name': 'Classic Literature', 'description': 'Timeless works that have influenced generations'},
        {'name': 'Fantasy', 'description': 'Stories involving magic and supernatural phenomena'},
        {'name': 'Science Fiction', 'description': 'Speculative fiction focusing on scientific advancement'},
        {'name': 'Mystery & Thriller', 'description': 'Suspenseful stories of crime and intrigue'},
        {'name': 'Romance', 'description': 'Stories centered around love and relationships'},
        {'name': 'Horror', 'description': 'Stories designed to frighten and unsettle'},
        {'name': 'Young Adult', 'description': 'Literature aimed at teenage readers'},
        {'name': 'Non-Fiction', 'description': 'Factual works based on real events and topics'},
        {'name': 'Historical Fiction', 'description': 'Fiction set in the past'},
        {'name': 'Contemporary Fiction', 'description': 'Modern stories set in present times'}
    ]

    categories = {}
    for cat_data in categories_data:
        category = Category.query.filter_by(name=cat_data['name']).first()
        if not category:
            category = Category(name=cat_data['name'], description=cat_data['description'])
            db.session.add(category)
            db.session.commit()
        categories[cat_data['name']] = category

    sample_books = [
        {
            'title': 'Pride and Prejudice',
            'author': 'Jane Austen',
            'genre': 'Classic Literature',
            'description': 'A masterpiece of regency romance.',
            'cover': 'pride_prejudice.jpg',
            'categories': ['Classic Literature', 'Romance']
        },
        {
            'title': 'The Hobbit',
            'author': 'J.R.R. Tolkien',
            'genre': 'Fantasy',
            'description': 'A fantasy novel about Bilbo Baggins\' journey.',
            'cover': 'hobbit.jpg',
            'categories': ['Fantasy', 'Classic Literature']
        },
        {
            'title': 'Dune',
            'author': 'Frank Herbert',
            'genre': 'Science Fiction',
            'description': 'A masterpiece of science fiction.',
            'cover': 'dune.jpg',
            'categories': ['Science Fiction']
        },
        {
            'title': 'The Silent Patient',
            'author': 'Alex Michaelides',
            'genre': 'Thriller',
            'description': 'A psychological thriller about a woman\'s act of violence.',
            'cover': 'silent_patient.jpg',
            'categories': ['Mystery & Thriller']
        },
        {
            'title': 'Project Hail Mary',
            'author': 'Andy Weir',
            'genre': 'Science Fiction',
            'description': 'An astronaut wakes up alone on a spacecraft.',
            'cover': 'hail_mary.jpg',
            'categories': ['Science Fiction']
        },
        {
            'title': 'The Midnight Library',
            'author': 'Matt Haig',
            'genre': 'Contemporary Fiction',
            'description': 'A library between life and death.',
            'cover': 'midnight_library.jpg',
            'categories': ['Contemporary Fiction', 'Fantasy']
        },
        {
            'title': 'Mexican Gothic',
            'author': 'Silvia Moreno-Garcia',
            'genre': 'Horror',
            'description': 'A gothic horror set in 1950s Mexico.',
            'cover': 'mexican_gothic.jpg',
            'categories': ['Horror', 'Historical Fiction']
        },
        {
            'title': 'The Seven Husbands of Evelyn Hugo',
            'author': 'Taylor Jenkins Reid',
            'genre': 'Historical Fiction',
            'description': 'The story of a fictional Hollywood star.',
            'cover': 'evelyn_hugo.jpg',
            'categories': ['Historical Fiction', 'Romance']
        },
        {
            'title': 'Atomic Habits',
            'author': 'James Clear',
            'genre': 'Non-Fiction',
            'description': 'A guide to building good habits.',
            'cover': 'atomic_habits.jpg',
            'categories': ['Non-Fiction']
        },
        {
            'title': 'Six of Crows',
            'author': 'Leigh Bardugo',
            'genre': 'Young Adult',
            'description': 'A heist story set in a fantasy world.',
            'cover': 'six_of_crows.jpg',
            'categories': ['Young Adult', 'Fantasy']
        },
        {
            'title': 'The Thursday Murder Club',
            'author': 'Richard Osman',
            'genre': 'Mystery',
            'description': 'Four retirees meet weekly to solve cold cases.',
            'cover': 'thursday_club.jpg',
            'categories': ['Mystery & Thriller']
        },
        {
            'title': 'The Invisible Life of Addie LaRue',
            'author': 'V.E. Schwab',
            'genre': 'Fantasy',
            'description': 'A woman makes a Faustian bargain.',
            'cover': 'addie_larue.jpg',
            'categories': ['Fantasy', 'Historical Fiction']
        },
        {
            'title': 'Klara and the Sun',
            'author': 'Kazuo Ishiguro',
            'genre': 'Science Fiction',
            'description': 'An AI observes human behavior.',
            'cover': 'klara_sun.jpg',
            'categories': ['Science Fiction', 'Contemporary Fiction']
        },
        {
            'title': 'The Paris Apartment',
            'author': 'Lucy Foley',
            'genre': 'Mystery',
            'description': 'A woman arrives in Paris to find her brother missing.',
            'cover': 'paris_apartment.jpg',
            'categories': ['Mystery & Thriller']
        },
        {
            'title': 'Beach Read',
            'author': 'Emily Henry',
            'genre': 'Romance',
            'description': 'Two writers switch genres for a summer.',
            'cover': 'beach_read.jpg',
            'categories': ['Romance', 'Contemporary Fiction']
        }
    ]

    for book_data in sample_books:
        if not Book.query.filter_by(title=book_data['title']).first():
            book = Book(
                title=book_data['title'],
                author=book_data['author'],
                genre=book_data['genre'],
                description=book_data['description'],
                cover_image=book_data['cover'],
                user_id=admin_user_id
            )
            # Add categories to the book
            for category_name in book_data['categories']:
                book.categories.append(categories[category_name])
            db.session.add(book)
    
    db.session.commit()

# Create database tables
with app.app_context():
    db.create_all()
    # Create admin user if it doesn't exist
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('admin123')  # Change this password!
        db.session.add(admin)
        db.session.commit()
        # Add sample books under admin user
        add_sample_books(admin.id)

@app.route('/categories')
def categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

@app.route('/category/<int:category_id>')
def category_books(category_id):
    category = Category.query.get_or_404(category_id)
    return render_template('category_books.html', category=category)

if __name__ == '__main__':
    app.run(debug=True) 