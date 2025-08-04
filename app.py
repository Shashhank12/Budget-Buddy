from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import string
import os
import io
import base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dotenv import load_dotenv
import google.generativeai as genai
import datetime
from dateutil.relativedelta import relativedelta
import mysql.connector.pooling
import pandas as pd
from sklearn.linear_model import LinearRegression
import json
from decimal import Decimal
import numpy as np
import re

# Load the .env file for secrets
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# For database related stuff
pool_config = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "port": os.getenv("DB_PORT"),
    "autocommit": True,
    "pool_size": 10,
    "pool_reset_session": True
}

# Using connection pool so that the app is more responsive
connection_pool = mysql.connector.pooling.MySQLConnectionPool(**pool_config)

def get_db_connection():
    return connection_pool.get_connection()

# Getting Gemini ready
try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=GEMINI_API_KEY)
    generation_config = genai.GenerationConfig(
        max_output_tokens=1600,
        response_mime_type="text/plain",
    )

    gemini_model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        generation_config=generation_config
    )
except Exception as e:
    gemini_model = None

# Used for decimals to JSON. Needed for charts and whatnot
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)
app.json_encoder = DecimalEncoder

# Use to create the message for when an image is not being displayed correctly
def create_message_image(message, width=6, height=4, dpi=72): 
    fig = None
    try:
        fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
        ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=12, color='#6c757d', wrap=True)
        ax.set_axis_off()
        fig.tight_layout(pad=0.5)

        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', transparent=True)
        buffer.seek(0)
        plt.close(fig)
        base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{base64_str}'
    except Exception as e:
        plt.close(fig)
        return url_for('static', filename='error.png')

# The first route
@app.route('/')
def index():
    return render_template('index.html')

# Redirect to the default
@app.route('/index.html')
def index_redirect():
    return redirect(url_for('index'))

# Also redirects to the first
@app.route('/home.html')
def home_redirect():
    return redirect(url_for('index'))

# Route for login. Uses GET and POST because Login involves posting to the python code after form submission.
@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get email + password from user
        email = request.form['email']
        password = request.form['password']

        try:
            with get_db_connection() as db:
                # Check if user exists in the database
                cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE Email = %s", (email,))
                user = cursor.fetchone()
                cursor.close()
                if user:
                    # Check if the password hash matches the one in the database
                    if check_password_hash(user["Password"], password):
                        session['user_id'] = user['User_ID']
                        session['user_name'] = user['Full_Name']
                        if check_setup_complete(user['User_ID']):
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

        # Ensure password fulfills requirements
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 8:
            flash('Password needs to be at least 8 characters', 'error')
            return redirect(url_for('register'))

        upper = False
        lower = False
        special = False


        if re.search(r'[A-Z]', password):
            upper = True
            
        if re.search(r'[a-z]', password):
            lower = True

        regex = re.compile(f'[{re.escape(string.punctuation)}]')
        special = bool(regex.search(password))

        if not(upper and lower and special):
            flash('Password must have at least 1 lowercase, 1 uppercase, and 1 special character', 'error')
            return redirect(url_for('register'))
                
        # Check if email has already been used
        try:
            with get_db_connection() as db:
                cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE Email = %s", (email,))
                if cursor.fetchone():
                    flash('Email already exists, Try Again!')
                    cursor.close()
                    return redirect(url_for('register'))

                hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                cursor.execute("INSERT INTO users (Full_Name, Email, Password) VALUES (%s, %s, %s)", (fullname, email, hashed_password))
                db.commit()

                # Load user credentials for session
                cursor.execute("SELECT User_ID, Full_Name FROM users WHERE Email = %s", (email,))
                user = cursor.fetchone()
                cursor.close()
                if user:
                    session['user_id'] = user['User_ID']
                    session['user_name'] = user['Full_Name']
                    return redirect(url_for('setup'))
                else:
                     flash('Registration succeeded but failed to log in automatically.', 'warning')
                     return redirect(url_for('login'))
        except Exception as e:
            flash('An error occurred while registering, please try again later.', 'error')
            return redirect(url_for('register'))
    return render_template('register.html')

# Route for loggin out, which just removes session related stuff
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('You have been logged out!', 'success')
    return redirect(url_for('login'))

# When an account is initially created, redirect to setup so that users can get some basic information filled
@app.route('/setup', methods=['GET', 'POST'])
def setup():
    user_id = session.get('user_id')
    if not user_id:
         return redirect(url_for('login'))

    # Check if user already completed setup
    if check_setup_complete(user_id):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        account_name = request.form['account_name']
        account_type = request.form['account_type']
        account_balance = request.form['account_balance']
        goal_target = request.form['goal_target']
        budget = request.form['monthly_budget']
        goal = request.form['goal1']
        deadline = request.form['goal_deadline']


        try:
            with get_db_connection() as db:
                # Load initial user data into the database
                cursor = db.cursor()
                cursor.execute("INSERT INTO accounts (Account_Name, Account_Balance, Account_Type) VALUES (%s, %s, %s)", (account_name, account_balance, account_type))
                cursor.execute("SELECT LAST_INSERT_ID()")
                account_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO has (User_ID, Account_ID) VALUES (%s, %s)", (user_id, account_id))

                cursor.execute("INSERT INTO goals (Goal_Name, Goal_Date, Goal_Target, Goal_Description, Monthly_Budget) VALUES (%s, %s, %s, %s, %s)", ("Monthly Budget", "2000-01-01", budget, "Monthly Budget", 1))
                cursor.execute("SELECT LAST_INSERT_ID()")
                budget_goal_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO sets (User_ID, Goal_ID) VALUES (%s, %s)", (user_id, budget_goal_id))

                cursor.execute("INSERT INTO goals (Goal_Name, Goal_Date, Goal_Target, Goal_Description, Monthly_Budget) VALUES (%s, %s, %s, %s, %s)", (goal, deadline, goal_target, "First Goal", 0))
                cursor.execute("SELECT LAST_INSERT_ID()")
                first_goal_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO sets (User_ID, Goal_ID) VALUES (%s, %s)", (user_id, first_goal_id))

                db.commit()
                cursor.close()

        except Exception as e:
            flash('An error occurred', 'error')
            return redirect(url_for('setup'))

        return redirect(url_for('dashboard'))

    return render_template('setup.html')

