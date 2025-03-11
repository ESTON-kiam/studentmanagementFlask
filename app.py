from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)


app.config['MONGO_URI'] = 'mongodb://localhost:27017/contactApp'
mongo = PyMongo(app)


EMAIL_ADDRESS = 'your_email@example.com'  # Replace with your email
EMAIL_PASSWORD = 'your_email_password'  # Replace with your email password
EMAIL_SERVER = 'smtp.example.com'  # Replace with your SMTP server
EMAIL_PORT = 587  # Replace with your SMTP port



@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = mongo.db.users.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')


        existing_user = mongo.db.users.find_one({'$or': [{'username': username}, {'email': email}]})
        if existing_user:
            flash('Username or email already exists', 'danger')
            return redirect(url_for('register'))


        hashed_password = generate_password_hash(password)
        mongo.db.users.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password,
            'created_at': datetime.now()
        })

        flash('Registration successful! Please login', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = mongo.db.users.find_one({'email': email})

        if user:

            reset_token = str(uuid.uuid4())
            expiry = datetime.now() + timedelta(hours=1)


            mongo.db.users.update_one(
                {'_id': user['_id']},
                {'$set': {'reset_token': reset_token, 'reset_expiry': expiry}}
            )


            send_reset_email(email, reset_token)

            flash('Password reset instructions sent to your email', 'info')
            return redirect(url_for('login'))
        else:
            flash('Email not found', 'danger')

    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):

    user = mongo.db.users.find_one({
        'reset_token': token,
        'reset_expiry': {'$gt': datetime.now()}
    })

    if not user:
        flash('Invalid or expired reset token', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('reset_password.html', token=token)


        hashed_password = generate_password_hash(new_password)
        mongo.db.users.update_one(
            {'_id': user['_id']},
            {
                '$set': {'password': hashed_password},
                '$unset': {'reset_token': "", 'reset_expiry': ""}
            }
        )

        flash('Password has been reset successfully. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    return render_template('dashboard.html')


@app.route('/add-contact', methods=['GET', 'POST'])
def add_contact():
    if 'user_id' not in session:
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        registration_number = request.form.get('registration_number')
        mobile = request.form.get('mobile')
        email = request.form.get('email')
        address = request.form.get('address')


        existing_contact = mongo.db.contacts.find_one({
            'user_id': session['user_id'],
            'registration_number': registration_number
        })

        if existing_contact:
            flash('Contact with this registration number already exists', 'danger')
            return redirect(url_for('add_contact'))


        mongo.db.contacts.insert_one({
            'user_id': session['user_id'],
            'registration_number': registration_number,
            'mobile': mobile,
            'email': email,
            'address': address,
            'created_at': datetime.now()
        })

        flash('Contact added successfully', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_contact.html')


@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'user_id' not in session:
        flash('Please login first', 'danger')
        return redirect(url_for('login'))

    contacts = []
    if request.method == 'POST':
        registration_number = request.form.get('registration_number')

        contacts = list(mongo.db.contacts.find({
            'user_id': session['user_id'],
            'registration_number': registration_number
        }))

        if not contacts:
            flash('No contacts found with this registration number', 'info')

    return render_template('search.html', contacts=contacts)


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))


def send_reset_email(email, token):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        msg['Subject'] = 'Password Reset Request'

        reset_link = f"{request.host_url}reset-password/{token}"
        body = f"""
        You recently requested to reset your password.
        Please click the following link to reset your password:

        {reset_link}

        This link will expire in 1 hour.

        If you did not request a password reset, please ignore this email.
        """

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


if __name__ == '__main__':
    app.run(debug=True)