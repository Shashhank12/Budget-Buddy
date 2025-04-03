from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import re
import string
import os
from dotenv import load_dotenv
load_dotenv()

import mysql.connector
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=os.getenv("DB_PORT"),
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE Email = %s", (email,))
            user = cursor.fetchone()
            if user:
                if check_password_hash(user["Password"], password):
                    session['user_id'] = user['User_ID']
                    session['user_name'] = user['Full_Name']
                    return redirect(url_for('dashboard'))
                else:
                    flash('Incorrect login, Try Again!', 'error')
                    return redirect(url_for('login'))
            else:
                flash('Incorrect login, Try Again!', 'error')
                return redirect(url_for('login'))
        except Exception as e:
            print(f"Error: {e}")
            flash('An error occurred while logging in, please try again later.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register',  methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match, Try Again!', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 8:
            flash('Password must be longer than 8 characters long!', 'error')
            return redirect(url_for('register'))
        
        upper_flag = False
        lower_flag = False
        
        for letter in password:
            if letter.isupper():
                upper_flag = True
            if letter.islower():
                lower_flag = True

        regex = re.compile(f'[{re.escape(string.punctuation)}]')
        special_flag = bool(regex.search(password))

        if not(upper_flag and lower_flag and special_flag):
            flash('Password must have at least 1 lowercase, 1 uppercase, and 1 special character', 'error')
            return redirect(url_for('register'))
    
        try:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM users WHERE Email = %s", (email,))
            if cursor.fetchone():
                flash('Email already exists, Try Again!')
                return redirect(url_for('register'))
            
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            cursor.execute("INSERT INTO users (Full_Name, Email, Password) VALUES (%s, %s, %s)", (fullname, email, hashed_password))
            
            db.commit()
        except Exception as e:
            print(f"Error: {e}")
            flash('An error occurred while registering, please try again later.', 'error')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE User_ID = %s", (user_id,))
        user = cursor.fetchone()
        return render_template('dashboard.html', user=user)
    else:
        return redirect(url_for('login'))

app.run(debug=True, host=os.getenv("FLASK_HOST"), port=int(os.getenv("FLASK_PORT")))