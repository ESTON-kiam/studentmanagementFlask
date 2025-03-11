# app.py

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
import os
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
import re
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure MongoDB
app.config["MONGO_URI"] = "mongodb://localhost:27017/contact_db"
mongo = PyMongo(app)

# Configure Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'your_password'  # Replace with your email password
app.config['MAIL_DEFAULT_SENDER'] = 'your_email@gmail.com'  # Replace with your email
mail = Mail(app)

# Token serializer for password reset
ts = URLSafeTimedSerializer(app.secret_key)


# Check if user is logged in
def is_logged_in():
    return 'user_id' in session


# Routes
@app.route('/')
def index():
    if is_logged_in():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        registration_number = request.form.get('registration_number')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        address = request.form.get('address')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validate data
        if not registration_number or not email or not mobile or not address or not password:
            flash('All fields are required', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')

        # Check if registration number already exists
        if mongo.db.users.find_one({'registration_number': registration_number}):
            flash('Registration number already exists', 'danger')
            return render_template('register.html')

        # Check if email already exists
        if mongo.db.users.find_one({'email': email}):
            flash('Email already exists', 'danger')
            return render_template('register.html')

        # Create user document
        user = {
            'registration_number': registration_number,
            'email': email,
            'mobile': mobile,
            'address': address,
            'password': generate_password_hash(password)
        }

        # Insert user into database
        mongo.db.users.insert_one(user)

        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        registration_number = request.form.get('registration_number')
        password = request.form.get('password')

        # Find user
        user = mongo.db.users.find_one({'email': email})

        # Check if user exists and password is correct
        if user and check_password_hash(user['password'], password):
            # Store user in session
            session['user_id'] = str(user['_id'])
            session['email'] = user['email']
            session['registration_number'] = user['registration_number']

            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')

        # Find user
        user = mongo.db.users.find_one({'email': email})

        if not user:
            flash('Email not found', 'danger')
            return render_template('forgot_password.html')

        # Generate token
        token = ts.dumps(email, salt='password-reset-salt')

        # Create password reset link
        reset_url = url_for('reset_password', token=token, _external=True)

        # Create email message
        subject = "Password Reset Request"
        msg = Message(subject=subject, recipients=[email])
        msg.body = f"You requested a password reset. Please follow this link to reset your password: {reset_url}"

        # Send email
        try:
            mail.send(msg)
            flash('Password reset email sent. Please check your inbox.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error sending email: {str(e)}', 'danger')

    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Verify token (expires after 1 hour)
        email = ts.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        flash('The password reset link is invalid or has expired', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('reset_password.html', token=token)

        # Update password
        mongo.db.users.update_one(
            {'email': email},
            {'$set': {'password': generate_password_hash(password)}}
        )

        flash('Password has been reset successfully. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('login'))

    # Get user info
    user_id = session['user_id']
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})

    return render_template('dashboard.html', user=user)


@app.route('/search', methods=['GET', 'POST'])
def search():
    if not is_logged_in():
        return redirect(url_for('login'))

    results = []

    if request.method == 'POST':
        registration_number = request.form.get('registration_number')

        # Find user by registration number
        user = mongo.db.users.find_one({'registration_number': registration_number})

        if user:
            results.append(user)
        else:
            flash('No results found', 'info')

    return render_template('search.html', results=results)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)