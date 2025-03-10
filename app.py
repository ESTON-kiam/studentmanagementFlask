from flask import Flask, render_template, request, redirect, url_for, flash
from flask_pymongo import PyMongo
from flask_mail import Mail, Message
from bson.objectid import ObjectId
import bcrypt  #used to hash passwords

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# MongoDB configuration
app.config['MONGO_URI'] = 'mongodb://localhost:27017/contact_db'
mongo = PyMongo(app)

# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-password'
mail = Mail(app)


# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = mongo.db.users.find_one({'username': username})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            flash('Login successful!', 'success')
            return redirect(url_for('contact_form'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = mongo.db.users.find_one({'email': email})
        if user:
            msg = Message('Password Reset', recipients=[email])
            msg.body = 'Click the link to reset your password.'
            mail.send(msg)
            flash('Password reset link sent to your email.', 'info')
        else:
            flash('Email not found.', 'danger')
    return render_template('forgot_password.html')


@app.route('/contact_form', methods=['GET', 'POST'])
def contact_form():
    if request.method == 'POST':
        contact = {
            'mobile_number': request.form['mobile_number'],
            'email': request.form['email'],
            'address': request.form['address'],
            'registration_number': request.form['registration_number']
        }
        mongo.db.contacts.insert_one(contact)
        flash('Contact saved successfully!', 'success')
    return render_template('contact_form.html')


@app.route('/search', methods=['GET', 'POST'])
def search():
    contact = None
    if request.method == 'POST':
        registration_number = request.form['registration_number']
        contact = mongo.db.contacts.find_one({'registration_number': registration_number})
        if not contact:
            flash('No contact found with that registration number.', 'warning')
    return render_template('search.html', contact=contact)


if __name__ == '__main__':
    app.run(debug=True)