# Route for adding transactions to account
@app.route('/transaction', methods = ['GET', 'POST'])
def transaction():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    accounts = []
    categories = load_categories(user_id)

    # Retrieve user's account data
    try:
        with get_db_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT Account_ID, Account_Name, Account_Balance FROM accounts JOIN has USING (Account_ID) WHERE User_ID = %s", (user_id,))
            accounts = cursor.fetchall()
            cursor.close()
    except Exception as e:
        flash('Could not load account data.', 'error')

    if request.method == 'POST':
        amount = request.form['amount']
        description = request.form['description']
        date = request.form['date']
        category_name = request.form['category']
        account_id_form = request.form['account']

        try:
            with get_db_connection() as db:
                cursor = db.cursor(dictionary=True)

                # Check if selected category exists
                cursor.execute("SELECT Category_ID FROM categories JOIN selects USING (Category_ID) WHERE User_ID = %s AND Category_Name = %s", (user_id, category_name))
                category_result = cursor.fetchone()
                if not category_result:
                     flash('Selected category not found.', 'error')
                     cursor.close()
                     return render_template('transaction.html', categories=categories, accounts=accounts, user_name=session.get('user_name', 'User'))
                category_id = category_result['Category_ID']

                # Record transaction in database
                cursor.execute("INSERT INTO transactions (Transaction_Amount, Transaction_Description, Transaction_Date) VALUES (%s, %s, %s)", (amount, description, date))
                cursor = db.cursor()
                cursor.execute("SELECT LAST_INSERT_ID()")
                transaction_id = cursor.fetchone()[0]
                print("Transaction ID: ", transaction_id)

                cursor.execute("INSERT INTO makes (User_ID, Transaction_ID) VALUES (%s, %s)", (user_id, transaction_id))
                cursor.execute("INSERT INTO falls_under (Transaction_ID, Category_ID) VALUES (%s, %s)", (transaction_id, category_id))
                cursor.execute("INSERT INTO made_on (Transaction_ID, Account_ID) VALUES (%s, %s)", (transaction_id, account_id_form))

                cursor.execute("UPDATE accounts SET Account_Balance = Account_Balance - %s WHERE Account_ID = %s", (amount, account_id_form))

                db.commit()
                cursor.close()

                flash('Transaction recorded', 'success')
                return redirect(url_for('dashboard'))

        except Exception as e:
            flash('Failed to save transaction. Please try again.', 'error')
            print(f"Error: {e}")

            return render_template('transaction.html', categories=categories, accounts=accounts, user_name=session.get('user_name', 'User'))
    else:
        return render_template('transaction.html', categories=categories, accounts=accounts, user_name=session.get('user_name', 'User'))


@app.route('/category', methods = ['GET', 'POST'])
def category():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    categories = load_categories(user_id)

    if request.method == 'POST':
        action = request.form.get('action')
        
        try:
            with get_db_connection() as db:
                cursor = db.cursor(dictionary=True)
                # Add new category to database
                if action == 'add':
                    new_category_name = request.form['add_category'].strip()
                    # Check if category already exists
                    if new_category_name:
                        cursor.execute("SELECT Category_ID FROM categories JOIN selects USING (Category_ID) WHERE User_ID = %s AND Category_Name = %s", (user_id, new_category_name))
                        if cursor.fetchone():
                             flash('Category already exists.', 'warning')
                        else:
                            cursor = db.cursor()
                            cursor.execute("INSERT INTO categories (Category_Name) VALUES (%s)", (new_category_name,))
                            cursor.execute("SELECT LAST_INSERT_ID()")
                            category_id = cursor.fetchone()[0]
                            cursor.execute("INSERT INTO selects (User_ID, Category_ID) VALUES (%s, %s)", (user_id, category_id))
                            db.commit()
                            flash('Category added.', 'success')
                            categories = load_categories(user_id)
                    else:
                        flash('Category name cannot be empty.', 'error')
                # Save edited category name
                elif action == 'save':
                    updated_count = 0
                    for key, new_name in request.form.items():
                        if key.startswith("new_category-"):
                            index = key.split('-')[1]
                            old_name_key = f'old_category-{index}'
                            old_name = request.form.get(old_name_key)
                            new_name = new_name.strip()

                            if old_name and new_name and old_name != new_name:
                                cursor.execute("SELECT Category_ID FROM categories JOIN selects USING (Category_ID) WHERE User_ID = %s AND Category_Name = %s", (user_id, old_name))
                                category_result = cursor.fetchone()
                                if category_result:
                                     category_id = category_result['Category_ID']
                                     cursor.execute("SELECT Category_ID FROM categories JOIN selects USING (Category_ID) WHERE User_ID = %s AND Category_Name = %s AND Category_ID != %s", (user_id, new_name, category_id))
                                     if cursor.fetchone():
                                         flash(f'Cannot rename "{old_name}" to "{new_name}", category already exists.', 'error')
                                     else:
                                         cursor.execute("UPDATE categories SET Category_Name = %s WHERE Category_ID = %s", (new_name, category_id))
                                         updated_count += 1
                    if updated_count > 0:
                        db.commit()
                        flash(f'{updated_count} categor{"y" if updated_count == 1 else "ies"} updated.', 'success')
                        categories = load_categories(user_id)
                # Delete category
                elif action == 'delete':
                    category_name_to_delete = None

                    for key, value in request.form.items():
                        if key == 'delete_target':
                            category_name_to_delete = value
                            break
                    
                    if category_name_to_delete:
                        cursor.execute("SELECT Category_ID FROM categories JOIN selects USING (Category_ID) WHERE User_ID = %s AND Category_Name = %s", (user_id, category_name_to_delete))
                        category_result = cursor.fetchone()
                        if category_result:
                            category_id = category_result['Category_ID']
                            cursor.execute("DELETE FROM selects WHERE User_ID = %s AND Category_ID = %s", (user_id, category_id))
                            cursor.execute("DELETE FROM categories WHERE Category_ID = %s", (category_id,))
                            db.commit()
                            flash(f'Category "{category_name_to_delete}" deleted.', 'success')
                            categories = load_categories(user_id)
                        else:
                            flash('Category not found for deletion.', 'warning')
                cursor.close()

        except Exception as e:
             flash('An error occurred while managing categories.', 'error')
             categories = load_categories(user_id)

    return render_template('category.html', categories=categories, user_name=session.get('user_name', 'User'))


