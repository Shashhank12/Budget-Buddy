# Project Title: Budget Buddy
### Project Members
* Timothy Chan (TimothyChan2912)
* Shashhank Seethula (Shashhank12)

## Brief Description
Our application was designed to help users manage their finances through different features such as data visualization, AI recommendations, etc. Users can set goals, track spendings by adding various transactions, and make smarter financial decisions.

## Dependencies
* Anaconda
    * Python 3.12
* MySQL 8.0.41 (Workbench, Server)
* JavaScript

## Setup and Execution
1. Ensure that the required dependencies are installed and accessible through the command line. (Anaconda, MySQL, JavaScript, Python are accessible through the command line). 
2. Extract the zip file to a local directory.
3. Setup the MySQL server and make sure you save the credentials such as username, password, and database port, database host. For example, you should have the following information. This website also provides more info on how to set up MySQL Server and Workbench: https://www.simplilearn.com/tutorials/mysql-tutorial/mysql-workbench-installation:
```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=budget-buddy
DB_PORT=3306
```
4. Login to your MySQL Workbench using your credentials. Find the Administration tab and select Data Import/Restore. Select the file budgetbuddydb.sql in the src directory of the zip file. Under import from disk, select import from a self-contained file. Select the file budgetbuddydb.sql. Go to the Import Progress tab and select Start Import. This should give all the necessary tables to run the application.
5. Copy the code files from the src folder to a desired directory.
6. Now set up the .env file in the project files using desired credentials and database information. For the Gemini API key, you can use the given key or generate one to your liking. Your .env file should look something like this:
```
FLASK_SECRET_KEY=KEY_HERE
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=budget-buddy
DB_NAME=budget_buddy
DB_PORT=3306
GEMINI_API_KEY=API_KEY_HERE
```
7. Run the following commands wherever Anaconda is accessible (Terminal, Anaconda Prompt, or Command Prompt). Ensure that the command line is in the same directory as the code files. This should make the web application accessible through localhost:5000. 
```
conda env create -f environment.yml
conda activate py312budgetbuddy
python app.py
```

## File Structure Overview
JS, CSS, HTML files used for frontend; app.py (Python) used for backend.
* HTML files are located in the templates folder.
* CSS files are located in the static/css folder.
* JS files are located in the static/js folder.
* Python files are located in the src folder.
* The database file is located in the src folder.
* The environment file is located in the src folder for Anaconda to read the dependencies.
* The .sql file is located in the src folder for MySQL to read the database structure.

## Known Bugs or Limitations
* Prediction analysis based on linear trends/patterns rather than complex models capturing non-linear relationships. 
* This application is not tested on all devices and screen sizes.
* The Prediction feature is not very informative if there isn't much data.