from flask import Flask, render_template
import mysql.connector
app = Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="PASSWORD",
    database="budget_buddy",
    port="3306"
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/users')
def users():
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    return str(users)

app.run(debug=True)