def load_categories(user_id):
    categories = []
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("SELECT Category_Name FROM categories JOIN selects USING (Category_ID) WHERE User_ID = %s ORDER BY Category_Name", (user_id,))
            categories_tuples = cursor.fetchall()
            cursor.close()
            categories = [category[0] for category in categories_tuples]
    except Exception as e:
        print(f"Error loading categories for user {user_id}: {e}")
    return categories

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user_name = session.get('user_name', 'User')
    total_balance = 0.0
    total_spent = 0.0
    budget_goal = 0.0
    remaining = 0.0

    today = datetime.date.today()
    view_type = request.form.get('time_view', 'month')
    time_offset = int(request.form.get('time_offset', 0))

    start_date_dt = None
    end_date_dt = None
    month_year_string = ""
    start_date_str = ''
    end_date_str = ''

    # Filter data by week, month, or year
    try:
        if view_type == 'month':
            target_month_date = today + relativedelta(months=time_offset)
            start_date_dt = target_month_date.replace(day=1)
            end_date_dt = (start_date_dt + relativedelta(months=1)) - relativedelta(days=1)
            month_year_string = start_date_dt.strftime("%B %Y")
        elif view_type == 'week':
            target_date = today + relativedelta(weeks=time_offset)
            start_date_dt = target_date - relativedelta(days=target_date.weekday())
            end_date_dt = start_date_dt + relativedelta(days=6)
            month_year_string = f"{start_date_dt.strftime('%b %d')} - {end_date_dt.strftime('%b %d, %Y')}"
        elif view_type == 'year':
            target_year = today.year + time_offset
            start_date_dt = datetime.date(target_year, 1, 1)
            end_date_dt = datetime.date(target_year, 12, 31)
            month_year_string = str(target_year)
        else:
             view_type = 'month'
             target_month_date = today + relativedelta(months=time_offset)
             start_date_dt = target_month_date.replace(day=1)
             end_date_dt = (start_date_dt + relativedelta(months=1)) - relativedelta(days=1)
             month_year_string = start_date_dt.strftime("%B %Y")

        start_date_str = start_date_dt.strftime('%Y-%m-%d')
        end_date_str = end_date_dt.strftime('%Y-%m-%d')


        with get_db_connection() as db:
            cursor = db.cursor(dictionary=True)

            # Get total balance from all accounts
            cursor.execute("SELECT SUM(Account_Balance) as total_balance FROM accounts JOIN has USING (Account_ID) WHERE User_ID = %s", (user_id,))
            balance_result = cursor.fetchone()
            if balance_result and balance_result['total_balance'] is not None:
                total_balance = float(balance_result['total_balance'])

            # Get monthly budget goal
            cursor.execute("SELECT Goal_Target FROM goals WHERE Monthly_Budget = 1 AND Goal_ID IN (SELECT Goal_ID FROM sets WHERE User_ID = %s)", (user_id,))
            budget_result = cursor.fetchone()
            monthly_budget_goal = 0.0
            if budget_result and budget_result['Goal_Target'] is not None:
                monthly_budget_goal = float(budget_result['Goal_Target'])

            cursor.execute("SELECT SUM(Transaction_Amount) as total_spent FROM transactions JOIN makes USING (Transaction_ID) WHERE User_ID = %s AND Transaction_Date BETWEEN %s AND %s", (user_id, start_date_str, end_date_str))

            spent_result = cursor.fetchone()
            if spent_result and spent_result['total_spent'] is not None:
                total_spent = float(spent_result['total_spent'])

            cursor.close()

        if view_type == 'year':
            budget_goal = monthly_budget_goal * 12
        elif view_type == 'week':
            budget_goal = monthly_budget_goal / 4
        else:
            budget_goal = monthly_budget_goal

        remaining = max(0.0, budget_goal - total_spent)

    except Exception as e:
        flash('Could not load dashboard data.', 'error')

    filter_categories = load_categories(user_id)

    return render_template('dashboard.html',
                           user_name=user_name,
                           balance=f"{total_balance:.2f}",
                           budget=f"{budget_goal:.2f}",
                           spent=f"{total_spent:.2f}",
                           remaining=f"{remaining:.2f}",
                           month_year=month_year_string,
                           selected_view=view_type,
                           time_offset=time_offset,
                           start_date=start_date_str,
                           end_date=end_date_str,
                           filter_categories=filter_categories
                           )

# Check if user is logged in
def logged_in():
    return 'user_id' in session

# Check is user completed initial setup
def check_setup_complete(user_id):
    try:
        with get_db_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT 1 FROM has WHERE User_ID = %s LIMIT 1", (user_id,))
            has_account = cursor.fetchone()
            cursor.execute("SELECT 1 FROM goals g JOIN sets s USING(Goal_ID) WHERE s.User_ID = %s AND g.Monthly_Budget = 1 LIMIT 1", (user_id,))
            has_budget_goal = cursor.fetchone()
            cursor.close()
            has_setup = has_account and has_budget_goal
            return has_setup
    except Exception as e:
        return False

# Create pie chart for budget
def create_budget_pie_chart(current_spent, budget_total):
    fig = None
    try:
        current_spent_f = max(0, float(current_spent))
        budget_total_f = max(0.01, float(budget_total))

        fig, ax = plt.subplots(figsize=(5, 5), dpi=90)
        ax.set_title('Spending vs Budget', fontsize=14, pad=15, weight='bold')

        if current_spent_f == 0 and budget_total_f <= 0.01:
             plt.close(fig)
             return create_message_image("No Budget or\nSpending Data", width=5, height=5, dpi=90)
        # Check is user overspent
        if current_spent_f > budget_total_f:
            overspent_amount = current_spent_f - budget_total_f
            labels = [f'Budget (${budget_total_f:.2f})']
            sizes = [1]
            colors = ['#dc3545']
            pie_labels = [f'Budget Used (${budget_total_f:.2f})']
            ax.text(0, 0, f"Overspent\n+${overspent_amount:.2f}",
                    ha='center', va='center', fontsize=14, weight='bold', color='#dc3545')
        elif current_spent_f == 0 and budget_total_f > 0:
            labels = [f'Budget Remaining (${budget_total_f:.2f})']
            sizes = [1]
            colors = ['#28a745']
            pie_labels = labels
        else:
            remaining = budget_total_f - current_spent_f
            labels = [f'Spent (${current_spent_f:.2f})', f'Remaining (${remaining:.2f})']
            sizes = [current_spent_f, remaining]
            colors = ['#dc3545', '#28a745']
            pie_labels = labels


        if sizes and sum(sizes) > 0:
             wedges, texts = ax.pie(
                sizes,
                explode=(0.05,) * len(sizes) if len(sizes) > 1 else None,
                labels=None,
                colors=colors,
                autopct=None,
                shadow=False,
                startangle=90,
                wedgeprops=dict(width=0.4, edgecolor='w')
            )

             ax.legend(wedges, pie_labels,
                      loc='upper center',
                      bbox_to_anchor=(0.5, -0.05),
                      fontsize='12',
                      frameon=False,
                      ncol=1)
        else:
             ax.text(0.5, 0.5, "No Data", ha='center', va='center', transform=ax.transAxes, fontsize=14, color='#cccccc')

        ax.axis('equal')
        fig.tight_layout(rect=[0, 0.05, 1, 1])

        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', transparent=True)
        buffer.seek(0)
        plt.close(fig)

        base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{base64_str}'

    except Exception as e:
        if fig: 
            plt.close(fig)
        return create_message_image("Error loading\nbudget chart", width=5, height=5, dpi=90)

# Get data for pie chart
@app.route('/api/pie-chart')
def get_pie_chart_data_api():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    view = request.args.get('view', 'month')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not start_date_str or not end_date_str:
        return jsonify({"error": "Missing start or end date"}), 400

    total_spent = 0.0
    budget_goal = 0.0
    monthly_budget_goal = 0.0

    try:
        with get_db_connection() as db:
            cursor = db.cursor(dictionary=True)

            # Get total amount spent
            cursor.execute("SELECT SUM(Transaction_Amount) AS total FROM transactions JOIN makes USING (Transaction_ID) WHERE User_ID = %s AND Transaction_Date BETWEEN %s AND %s", (user_id, start_date_str, end_date_str))
            spent_result = cursor.fetchone()
            total_spent = float(spent_result['total'] or 0.0)

            # Get montly budget goal
            cursor.execute("SELECT Goal_Target FROM goals WHERE Monthly_Budget = 1 AND Goal_ID IN (SELECT Goal_ID FROM sets WHERE User_ID = %s)", (user_id,))
            budget_result = cursor.fetchone()
            monthly_budget_goal = float(budget_result['Goal_Target'] or 0.0)

            cursor.close()

        if view == 'year':
            budget_goal = monthly_budget_goal * 12
        elif view == 'week':
             budget_goal = monthly_budget_goal / 4.33
        else:
            budget_goal = monthly_budget_goal

        chart_uri = create_budget_pie_chart(total_spent, budget_goal)
        if chart_uri:
            return jsonify({"chart_uri": chart_uri})
        else:
            return jsonify({"error": "Chart generation failed"}), 500

    except Exception as e:
        return jsonify({"error": f"Internal server error: {e}", "chart_uri": create_message_image("API Error", width=5, height=5, dpi=90)}), 500

