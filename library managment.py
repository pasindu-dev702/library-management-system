from flask import Flask, request, jsonify, render_template, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = 'your-secret-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Books table
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    total_copies = db.Column(db.Integer, default=1)
    available_copies = db.Column(db.Integer, default=1)

# Users table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='member')  # admin or member

# Borrow records table
class BorrowRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    return_date = db.Column(db.DateTime, nullable=True)

@app.route('/')
def home():
    search_query = request.args.get('search', '')
    if search_query:
        books = Book.query.filter(
            (Book.title.contains(search_query)) | (Book.author.contains(search_query))
        ).all()
    else:
        books = Book.query.all()

    user_name = session.get('user_name')
    user_role = session.get('user_role')
    return render_template('index.html', books=books, user_name=user_name, user_role=user_role)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
from datetime import timedelta

@app.route('/borrow_book/<int:book_id>', methods=['POST'])
def borrow_book(book_id):
    if 'user_id' not in session:
        return redirect('/login')

    book = Book.query.get(book_id)

    if book and book.available_copies > 0:
        new_borrow = BorrowRecord(
            book_id=book.id,
            user_id=session['user_id'],
            due_date=datetime.utcnow() + timedelta(days=14)
        )
        book.available_copies -= 1
        db.session.add(new_borrow)
        db.session.commit()

    return redirect('/')

@app.route('/my_books')
def my_books():
    if 'user_id' not in session:
        return redirect('/login')

    records = BorrowRecord.query.filter_by(user_id=session['user_id'], return_date=None).all()

    borrowed_list = []
    for record in records:
        book = Book.query.get(record.book_id)
        borrowed_list.append({
            'record_id': record.id,
            'title': book.title,
            'author': book.author,
            'due_date': record.due_date
        })

    return render_template('my_books.html', borrowed_list=borrowed_list)

@app.route('/return_book/<int:record_id>', methods=['POST'])
def return_book(record_id):
    record = BorrowRecord.query.get(record_id)

    if record and record.return_date is None:
        record.return_date = datetime.utcnow()
        book = Book.query.get(record.book_id)
        book.available_copies += 1
        db.session.commit()

    return redirect('/my_books')

@app.route('/add_book', methods=['POST'])
def add_book_form():
    title = request.form['title']
    author = request.form['author']
    category = request.form.get('category', '')
    total_copies = int(request.form.get('total_copies', 1))

    new_book = Book(
        title=title,
        author=author,
        category=category,
        total_copies=total_copies,
        available_copies=total_copies
    )
    db.session.add(new_book)
    db.session.commit()
    return redirect('/')


@app.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    book = Book.query.get(book_id)
    if book:
        db.session.delete(book)
        db.session.commit()
    return redirect('/')


@app.route('/edit_book/<int:book_id>', methods=['GET'])
def edit_book_page(book_id):
    book = Book.query.get(book_id)
    return render_template('edit.html', book=book)


@app.route('/edit_book/<int:book_id>', methods=['POST'])
def edit_book(book_id):
    book = Book.query.get(book_id)
    book.title = request.form['title']
    book.author = request.form['author']
    book.category = request.form.get('category', '')
    book.total_copies = int(request.form.get('total_copies', 1))
    db.session.commit()
    return redirect('/')


@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = User(name=name, email=email, password=hashed_password, role='member')
    db.session.add(new_user)
    db.session.commit()

    return redirect('/login')

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    user = User.query.filter_by(email=email).first()

    if user and bcrypt.check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_role'] = user.role

        if user.role == 'admin':
            return redirect('/admin_dashboard')
        else:
            return redirect('/')
    else:
        return "Invalid email or password. <a href='/login'>Try again</a>"



@app.route('/books', methods=['GET'])
def get_books():
    books = Book.query.all()
    result = []
    for book in books:
        result.append({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'category': book.category,
            'available_copies': book.available_copies
        })
    return jsonify(result)


@app.route('/books', methods=['POST'])
def add_book():
    data = request.get_json()
    new_book = Book(
        title=data['title'],
        author=data['author'],
        category=data.get('category', ''),
        total_copies=data.get('total_copies', 1),
        available_copies=data.get('total_copies', 1)
    )
    db.session.add(new_book)
    db.session.commit()
    return jsonify({'message': 'Book added successfully!', 'id': new_book.id}), 201


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)