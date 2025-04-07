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
                    if check_setup_complete():
                        return redirect(url_for('dashboard'))
                    else:
                        return redirect(url_for('setup'))
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
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE Email = %s", (email,))
            user = cursor.fetchone()
            session['user_id'] = user['User_ID']
            session['user_name'] = user['Full_Name']
            return redirect(url_for('setup'))
        except Exception as e:
            print(f"Error: {e}")
            flash('An error occurred while registering, please try again later.', 'error')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('You have been logged out!', 'success')
    return redirect(url_for('login'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if logged_in() and not check_setup_complete():
        if request.method == 'POST':
            account_name = request.form['account_name']
            account_type = request.form['account_type']
            account_balance = request.form['account_balance']
            goal_target = request.form['goal_target']
            budget = request.form['monthly_budget']
            goal = request.form['goal1']
            deadline = request.form['goal_deadline']
            

            try:
                cursor = db.cursor()
                cursor.execute("INSERT INTO accounts (Account_Name, Account_Balance, Account_Type) VALUES (%s, %s, %s)", (account_name, account_balance, account_type))
                db.commit()
                
                # Get the Account_ID of the newly created account
                cursor.execute("SELECT LAST_INSERT_ID();")
                account_id = cursor.fetchone()[0]
                print(account_id)
                cursor.execute("INSERT INTO has (User_ID, Account_ID) VALUES (%s, %s)", (session['user_id'], account_id))
                db.commit()
                
                cursor.execute("INSERT INTO goals (Goal_Name, Goal_Date, Goal_Target, Goal_Description, Monthly_Budget) VALUES (%s, %s, %s, %s, %s)", ("Monthly Budget", "2000-01-01", budget, "Monthly Budget", 1))
                db.commit()
                
                cursor.execute("SELECT LAST_INSERT_ID();")
                goal_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO sets (User_ID, Goal_ID) VALUES (%s, %s)", (session['user_id'], goal_id))
                db.commit()
                
                cursor.execute("INSERT INTO goals (Goal_Name, Goal_Date, Goal_Target, Goal_Description, Monthly_Budget) VALUES (%s, %s, %s, %s, %s)", (goal, deadline, goal_target, "First Goal", 0))
                db.commit()
                
                cursor.execute("SELECT LAST_INSERT_ID();")
                goal_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO sets (User_ID, Goal_ID) VALUES (%s, %s)", (session['user_id'], goal_id))
                db.commit()

            except Exception as e:
                print(f"Error: {e}")
                flash('An error occurred while setting up your account, please try again later.', 'error')
                return redirect(url_for('setup'))

            flash("Setup complete!", "success")
            return redirect(url_for('dashboard'))

        return render_template('setup.html')
    elif logged_in():
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/transaction', methods = ['GET', 'POST'])
def transaction():
    if logged_in():
        if request.method == 'POST':
            amount = request.form['amount']
            description = request.form['description']
            date = request.form['date']

            try:
                cursor = db.cursor()
                cursor.execute("INSERT INTO transactions (Transaction_Amount, Transaction_Description, Transaction_Date) VALUES (%s, %s, %s)", (amount, description, date))
                db.commit()

                cursor.execute("SELECT LAST_INSERT_ID();")
                transaction_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO makes (User_ID, Transaction_ID) VALUES (%s, %s)", (session['user_id'], transaction_id))
                db.commit()

            except Exception as e:
                print(f"Error: {e}")
                flash('An error occurred while inputting the transaction, please try again later.', 'error')
                return redirect(url_for('transaction'))
            
            # flash("Transaction recorded!", "success")
            return redirect(url_for('dashboard'))
            
        return render_template('transaction.html')
    else:
        return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if logged_in():
        user_name = session['user_name']
        user_id = session['user_id']
        total_balance = 0
        total_spent = 0

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE User_ID = %s", (user_id,))
        user = cursor.fetchone()
        
        cursor = db.cursor()
        cursor.execute("SELECT Account_Balance FROM accounts WHERE Account_ID IN (SELECT Account_ID FROM has WHERE User_ID = %s)", (user_id,))
        balances = cursor.fetchall()
        for balance in balances:
            total_balance = total_balance + balance[0]
            
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT Goal_Target FROM goals WHERE Monthly_Budget = 1 AND Goal_ID IN (SELECT Goal_ID FROM sets WHERE User_ID = %s)", (user_id,))
        budget_goal = cursor.fetchone()["Goal_Target"]
        
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT Transaction_Amount FROM transactions WHERE Transaction_ID IN (SELECT Transaction_ID FROM makes WHERE User_ID = %s)", (user_id,))
        transactions = cursor.fetchall()
        for transaction in transactions:
            total_spent = total_spent + transaction["Transaction_Amount"]
            
        remaining = float(budget_goal) - float(total_spent)
        
        # Round to 2 decimal places as a string
        total_balance = "{:.2f}".format(total_balance)
        budget_goal = "{:.2f}".format(float(budget_goal))
        total_spent = "{:.2f}".format(float(total_spent))
        remaining = "{:.2f}".format(float(remaining))
        
        return render_template('dashboard.html', user_name=user_name, balance=total_balance, budget=budget_goal, spent=total_spent, remaining=remaining)
    else:
        return redirect(url_for('login'))
    
def logged_in():
    return 'user_id' in session

def check_setup_complete():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM has WHERE User_ID = %s", (session['user_id'],))
    account = cursor.fetchone()
    if account:
        return True
    return False

app.run(debug=True, host=os.getenv("FLASK_HOST"), port=int(os.getenv("FLASK_PORT")))