# Create line chart for spending by category
def create_line_chart_for_categories(user_id, start_date, end_date):
    fig = None
    try:
        start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        date_range_days = (end_dt - start_dt).days + 1

        # Get 
        with get_db_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT Category_Name, Transaction_Date, SUM(Transaction_Amount) AS Daily_Amount FROM transactions JOIN falls_under USING (Transaction_ID) JOIN categories USING (Category_ID) JOIN makes USING (Transaction_ID) WHERE User_ID = %s AND Transaction_Date BETWEEN %s AND %s GROUP BY Category_Name, Transaction_Date ORDER BY Transaction_Date, Category_Name", (user_id, start_date, end_date))
            transactions = cursor.fetchall()
            cursor.close()

        fig, ax = plt.subplots(figsize=(7, 4), dpi=96)

        if not transactions:
             plt.close(fig)
             return create_message_image("No spending data in this period.", width=7, height=4, dpi=96)

        df = pd.DataFrame(transactions)
        df['Transaction_Date'] = pd.to_datetime(df['Transaction_Date']).dt.date
        df['Daily_Amount'] = df['Daily_Amount'].astype(float)
        pivot_df = df.pivot_table(index='Transaction_Date', columns='Category_Name', values='Daily_Amount', fill_value=0)
        all_dates = pd.date_range(start=start_dt, end=end_dt, freq='D').date
        pivot_df = pivot_df.reindex(all_dates, fill_value=0)
        colors = plt.cm.tab10.colors
        categories = pivot_df.columns

        for i, category in enumerate(categories):
            color = colors[i % len(colors)]
            total_spend = pivot_df[category].sum()
            if total_spend > 0:
                ax.plot(pivot_df.index, pivot_df[category], marker='.', markersize=4,
                       linestyle='-', linewidth=1.2,
                       label=f"{category} (${total_spend:.2f})", color=color)

        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel('Spending ($)', fontsize=10)
        ax.set_title('Daily Spending by Category', fontsize=12, fontweight='bold')

        if date_range_days <= 10: locator, formatter = mdates.DayLocator(), mdates.DateFormatter('%a %d')
        elif date_range_days <= 60: locator, formatter = mdates.DayLocator(interval=max(1, date_range_days // 7)), mdates.DateFormatter('%b %d')
        elif date_range_days <= 730: locator, formatter = mdates.MonthLocator(), mdates.DateFormatter('%b %y')
        else: locator, formatter = mdates.YearLocator(), mdates.DateFormatter('%Y')

        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        fig.autofmt_xdate(rotation=30, ha='right')
        ax.tick_params(axis='both', which='major', labelsize=9)

        if len(categories) > 0:
             ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), borderaxespad=0., fontsize=8.5)

        ax.grid(True, alpha=0.3, linestyle=':')
        ax.set_ylim(bottom=0)
        fig.tight_layout(rect=[0, 0, 0.88, 1])

        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=96)
        buffer.seek(0)
        plt.close(fig)
        base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{base64_str}'

    except Exception as e:
        if fig: 
            plt.close(fig)
        return create_message_image("Error loading category spending chart", width=7, height=4, dpi=96)

# Get data for line chart
@app.route('/api/line-chart')
def get_line_chart_data_api():
    user_id = session.get('user_id')
    if not user_id: return jsonify({"error": "Not authenticated"}), 401
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date: return jsonify({"error": "Missing start or end date"}), 400
    try:
        chart_uri = create_line_chart_for_categories(user_id, start_date, end_date)
        return jsonify({"chart_uri": chart_uri})
    except Exception as e:
        return jsonify({"error": f"Internal server error: {e}", "chart_uri": create_message_image("API Error", width=7, height=4, dpi=96)}), 500

# Create pie chart for spending by category
def create_category_spending_pie_chart(user_id, start_date, end_date):
    fig = None
    try:
        with get_db_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT Category_Name, SUM(Transaction_Amount) AS Total_Amount FROM transactions JOIN falls_under USING (Transaction_ID) JOIN categories USING (Category_ID) JOIN makes USING (Transaction_ID) WHERE User_ID = %s AND Transaction_Date BETWEEN %s AND %s GROUP BY Category_Name HAVING Total_Amount > 0 ORDER BY Total_Amount DESC", (user_id, start_date, end_date))
            category_spending = cursor.fetchall()
            cursor.close()

        fig, ax = plt.subplots(figsize=(5, 5), dpi=90)
        ax.set_title('Spending by Category', fontsize=14, pad=15, weight='bold')

        if not category_spending:
            plt.close(fig)
            return create_message_image("No Spending Data\nfor Categories", width=5, height=5, dpi=90)

        labels = [f"{item['Category_Name']} (${float(item['Total_Amount']):.2f})" for item in category_spending]
        sizes = [float(item['Total_Amount']) for item in category_spending]
        colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(sizes)))

        wedges, texts = ax.pie(
            sizes, labels=None, colors=colors, autopct=None, shadow=False, startangle=90,
            wedgeprops=dict(width=0.4, edgecolor='w')
        )

        ax.legend(wedges, labels, loc='upper center', bbox_to_anchor=(0.5, -0.05),
                  fontsize='12', frameon=False, ncol=1)
        ax.axis('equal')
        fig.tight_layout(rect=[0, 0.05, 1, 1])

        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', transparent=True)
        buffer.seek(0)
        plt.close(fig)
        base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{base64_str}'

    except Exception as e:
        if fig: 
            plt.close(fig)
        return create_message_image("Error loading\ncategory pie chart", width=5, height=5, dpi=90)

# Get data for spending by category pie chart
@app.route('/api/category-pie-chart')
def get_category_pie_chart_api():
    user_id = session.get('user_id')
    if not user_id: return jsonify({"error": "Not authenticated"}), 401
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date: return jsonify({"error": "Missing start or end date"}), 400
    try:
        chart_uri = create_category_spending_pie_chart(user_id, start_date, end_date)
        return jsonify({"chart_uri": chart_uri})
    except Exception as e:
        return jsonify({"error": f"Internal server error: {e}", "chart_uri": create_message_image("API Error", width=5, height=5, dpi=90)}), 500

# Get data for prediction analysis
def get_prediction_data(user_id, view_type, current_start_date_str):
    num_historical_periods = 0
    period_delta = None
    period_name = ""
    period_format_label = lambda d: d.strftime('%Y-%m-%d')

    current_start_date = datetime.datetime.strptime(current_start_date_str, '%Y-%m-%d').date()

    if view_type == 'week': num_historical_periods, period_delta, period_name, period_format_label = 8, relativedelta(weeks=1), "Week", lambda d: f"W {d.strftime('%U')}"
    elif view_type == 'month': num_historical_periods, period_delta, period_name, period_format_label = 12, relativedelta(months=1), "Month", lambda d: d.strftime('%b %y')
    elif view_type == 'year': num_historical_periods, period_delta, period_name, period_format_label = 5, relativedelta(years=1), "Year", lambda d: d.strftime('%Y')
    else: return None, "Invalid view type for prediction."

    historical_data = []
    analysis_text = f"**Prediction Analysis ({period_name}ly Trend)**\n\n"
    try:
        with get_db_connection() as db:
            cursor = db.cursor(dictionary=True)
            period_labels = []
            period_amounts = []
            for i in range(num_historical_periods, 0, -1):
                hist_end_date = current_start_date - (period_delta * (i-1)) - relativedelta(days=1)
                hist_start_date = current_start_date - (period_delta * i)
                period_label = period_format_label(hist_start_date)
                period_labels.append(period_label)
                cursor.execute("SELECT SUM(Transaction_Amount) as total_spent FROM transactions JOIN makes USING (Transaction_ID) WHERE User_ID = %s AND Transaction_Date BETWEEN %s AND %s ", (user_id, hist_start_date.strftime('%Y-%m-%d'), hist_end_date.strftime('%Y-%m-%d')))
                result = cursor.fetchone()
                amount = float(result['total_spent'] or 0.0)
                historical_data.append({'period_label': period_label, 'amount': amount})
                period_amounts.append(amount)
            cursor.close()

        if len(period_amounts) < 3: return None, f"Not enough historical data (need at least 3 {period_name.lower()}s)."

        df = pd.DataFrame({'period_index': range(num_historical_periods), 'amount': period_amounts})
        X = df[['period_index']]
        y = df['amount']
        model = LinearRegression()
        model.fit(X, y)
        prediction = max(0, model.predict(np.array([[num_historical_periods]]))[0])
        prediction_data = {'period_label': f"Next {period_name}", 'amount': prediction}

        avg_historical = np.mean(period_amounts)
        std_dev_historical = np.std(period_amounts) if len(period_amounts) > 1 else 0
        last_period_amount = period_amounts[-1]
        trend = model.coef_[0]
        pred_diff = prediction - last_period_amount
        pred_diff_perc = (pred_diff / (last_period_amount + 0.01)) * 100 if last_period_amount else (100 if prediction > 0 else 0)

        analysis_text += f"*   **Historical Average:** ${avg_historical:.2f} per {period_name.lower()} (Std Dev: ${std_dev_historical:.2f}).\n"
        analysis_text += f"*   **Last Period's Spending:** ${last_period_amount:.2f}.\n"
        analysis_text += f"*   **Linear Trend:** Spending changed by approx. **${trend:+.2f}** per {period_name.lower()}. "
        analysis_text += f"{'Suggests increase.' if trend > 0.01 else ('Suggests decrease.' if trend < -0.01 else 'Relatively stable.')}\n"
        analysis_text += f"*   **Prediction for Next {period_name}:** **${prediction:.2f}**. Change of ${pred_diff:+.2f} ({pred_diff_perc:+.1f}%).\n\n"

        return {'historical': historical_data, 'prediction': prediction_data}, analysis_text

    except Exception as e:
        return None, "Could not generate prediction data due to an error."

# Create line chart with prediction 
def create_prediction_line_chart(prediction_result):
    fig = None
    if not prediction_result or 'historical' not in prediction_result or 'prediction' not in prediction_result:
        return create_message_image("Not enough data\nfor prediction chart.", width=7, height=4, dpi=96)

    historical = prediction_result['historical']
    prediction = prediction_result['prediction']
    if not historical: return create_message_image("No historical data\nfor prediction.", width=7, height=4, dpi=96)

    try:
        fig, ax = plt.subplots(figsize=(7, 4), dpi=96)

        hist_labels = [h['period_label'] for h in historical]
        hist_amounts = [h['amount'] for h in historical]
        hist_indices = range(len(historical))

        ax.plot(hist_indices, hist_amounts, marker='o', markersize=5, linestyle='-', color='royalblue', label='Historical Spending')

        pred_index = len(historical)
        pred_amount = prediction['amount']
        pred_label = prediction['period_label']

        ax.plot(pred_index, pred_amount, marker='*', markersize=12, color='orangered', linestyle='none', label=f'Predicted: ${pred_amount:.2f}')
        ax.plot([hist_indices[-1], pred_index], [hist_amounts[-1], pred_amount], linestyle=':', color='grey', alpha=0.7)

        all_labels = hist_labels + [pred_label]
        all_indices = list(hist_indices) + [pred_index]

        ax.set_xticks(all_indices)
        ax.set_xticklabels(all_labels, rotation=30, ha='right', fontsize=9)

        ax.set_ylabel('Spending ($)', fontsize=10)
        ax.set_title('Spending Trend and Prediction', fontsize=12, fontweight='bold')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3, linestyle=':')
        ax.set_ylim(bottom=0)
        ax.tick_params(axis='y', labelsize=10)

        fig.tight_layout()

        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=96)
        buffer.seek(0)
        plt.close(fig)
        base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{base64_str}'

    except Exception as e:
        if fig: plt.close(fig)
        return create_message_image("Error generating\nprediction chart.", width=7, height=4, dpi=96)

# Get data for prediction line chart
@app.route('/api/prediction-chart')
def get_prediction_chart_api():
    user_id = session.get('user_id')
    if not user_id: return jsonify({"error": "Not authenticated"}), 401
    view_type = request.args.get('view')
    start_date_str = request.args.get('start_date')
    if not view_type or not start_date_str: return jsonify({"error": "Missing view type or start date"}), 400
    try:
        prediction_data, _ = get_prediction_data(user_id, view_type, start_date_str)
        chart_uri = create_prediction_line_chart(prediction_data)
        return jsonify({"chart_uri": chart_uri})
    except Exception as e:
        return jsonify({"error": f"Internal server error: {e}", "chart_uri": create_message_image("API Error", width=7, height=4, dpi=96)}), 500

# Get data for prediction analysis
@app.route('/api/spending-prediction')
def get_spending_prediction_api():
    user_id = session.get('user_id')
    if not user_id: return jsonify({"error": "Not authenticated"}), 401
    view_type = request.args.get('view')
    start_date_str = request.args.get('start_date')
    if not view_type or not start_date_str: return jsonify({"error": "Missing view type or start date"}), 400
    try:
        _, analysis_text = get_prediction_data(user_id, view_type, start_date_str)
        return jsonify({"analysis_text": analysis_text})
    except Exception as e:
        return jsonify({"analysis_text": f"Error loading analysis: {e}"}), 500

# Get data for AI chatbot
def get_data_for_chatbot(user_id, start_date, end_date, limit=5):
    context_data = {}
    try:
        with get_db_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT SUM(Transaction_Amount) as total_spent, COUNT(*) as transaction_count FROM transactions JOIN makes USING (Transaction_ID) WHERE User_ID = %s AND Transaction_Date BETWEEN %s AND %s", (user_id, start_date, end_date))
            summary = cursor.fetchone()
            context_data['total_spent'] = float(summary['total_spent'] or 0.0)
            context_data['transaction_count'] = int(summary['transaction_count'] or 0)
            cursor.execute("SELECT Goal_Target FROM goals WHERE Monthly_Budget = 1 AND Goal_ID IN (SELECT Goal_ID FROM sets WHERE User_ID = %s)", (user_id,))
            budget_result = cursor.fetchone()
            context_data['monthly_budget_goal'] = float(budget_result['Goal_Target'] or 0.0)
            cursor.execute("SELECT c.Category_Name, SUM(t.Transaction_Amount) AS Amount, COUNT(*) as Count FROM transactions t JOIN falls_under fu ON t.Transaction_ID = fu.Transaction_ID JOIN categories c ON fu.Category_ID = c.Category_ID JOIN makes m ON t.Transaction_ID = m.Transaction_ID WHERE m.User_ID = %s AND t.Transaction_Date BETWEEN %s AND %s GROUP BY c.Category_Name HAVING Amount > 0 ORDER BY Amount DESC ", (user_id, start_date, end_date))
            categories = cursor.fetchall()
            context_data['category_spending'] = { c['Category_Name']: {'total': float(c['Amount']), 'count': int(c['Count'])} for c in categories }
            cursor.execute("SELECT t.Transaction_Date, t.Transaction_Description, t.Transaction_Amount, c.Category_Name FROM transactions t JOIN falls_under fu ON t.Transaction_ID = fu.Transaction_ID JOIN categories c ON fu.Category_ID = c.Category_ID JOIN makes m ON t.Transaction_ID = m.Transaction_ID WHERE m.User_ID = %s AND t.Transaction_Date BETWEEN %s AND %s ORDER BY t.Transaction_Amount DESC LIMIT %s ", (user_id, start_date, end_date, limit))
            top_transactions = cursor.fetchall()
            context_data['top_transactions'] = [ {'date': t['Transaction_Date'].strftime('%Y-%m-%d'), 'desc': t['Transaction_Description'], 'amount': float(t['Transaction_Amount']), 'category': t['Category_Name']} for t in top_transactions ]
            cursor.close()
        return context_data
    except Exception as e:
        return {"error": "Could not retrieve detailed data for analysis."}


@app.route('/api/chatbot', methods=['POST'])
def chatbot_api():
    user_id = session.get('user_id')
    if not user_id or not gemini_model: return jsonify({"error": "Chatbot unavailable or user not authenticated"}), 403

    data = request.json
    user_prompt = data.get('prompt')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    view_type = data.get('view_type')
    if not user_prompt or not start_date or not end_date or not view_type: return jsonify({"error": "Missing required data"}), 400

    period_data = get_data_for_chatbot(user_id, start_date, end_date)
    if "error" in period_data: return jsonify({"response": period_data["error"]})

    period_budget = period_data['monthly_budget_goal']
    period_name = f"{start_date} to {end_date}"
    if view_type == 'year':
        period_budget *= 12
        period_name = f"the year starting {start_date}"
    elif view_type == 'week':
        
        period_budget /= 4
        period_name = f"the week of {start_date}"
    elif view_type == 'month':
        period_name = f"the month starting {start_date}"

    system_instruction = f""" You are a friendly financial analysis assistant. Analyze the user's spending for {period_name}. Be concise and focus ONLY on the provided data summary. Do not make up info. Also answer any additional questions the user asks related to money to the best of your ability. Give good examples and tips.

    Data Summary:
    Total Spent: ${period_data['total_spent']:.2f} ({period_data['transaction_count']} transactions)
    Period Budget: ${period_budget:.2f} (approx.)
    Spending by Category (Total, Count): {json.dumps(period_data['category_spending'], indent=1)}
    Top 5 Largest Transactions: {json.dumps(period_data['top_transactions'], indent=1)}

    User's question: "{user_prompt}"

    Answer based ONLY on the summary. If details aren't present (e.g., specific transaction not in top 5), state that but offer analysis based on available data. """

    try:
        response = gemini_model.generate_content(system_instruction)
        bot_response = ""
        if response.parts: bot_response = "".join(part.text for part in response.parts).strip()
        elif response.prompt_feedback and response.prompt_feedback.block_reason: bot_response = f"Blocked: {response.prompt_feedback.block_reason}"
        else: bot_response = "Sorry, empty response."
        return jsonify({"response": bot_response})
    except Exception as e:
        error_detail = str(e)
        return jsonify({"response": f"Sorry, error generating analysis."}), 500

# Update an existing transaction
@app.route('/api/transactions/update', methods=['POST'])
def update_transaction_api():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    if not data or 'transaction_id' not in data:
        return jsonify({"error": "Missing transaction data"}), 400
    
    # Retreive updated data from fields
    transaction_id = data.get('transaction_id')
    amount = data.get('amount')
    description = data.get('description')
    date = data.get('date')
    category = data.get('category')
    account = data.get('account')
    
    # Find matching transaction and update data accordingly
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            
            cursor.execute("SELECT 1 FROM makes WHERE User_ID = %s AND Transaction_ID = %s", 
                          (user_id, transaction_id))
            if not cursor.fetchone():
                return jsonify({"error": "Transaction not found or access denied"}), 403
            
            cursor.execute("SELECT Transaction_Amount FROM transactions WHERE Transaction_ID = %s", 
                         (transaction_id,))
            old_amount_result = cursor.fetchone()
            old_amount = float(old_amount_result[0]) if old_amount_result else 0
            
            cursor.execute("SELECT Category_ID FROM categories WHERE Category_Name = %s", (category,))
            category_result = cursor.fetchone()
            if not category_result:
                return jsonify({"error": f"Category '{category}' not found"}), 400
            category_id = category_result[0]
            
            cursor.execute("UPDATE transactions SET Transaction_Amount = %s, Transaction_Description = %s, Transaction_Date = %s WHERE Transaction_ID = %s", (amount, description, date, transaction_id))
            
            cursor.execute("SELECT Category_ID FROM falls_under WHERE Transaction_ID = %s", (transaction_id,))
            current_category = cursor.fetchone()
            if current_category and current_category[0] != category_id:
                cursor.execute("UPDATE falls_under SET Category_ID = %s WHERE Transaction_ID = %s", 
                             (category_id, transaction_id))
            elif not current_category:
                cursor.execute("INSERT INTO falls_under (Transaction_ID, Category_ID) VALUES (%s, %s)", 
                             (transaction_id, category_id))
            
            amount_diff = float(old_amount) - float(amount)
            
            cursor.execute("SELECT Account_ID FROM made_on WHERE Transaction_ID = %s", (transaction_id,))
            current_account = cursor.fetchone()
            current_account_id = current_account[0] if current_account else None
            
            if current_account_id and str(current_account_id) != str(account):
                cursor.execute("UPDATE accounts SET Account_Balance = Account_Balance + %s WHERE Account_ID = %s", 
                             (old_amount, current_account_id))
                
                cursor.execute("UPDATE accounts SET Account_Balance = Account_Balance - %s WHERE Account_ID = %s", 
                             (amount, account))
                
                cursor.execute("UPDATE made_on SET Account_ID = %s WHERE Transaction_ID = %s", 
                             (account, transaction_id))
            else:
                cursor.execute("UPDATE accounts SET Account_Balance = Account_Balance + %s WHERE Account_ID = %s", 
                             (amount_diff, current_account_id if current_account_id else account))
            
            db.commit()
            return jsonify({"success": True, "message": "Transaction updated successfully"})
            
    except Exception as e:
        return jsonify({"error": f"Failed to update transaction: {str(e)}"}), 500

# Delete an existing transaction
@app.route('/api/transactions/delete/<int:transaction_id>', methods=['DELETE'])
def delete_transaction_api(transaction_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Find transaction and delete it
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            
            cursor.execute("SELECT t.Transaction_Amount, mo.Account_ID FROM transactions t JOIN makes m ON t.Transaction_ID = m.Transaction_ID LEFT JOIN made_on mo ON t.Transaction_ID = mo.Transaction_ID WHERE m.User_ID = %s AND t.Transaction_ID = %s", (user_id, transaction_id))
            
            transaction = cursor.fetchone()
            if not transaction:
                return jsonify({"error": "Transaction not found or access denied"}), 403
            
            amount = float(transaction[0]) if transaction[0] else 0
            account_id = transaction[1]
            
            if account_id:
                cursor.execute("UPDATE accounts SET Account_Balance = Account_Balance + %s WHERE Account_ID = %s", 
                             (amount, account_id))
            
            cursor.execute("DELETE FROM falls_under WHERE Transaction_ID = %s", (transaction_id,))
            cursor.execute("DELETE FROM made_on WHERE Transaction_ID = %s", (transaction_id,))
            cursor.execute("DELETE FROM makes WHERE Transaction_ID = %s", (transaction_id,))
            
            cursor.execute("DELETE FROM transactions WHERE Transaction_ID = %s", (transaction_id,))
            
            db.commit()
            return jsonify({"success": True, "message": "Transaction deleted successfully"})
            
    except Exception as e:
        return jsonify({"error": f"Failed to delete transaction: {str(e)}"}), 500

# Retrieve user's transactions
@app.route('/api/transactions')
def get_transactions_api():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    # Apply filters to search for transactions
    filter_category = request.args.get('category', None)
    filter_account = request.args.get('account', None)
    filter_start_date = request.args.get('start_date', None)
    filter_end_date = request.args.get('end_date', None)
    filter_description = request.args.get('description', None)
    filter_min_amount = request.args.get('min_amount', None)
    filter_max_amount = request.args.get('max_amount', None)
    filter_sort = request.args.get('sort', 'date_desc')

    where_clauses = ["m.User_ID = %s"]
    params = [user_id]

    if filter_category:
        where_clauses.append("c.Category_Name = %s")
        params.append(filter_category)
    if filter_account:
        where_clauses.append("a.Account_Name = %s")
        params.append(filter_account)
    if filter_start_date:
        where_clauses.append("t.Transaction_Date >= %s")
        params.append(filter_start_date)
    if filter_end_date:
        where_clauses.append("t.Transaction_Date <= %s")
        params.append(filter_end_date)
    if filter_description:
        where_clauses.append("t.Transaction_Description LIKE %s")
        params.append(f"%{filter_description}%")
    if filter_min_amount:
        where_clauses.append("t.Transaction_Amount >= %s")
        params.append(filter_min_amount)
    if filter_max_amount:
        where_clauses.append("t.Transaction_Amount <= %s")
        params.append(filter_max_amount)

    sql_where = " AND ".join(where_clauses)

    order_clause = ""
    if filter_sort == 'date_asc':
        order_clause = "ORDER BY t.Transaction_Date ASC, t.Transaction_ID ASC"
    elif filter_sort == 'amount_desc':
        order_clause = "ORDER BY t.Transaction_Amount DESC, t.Transaction_Date DESC"
    elif filter_sort == 'amount_asc':
        order_clause = "ORDER BY t.Transaction_Amount ASC, t.Transaction_Date DESC"
    else:
        order_clause = "ORDER BY t.Transaction_Date DESC, t.Transaction_ID DESC"

    query = f"SELECT t.Transaction_ID, t.Transaction_Date, t.Transaction_Description, t.Transaction_Amount, c.Category_Name, a.Account_Name FROM transactions t JOIN makes m ON t.Transaction_ID = m.Transaction_ID LEFT JOIN falls_under fu ON t.Transaction_ID = fu.Transaction_ID LEFT JOIN categories c ON fu.Category_ID = c.Category_ID LEFT JOIN made_on mo ON t.Transaction_ID = mo.Transaction_ID LEFT JOIN accounts a ON mo.Account_ID = a.Account_ID WHERE {sql_where} {order_clause}"

    transactions = []
    try:
        with get_db_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(query, params)
            transactions = cursor.fetchall()
            for t in transactions:
                if isinstance(t['Transaction_Date'], datetime.date):
                    t['Transaction_Date'] = t['Transaction_Date'].strftime('%Y-%m-%d')
            cursor.close()
        return jsonify(transactions)
    except Exception as e:
        return jsonify({"error": f"Failed to load transactions: {str(e)}"}), 500

# Load transactions to UI
@app.route('/manage_transaction')
def manage_transaction():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    if not check_setup_complete(user_id):
        flash('Please complete your account setup before managing transactions.', 'warning')
        return redirect(url_for('setup'))

    filter_categories = load_categories(user_id)
    
    accounts = []
    # Find user's transactions
    try:
        with get_db_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT Account_ID, Account_Name FROM accounts JOIN has USING (Account_ID) WHERE User_ID = %s", (user_id,))
            accounts = cursor.fetchall()            
            cursor.close()
    except Exception as e:
        flash('Could not load account data.', 'error')

    return render_template('manage_transaction.html', 
                          filter_categories=filter_categories,
                          accounts=accounts,
                          user_name=session.get('user_name', 'User'))

# Record new goal for user
@app.route('/record_goal', methods=['GET', 'POST'])
def record_goal():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    if request.method == 'POST':
        goal_name = request.form['goal_name']
        goal_target = request.form['goal_target']
        current_amount = request.form.get('current_amount', 0.00)
        goal_deadline = request.form['goal_deadline']
        goal_description = request.form.get('goal_description', '')

        # Create new goal
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("INSERT INTO goals (Goal_Name, Goal_Date, Goal_Target, Current_Amount, Goal_Description, Monthly_Budget) VALUES (%s, %s, %s, %s, %s, 0)", (goal_name, goal_deadline, goal_target, current_amount, goal_description))
                cursor.execute("SELECT LAST_INSERT_ID()")
                goal_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO sets (User_ID, Goal_ID) VALUES (%s, %s)", (user_id, goal_id))
                db.commit()
                cursor.close()
                flash('New goal added', 'success')
                return redirect(url_for('manage_goals'))
        except Exception as e:
            flash('Failed to record goal', 'error')

    return render_template('record_goal.html', user_name=session.get('user_name', 'User'))

# Manage user's goals
@app.route('/manage_goals')
def manage_goals():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    goals = []
    try:
        with get_db_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT Goal_ID, Goal_Name, Goal_Date, Goal_Target, Current_Amount, Goal_Description FROM goals g JOIN sets s USING(Goal_ID) WHERE s.User_ID = %s AND g.Monthly_Budget = 0 ORDER BY g.Goal_Date ASC, g.Goal_Name ASC", (user_id,))
            goals = cursor.fetchall()
            cursor.close()
    except Exception as e:
        flash('Could not load your goals.', 'error')

    return render_template('manage_goals.html',
                           goals=goals,
                           user_name=session.get('user_name', 'User'))

@app.route('/update_goal_progress', methods=['POST'])
def update_goal_progress():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    goal_id = request.form.get('goal_id')
    current_amount = request.form.get('current_amount')

    if not goal_id or current_amount is None:
        flash('Invalid data provided for update.', 'error')
        return redirect(url_for('manage_goals'))

# Update goal data accordingto    
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("SELECT 1 FROM sets WHERE User_ID = %s AND Goal_ID = %s", (user_id, goal_id))
            if not cursor.fetchone():
                 flash('Goal not found or access denied.', 'error')
            else:
                cursor.execute("UPDATE goals SET Current_Amount = %s WHERE Goal_ID = %s", (current_amount, goal_id))
                db.commit()
                flash('Goal progress updated.', 'success')
            cursor.close()
    except Exception as e:
        flash('Failed to update goal progress.', 'error')

    return redirect(url_for('manage_goals'))

# Delete a goal when the user selects delete on a goal
@app.route('/delete_goal/<int:goal_id>', methods=['POST'])
def delete_goal(goal_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("SELECT 1 FROM sets WHERE User_ID = %s AND Goal_ID = %s", (user_id, goal_id))
            if not cursor.fetchone():
                 flash('Goal not found or access denied.', 'error')
            else:
                cursor.execute("DELETE FROM sets WHERE User_ID = %s AND Goal_ID = %s", (user_id, goal_id))
                cursor.execute("DELETE FROM goals WHERE Goal_ID = %s", (goal_id,))
                db.commit()
                flash('Goal deleted successfully.', 'success')
            cursor.close()
    except Exception as e:
        flash('Failed to delete goal.', 'error')

    return redirect(url_for('manage_goals'))

# Edit and update the goal with new info based on what the user provides
@app.route('/edit_goal/<int:goal_id>', methods=['GET', 'POST'])
def edit_goal(goal_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    try:
        with get_db_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT g.* FROM goals g JOIN sets s ON g.Goal_ID = s.Goal_ID WHERE s.User_ID = %s AND g.Goal_ID = %s", (user_id, goal_id))
            goal = cursor.fetchone()
            cursor.close()
            
            if not goal:
                flash('Goal not found or access denied.', 'error')
                return redirect(url_for('manage_goals'))
                
    except Exception as e:
        flash('Could not load goal details.', 'error')
        return redirect(url_for('manage_goals'))
    
    if request.method == 'POST':
        goal_name = request.form['goal_name']
        goal_target = request.form['goal_target']
        goal_deadline = request.form['goal_deadline']
        goal_description = request.form.get('goal_description', '')
        
        try:
            with get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("UPDATE goals SET Goal_Name = %s, Goal_Target = %s, Goal_Date = %s, Goal_Description = %s WHERE Goal_ID = %s", (goal_name, goal_target, goal_deadline, goal_description, goal_id))
                db.commit()
                cursor.close()
                flash('Goal updated successfully.', 'success')
                return redirect(url_for('manage_goals'))
        except Exception as e:
            flash('Failed to update goal. Please try again.', 'error')
    
    return render_template('edit_goal.html', goal=goal, user_name=session.get('user_name', 'User'))

# Manage accounts allows users to add different types of accounts such as savings, checkings, etc.
@app.route('/manage_accounts')
def manage_accounts():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    accounts = []
    try:
        with get_db_connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT Account_ID, Account_Name, Account_Type, Account_Balance FROM accounts a JOIN has h USING(Account_ID) WHERE h.User_ID = %s ORDER BY a.Account_Name ASC", (user_id,))
            accounts = cursor.fetchall()
            cursor.close()
    except Exception as e:
        flash('Could not load your accounts.', 'error')

    return render_template('manage_accounts.html',
                           accounts=accounts,
                           user_name=session.get('user_name', 'User'))

# Add account works when user clicks add account from manage account
@app.route('/add_account', methods=['POST'])
def add_account():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    account_name = request.form.get('account_name')
    account_type = request.form.get('account_type')
    account_balance = request.form.get('account_balance')

    if not all([account_name, account_type, account_balance is not None]):
        flash('Missing account information.', 'error')
        return redirect(url_for('manage_accounts'))

    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO accounts (Account_Name, Account_Type, Account_Balance) VALUES (%s, %s, %s)", (account_name, account_type, account_balance))
            cursor.execute("SELECT LAST_INSERT_ID()")
            account_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO has (User_ID, Account_ID) VALUES (%s, %s)", (user_id, account_id))
            db.commit()
            cursor.close()
            flash('Account added successfully.', 'success')
    except Exception as e:
        flash('Failed to add account.', 'error')

    return redirect(url_for('manage_accounts'))

# Edit accounts updates the account based on new info
@app.route('/edit_account/<int:account_id>', methods=['POST'])
def edit_account(account_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    account_name = request.form.get('account_name')
    account_type = request.form.get('account_type')
    account_balance = request.form.get('account_balance')

    if not all([account_name, account_type, account_balance is not None]):
        flash('Missing account information for update.', 'error')
        return redirect(url_for('manage_accounts'))

    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("SELECT 1 FROM has WHERE User_ID = %s AND Account_ID = %s", (user_id, account_id))
            if not cursor.fetchone():
                 flash('Account not found or access denied.', 'error')
            else:
                cursor.execute("UPDATE accounts SET Account_Name = %s, Account_Type = %s, Account_Balance = %s WHERE Account_ID = %s", (account_name, account_type, account_balance, account_id))
                db.commit()
                flash('Account updated successfully.', 'success')
            cursor.close()
    except Exception as e:
        flash('Failed to update account.', 'error')

    return redirect(url_for('manage_accounts'))

# Delete account will delete the selected account
@app.route('/delete_account/<int:account_id>', methods=['POST'])
def delete_account(account_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("SELECT 1 FROM has WHERE User_ID = %s AND Account_ID = %s", (user_id, account_id))
            if not cursor.fetchone():
                 flash('Account not found or access denied.', 'error')
            else:
                cursor.execute("SELECT 1 FROM made_on WHERE Account_ID = %s LIMIT 1", (account_id,))
                if cursor.fetchone():
                    flash('Cannot delete account because it has associated transactions. Reassign transactions first.', 'warning')
                else:
                    cursor.execute("DELETE FROM has WHERE User_ID = %s AND Account_ID = %s", (user_id, account_id))
                    cursor.execute("DELETE FROM accounts WHERE Account_ID = %s", (account_id,))
                    db.commit()
                    flash('Account deleted successfully.', 'success')
            cursor.close()
    except Exception as e:
        flash(f'Failed to delete account: {e}', 'error')

    return redirect(url_for('manage_accounts'))

if __name__ == '__main__':
     app.run(debug=True, host="0.0.0.0", port=5000)