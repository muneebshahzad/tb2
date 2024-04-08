import pyodbc
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import datetime, random
from datetime import datetime
import os
import pymssql
import lazop
client = lazop.LazopClient('https://api.daraz.pk/rest', '501554', 'nrP3XFN7ChZL53cXyVED1yj4iGZZtlcD')
app = Flask(__name__)
@app.route('/d')
def daraz():
    # Render the daraz.html template
    return render_template('daraz.html')


@app.route('/daraz', methods=['GET'])
def daraz_callback():
    # Extract the authorization code from the callback URL
    code = request.args.get('code')

    # Create a Lazop request to exchange authorization code for access token
    request = lazop.LazopRequest('/auth/token/create', 'GET')
    request.add_api_param('code', code)

    # Execute the request and get the response
    response = client.execute(request)

    # Return the access token response
    return jsonify(response.body)


# Accessing environment variable
database_url = os.environ.get('DATABASE_URL')

# Print the value
print(f'DATABASE_URL: {database_url}')
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure secret key

# Store IDs globally for reuse
global_ids = {'income_id': None, 'payment_by': None, 'payment_to': None}

# Store IDs globally for reuse
global_ids_expense = {'expense_id': None, 'payment_by': None, 'payment_to': None}

mon = datetime.now().strftime("%B")
def check_database_connection():
    server = 'tickbags.database.windows.net'
    database = 'TickBags'
    username = 'tickbags_ltd'
    password = 'TB@2024!'

    try:
        print('Connecting to the database...')
        connection = pymssql.connect(server=server, user=username, password=password, database=database)
        print('Connected to the database')
        return connection
    except pymssql.Error as e:
        print(f"Error connecting to the database: {str(e)}")
        return None

def execute_query(connection, query, params=None, fetchall=False, as_dict=False):
    cursor = connection.cursor()

    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if fetchall:
            if as_dict:
                columns = [column[0] for column in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            else:
                return cursor.fetchall()
        else:
            return None

    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return None

    finally:
        cursor.close()

@app.before_request
def require_login():
    print('Endpoint:', request.endpoint)
    allowed_routes = ['login', 'static']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        print('Redirecting to login')
        return redirect(url_for('login'))
##LOGIN

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        print('Login POST request received')
        username = request.form.get('username')
        password = request.form.get('password')

        # Assuming you have a SQL Server database connection
        connection = check_database_connection()

        try:
            if connection:
                cursor = connection.cursor()
                query = "SELECT * FROM users WHERE username = %s AND password = %s"
                cursor.execute(query, (username, password))
                user = cursor.fetchone()

                if user:
                    # If the user exists, store their information in the session
                    session['user_id'] = user[0]  # Assuming user_id is the first column
                    session['username'] = user[1]  # Assuming username is the second column
                    # You can store more user-related information in the session if needed

                    return redirect(url_for('home'))  # Redirect to the home page or another authenticated route
                else:
                    # If the login fails, you can show an error message
                    error_message = "Invalid username or password"
                    return render_template('Login1.html', error_message=error_message)
            else:
                return "Error: No database connection"

        except Exception as e:
            print(f"Error during login: {str(e)}")
            return "Error during login"

        finally:
            if connection:
                connection.close()

    return render_template('Login1.html')

def get_income_types(connection):
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM income_type')
    types = cursor.fetchall()
    cursor.close()
    return types

def get_expense_types(connection):
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM expense_type')
    types = cursor.fetchall()
    cursor.close()
    return types


def fetch_source_data(connection, income_type):
    cursor = connection.cursor()

    try:
        if income_type == "Sales":
            cursor.execute('SELECT vendor_name FROM income_vendors')
        elif income_type == "Investments":
            cursor.execute('SELECT owner_name FROM owners')
        elif income_type == "Loans Recovery":
            cursor.execute('SELECT accounts_name FROM accounts')
        else:
            return []  # Handle other cases or return an empty list

        data = [row[0] for row in cursor.fetchall()]
        return data

    except Exception as e:
        print(f"Error fetching source data: {str(e)}")
        return []

    finally:
        cursor.close()

def fetch_payment_to_data(connection, expense_type):
    cursor = connection.cursor()

    try:
        if expense_type == "Profit Withdrawal":
            cursor.execute('SELECT DISTINCT owner_name FROM owners')  # Use DISTINCT to eliminate duplicates
        elif expense_type == "Other":
            # Show "Other" option
            return ["Other"]
        elif expense_type == "Employee Salary" or expense_type == "Employee Loan":
            cursor.execute('SELECT DISTINCT employee_name FROM employees')  # Use DISTINCT to eliminate duplicates
        elif expense_type == "Website & Advertising":
            # Display specific options for Website & Advertising
            return ["Facebook", "Shopify", "Google", "Godaddy"]
        elif expense_type == "Raw Material Purchasing":
            # Display options from expense_title in expense_vendors for Raw Material Purchasing
            cursor.execute('SELECT DISTINCT expense_title FROM expense_vendors ')
        elif expense_type == "Employee Expense":
            # Display specific options for Employee Expense
            return ["Food", "Other"]
        elif expense_type == "Office expenses and supplies":
            # Display specific options for Office expenses and supplies
            return ["Rent", "Utilities", "Other"]
        else:
            return []  # Handle other cases or return an empty list

        data = [row[0] for row in cursor.fetchall()]
        return data

    except Exception as e:
        print(f"Error fetching payment to data: {str(e)}")
        return []

    finally:
        cursor.close()


def add_X_to_accounts(connection, received_by):
    cursor = connection.cursor()

    try:
        cursor.execute('INSERT INTO accounts (accounts_name) VALUES (%s)', received_by)
        connection.commit()
        return True

    except Exception as e:
        print(f"Error adding 'X' to accounts: {str(e)}")
        connection.rollback()
        return False

    finally:
        cursor.close()


def get_ids(connection, income_type, payment_via, received_by):
    global global_ids  # Use the global variable

    cursor = connection.cursor()

    try:
        income_id, payment_by, payment_to = None, None, None

        if global_ids['income_id'] is not None:
            # If values are already fetched, use them
            income_id = global_ids['income_id']
            payment_by = global_ids['payment_by']
            payment_to = global_ids['payment_to']
        else:
            # Fetch values only if not already fetched
            cursor.execute('SELECT income_id FROM income_type WHERE income_title = %s', income_type)
            result = cursor.fetchone()
            if result:
                income_id = result[0]

            cursor.execute('SELECT account_id FROM accounts WHERE accounts_name = %s', payment_via)
            result = cursor.fetchone()
            if result:
                payment_by = result[0]

            cursor.execute('SELECT account_id FROM accounts WHERE accounts_name = %s', received_by)
            result = cursor.fetchone()
            if result:
                payment_to = result[0]

            # Update global variable with fetched values
            global_ids = {'income_id': income_id, 'payment_by': payment_by, 'payment_to': payment_to}

        print(f"After get_ids  line 96- Income ID: {income_id}, Payment By: {payment_by}, Payment To: {payment_to}")

        return {'income_id': income_id, 'payment_by': payment_by, 'payment_to': payment_to}

    except Exception as e:
        print(f"Error fetching IDs: {str(e)}")
        return {'income_id': None, 'payment_by': None, 'payment_to': None}

    finally:
        cursor.close()

def get_expense_ids(connection, income_type, payment_via, received_by):
    global global_ids  # Use the global variable

    cursor = connection.cursor()

    try:
        income_id, payment_by, payment_to = None, None, None

        if global_ids['income_id'] is not None:
            # If values are already fetched, use them
            income_id = global_ids['income_id']
            payment_by = global_ids['payment_by']
            payment_to = global_ids['payment_to']
        else:
            # Fetch values only if not already fetched
            cursor.execute('SELECT expense_id FROM expense_type WHERE expense_title = %s', income_type)
            result = cursor.fetchone()
            if result:
                income_id = result[0]

            cursor.execute('SELECT account_id FROM accounts WHERE accounts_name = %s', payment_via)
            result = cursor.fetchone()
            if result:
                payment_by = result[0]

            cursor.execute('SELECT account_id FROM accounts WHERE accounts_name = %s', received_by)
            result = cursor.fetchone()
            if result:
                payment_to = result[0]

            # Update global variable with fetched values
            global_ids = {'income_id': income_id, 'payment_by': payment_by, 'payment_to': payment_to}

        print(f"After get_ids  line 96- Income ID: {income_id}, Payment By: {payment_by}, Payment To: {payment_to}")

        return {'income_id': income_id, 'payment_by': payment_by, 'payment_to': payment_to}

    except Exception as e:
        print(f"Error fetching IDs: {str(e)}")
        return {'income_id': None, 'payment_by': None, 'payment_to': None}

    finally:
        cursor.close()

def add_transaction(connection, amount, income_id, source, description, payment_by, payment_to):
    cursor = connection.cursor()
    try:
        print(f"Before add_transaction line 112 - Income ID: {income_id}, Payment By: {payment_by}, Payment To: {payment_to}")

        submission_datetime = datetime.now()

        cursor.execute(
            'INSERT INTO Transactions (amount, income_id, source, description, payment_by, payment_to, submission_datetime, type) VALUES (%s, %s, %s, %s, %s, %s, %s, 1)',
            (amount, income_id, source, description, payment_by, payment_to, submission_datetime)
        )
        print("executed")
        cursor.execute('UPDATE accounts SET accounts_balance = accounts_balance + %s WHERE account_id = %s', (amount, payment_by))

        if income_id ==2:
            cursor.execute('UPDATE accounts SET accounts_balance = accounts_balance - %s WHERE accounts_name = %s',
                           (amount, source))

        global_ids = {'income_id': None, 'payment_by': None, 'payment_to': None}

        connection.commit()
        return True

    except Exception as e:
        print(f"Error adding transaction: {str(e)}")
        connection.rollback()
        return False

    finally:
        cursor.close()




def get_income_types(connection):
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM income_type')
    types = cursor.fetchall()
    cursor.close()
    return types

def get_expense_types(connection):
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM expense_type')
    types = cursor.fetchall()
    cursor.close()
    return types


def fetch_source_data(connection, income_type):
    cursor = connection.cursor()

    try:
        if income_type == "Sales":
            cursor.execute('SELECT vendor_name FROM income_vendors')
        elif income_type == "Investments":
            cursor.execute('SELECT owner_name FROM owners')
        elif income_type == "Loans Recovery":
            cursor.execute('SELECT accounts_name FROM accounts')
        else:
            return []  # Handle other cases or return an empty list

        data = [row[0] for row in cursor.fetchall()]
        return data

    except Exception as e:
        print(f"Error fetching source data: {str(e)}")
        return []

    finally:
        cursor.close()

def fetch_payment_to_data(connection, expense_type):
    cursor = connection.cursor()

    try:
        if expense_type == "Profit Withdrawal":
            cursor.execute('SELECT DISTINCT owner_name FROM owners')  # Use DISTINCT to eliminate duplicates
        elif expense_type == "Other":
            # Show "Other" option
            return ["Other"]
        elif expense_type == "Employee Salary" or expense_type == "Employee Loan":
            cursor.execute('SELECT DISTINCT employee_name FROM employees')  # Use DISTINCT to eliminate duplicates
        elif expense_type == "Website & Advertising":
            # Display specific options for Website & Advertising
            return ["Facebook", "Shopify", "Google", "Godaddy"]
        elif expense_type == "Raw Material Purchasing":
            # Display options from expense_title in expense_vendors for Raw Material Purchasing
            cursor.execute('SELECT DISTINCT expense_title FROM expense_vendors ')
        elif expense_type == "Employee Expense":
            # Display specific options for Employee Expense
            return ["Food", "Other"]
        elif expense_type == "Office expenses and supplies":
            # Display specific options for Office expenses and supplies
            return ["Rent", "Utilities", "Other"]
        else:
            return []  # Handle other cases or return an empty list

        data = [row[0] for row in cursor.fetchall()]
        return data

    except Exception as e:
        print(f"Error fetching payment to data: {str(e)}")
        return []

    finally:
        cursor.close()


def add_X_to_accounts(connection, received_by):
    cursor = connection.cursor()

    try:
        cursor.execute('INSERT INTO accounts (accounts_name) VALUES (%s)', received_by)
        connection.commit()
        return True

    except Exception as e:
        print(f"Error adding 'X' to accounts: {str(e)}")
        connection.rollback()
        return False

    finally:
        cursor.close()


def get_ids(connection, income_type, payment_via, received_by):
    global global_ids  # Use the global variable

    cursor = connection.cursor()

    try:
        income_id, payment_by, payment_to = None, None, None

        if global_ids['income_id'] is not None:
            # If values are already fetched, use them
            income_id = global_ids['income_id']
            payment_by = global_ids['payment_by']
            payment_to = global_ids['payment_to']
        else:
            # Fetch values only if not already fetched
            cursor.execute('SELECT income_id FROM income_type WHERE income_title = %s', income_type)
            result = cursor.fetchone()
            if result:
                income_id = result[0]

            cursor.execute('SELECT account_id FROM accounts WHERE accounts_name = %s', payment_via)
            result = cursor.fetchone()
            if result:
                payment_by = result[0]

            cursor.execute('SELECT account_id FROM accounts WHERE accounts_name = %s', received_by)
            result = cursor.fetchone()
            if result:
                payment_to = result[0]

            # Update global variable with fetched values
            global_ids = {'income_id': income_id, 'payment_by': payment_by, 'payment_to': payment_to}

        print(f"After get_ids  line 96- Income ID: {income_id}, Payment By: {payment_by}, Payment To: {payment_to}")

        return {'income_id': income_id, 'payment_by': payment_by, 'payment_to': payment_to}

    except Exception as e:
        print(f"Error fetching IDs: {str(e)}")
        return {'income_id': None, 'payment_by': None, 'payment_to': None}

    finally:
        cursor.close()

def get_expense_ids(connection, expense_type, payment_via, received_by):
    global global_ids_expense

    cursor = connection.cursor()

    try:
        expense_id, payment_by, payment_to = None, None, None

        if global_ids_expense['expense_id'] is not None:
            # If values are already fetched, use them
            expense_id = global_ids_expense['expense_id']
            payment_by = global_ids_expense['payment_by']
            payment_to = global_ids_expense['payment_to']
        else:
            # Fetch values only if not already fetched
            cursor.execute('SELECT expense_id FROM expense_type WHERE expense_title = %s', expense_type)
            result = cursor.fetchone()
            if result:
                expense_id = result[0]

            cursor.execute('SELECT account_id FROM accounts WHERE accounts_name = %s', payment_via)
            result = cursor.fetchone()
            if result:
                payment_by = result[0]

            cursor.execute('SELECT account_id FROM accounts WHERE accounts_name = %s', received_by)
            result = cursor.fetchone()
            if result:
                payment_to = result[0]

            # Update global variable with fetched values
            global_ids_expense = {'expense_id': expense_id, 'payment_by': payment_by, 'payment_to': payment_to}

        print(f"After get_expense_ids line 96 - Expense ID: {expense_id}, Payment By: {payment_by}, Payment To: {payment_to}")

        return {'expense_id': expense_id, 'payment_by': payment_by, 'payment_to': payment_to}

    except Exception as e:
        print(f"Error fetching Expense IDs: {str(e)}")
        return {'expense_id': None, 'payment_by': None, 'payment_to': None}

    finally:
        cursor.close()

def check_source_exists(connection, source):
    cursor = connection.cursor()

    try:
        cursor.execute(
            '''
            SELECT COUNT(*) AS source_exists
            FROM accounts
            WHERE accounts_name = %s 
              AND accounts_name NOT IN ('Bank', 'Cash');
            ''',
            source
        )

        result = cursor.fetchone()
        source_exists = result[0] if result else 0

        return source_exists == 1

    except Exception as e:
        print(f"Error checking source: {str(e)}")
        return False

    finally:
        cursor.close()
def add_expense_transaction(connection, amount, expense_id, source, description, payment_by, payment_to):
    cursor = connection.cursor()
    global global_ids_expense

    try:
        submission_datetime = datetime.now()

        # Check if the source is included in the accounts table and is not "Bank" or "Cash"
        source_exists = check_source_exists(connection, source)

        cursor.execute(
            '''
            INSERT INTO Transactions (amount, income_id, source, description, payment_by, payment_to, submission_datetime, type) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, -1)
            ''',
            (amount, expense_id, source, description, payment_by, payment_to, submission_datetime)
        )

        cursor.execute('UPDATE accounts SET accounts_balance = accounts_balance - %s WHERE account_id = %s',
                       (amount, payment_by))

        if expense_id ==5 or expense_id ==7:
            cursor.execute('UPDATE accounts SET accounts_balance = accounts_balance + %s WHERE accounts_name = %s',
                           (amount, source))


        connection.commit()
        global_ids_expense = {'expense_id': None, 'payment_by': None, 'payment_to': None}

        return True

    except Exception as e:
        print(f"Error adding transaction: {str(e)}")
        connection.rollback()
        return False

    finally:
        cursor.close()


@app.route('/get_source_data', methods=['POST'])
def get_source_data():
    connection = check_database_connection()

    try:
        if connection:
            income_type = request.form.get('type')
            data = fetch_source_data(connection, income_type)
            return jsonify(data)
        else:
            return jsonify([])

    except Exception as e:
        print(f"Error fetching source data: {str(e)}")
        return jsonify([])

    finally:
        if connection:
            connection.close()

@app.route('/get_payment_to_data', methods=['POST'])
def get_payment_to_data():
    connection = check_database_connection()

    try:
        if connection:
            expense_type = request.form.get('type')  # Update variable name to expense_type
            data = fetch_payment_to_data(connection, expense_type)
            return jsonify(data)
        else:
            return jsonify([])

    except Exception as e:
        print(f"Error fetching payment to data: {str(e)}")
        return jsonify([])

    finally:
        if connection:
            connection.close()


@app.route('/')
def home():
    print(f'DATABASE_URL: {database_url}')

    return render_template("index.html", month=mon)




@app.route('/add_income', methods=['GET', 'POST'])
def add_income():
    if request.method == 'GET':
        connection = check_database_connection()
        income_types = []

        if connection:
            income_types = get_income_types(connection)
            connection.close()

        return render_template("add_income.html", income_types=income_types)


    elif request.method == 'POST':

        amount = request.form.get('amount')

        income_id = request.form.get('type')

        source = request.form.get('source')

        description = request.form.get('description', '')

        payment_by = request.form.get('paymentVia')

        received_by = request.form.get('receivedBy')

        if not income_id or not payment_by or not received_by:
            return "Error: Missing required parameters"

        connection = check_database_connection()

        try:

            if connection:

                print("In add income")

                ids = get_ids(connection, income_id, payment_by, received_by)

                print("after add income")

                print(
                    f"Before add_transaction line 190 - Income ID: {ids['income_id']}, Payment By: {ids['payment_by']}, Payment To: {ids['payment_to']}")

                # Set the values obtained from get_ids

                income_id = ids['income_id']

                payment_by = ids['payment_by']

                payment_to = ids['payment_to']

                print(
                    f"After get_ids in add_income 196 - Income ID: {income_id}, Payment By: {payment_by}, Payment To: {payment_to}")

                success = add_transaction(connection, amount, income_id, source, description, payment_by, payment_to)

                if success:

                    return "Form submitted successfully"

                else:

                    return "Error submitting form"


            else:

                return "Error: No database connection"


        except Exception as e:

            print(f"Error in add_income: {str(e)}")

            return "Error in add_income"


        finally:

            if connection:
                connection.close()





@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'GET':
        connection = check_database_connection()
        expense_types = []

        if connection:
            expense_types = get_expense_types(connection)
            connection.close()

        return render_template("add_expense.html", expense_types=expense_types)

    elif request.method == 'POST':
        amount = request.form.get('amount')
        expense_type = request.form.get('type')
        source = request.form.get('source')
        description = request.form.get('description', '')
        payment_by = request.form.get('paymentVia')
        received_by = request.form.get('receivedBy')

        if not expense_type or not payment_by or not received_by:
            return "Error: Missing required parameters"

        connection = check_database_connection()

        try:
            if connection:
                print("In add_expense")

                ids = get_expense_ids(connection, expense_type, payment_by, received_by)

                print("after add_expense")

                print(
                    f"Before add_expense_transaction line 190 - Expense ID: {ids['expense_id']}, Payment By: {ids['payment_by']}, Payment To: {ids['payment_to']}")

                # Set the values obtained from get_expense_ids
                expense_id = ids['expense_id']
                payment_by = ids['payment_by']
                payment_to = ids['payment_to']

                print(
                    f"After get_expense_ids in add_expense 196 - Expense ID: {expense_id}, Payment By: {payment_by}, Payment To: {payment_to}")

                success = add_expense_transaction(connection, amount, expense_id, source, description, payment_by, payment_to)

                if success:
                    return "Form submitted successfully"
                else:
                    return "Error submitting form"
            else:
                return "Error: No database connection"

        except Exception as e:
            print(f"Error in add_expense: {str(e)}")
            return "Error in add_expense"

        finally:
            if connection:
                connection.close()




@app.route('/get_ids', methods=['POST'])
def get_ids_route():
    connection = check_database_connection()

    try:
        if connection:
            income_type = request.form.get('type')
            payment_via = request.form.get('paymentVia')
            received_by = request.form.get('receivedBy')

            if not income_type:
                income_type = "Sales"
            if not payment_via:
                payment_via = "Bank"
            ids = get_ids(connection, income_type, payment_via, received_by)
            print(jsonify(ids))
            return jsonify(ids)
        else:
            return jsonify({})

    except Exception as e:
        print(f"Error fetching IDs: {str(e)}")
        return jsonify({})

    finally:
        if connection:
            connection.close()


@app.route('/get_expense_ids', methods=['POST'])
def get_expense_ids_route():
    connection = check_database_connection()

    try:
        if connection:
            income_type = request.form.get('type')
            payment_via = request.form.get('paymentVia')
            received_by = request.form.get('receivedBy')

            if not income_type:
                income_type = "Other"
            if not payment_via:
                payment_via = "Bank"
            ids = get_expense_ids(connection, income_type, payment_via, received_by)
            print(jsonify(ids))
            return jsonify(ids)
        else:
            return jsonify({})

    except Exception as e:
        print(f"Error fetching IDs: {str(e)}")
        return jsonify({})

    finally:
        if connection:
            connection.close()











##HOME


@app.route('/get_income_this_month', methods=['GET'])
def get_income_this_month():
    connection = check_database_connection()

    try:
        if connection:
            data = fetch_income_this_month(connection)
            return jsonify(data)

        return jsonify(0)  # Default value if no connection

    except Exception as e:
        print(f"Error fetching income this month data: {str(e)}")
        return jsonify(0)  # Default value in case of an error

    finally:
        if connection:
            connection.close()




@app.route('/get_expenses_this_month', methods=['GET'])
def get_expenses_this_month():
    connection = check_database_connection()

    try:
        if connection:
            data = fetch_expenses_this_month(connection)
            return jsonify(data)

        return jsonify(0)  # Default value if no connection

    except Exception as e:
        print(f"Error fetching expenses this month data: {str(e)}")
        return jsonify(0)  # Default value in case of an error

    finally:
        if connection:
            connection.close()


def fetch_expenses_this_month(connection):
    cursor = connection.cursor()
    expenses = 0  # Initialize expenses

    try:
        current_month = datetime.now().month
        current_year = datetime.now().year

        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions 
            WHERE type = -1
            AND MONTH(submission_datetime) = %s
            AND YEAR(submission_datetime) = %s
        """, (current_month, current_year))

        data = cursor.fetchone()
        expenses = data[0] if data and data[0] is not None else 0
        print(f"The expenses: {expenses}")
        return expenses

    except Exception as e:
        print(f"Error fetching expenses this month data: {str(e)}")
        return expenses

    finally:
        cursor.close()

def fetch_income_this_month(connection):
    cursor = connection.cursor()
    income = 0  # Initialize income

    try:
        current_month = datetime.now().month
        current_year = datetime.now().year

        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) AS income
            FROM transactions 
            WHERE type = 1
            AND MONTH(submission_datetime) = %s
            AND YEAR(submission_datetime) = %s
        """, (current_month, current_year))

        data = cursor.fetchone()
        income = data[0] if data and data[0] is not None else 0
        print(f"The income: {income}")
        return income

    except Exception as e:
        print(f"Error fetching income this month data: {str(e)}")
        return income

    finally:
        cursor.close()

@app.route('/get_net_profit_this_month', methods=['GET'])
def get_net_profit_this_month():
    connection = check_database_connection()

    try:
        if connection:
            net_profit = fetch_net_profit_this_month(connection)
            return jsonify(net_profit)

        return jsonify(0)  # Default value if no connection

    except Exception as e:
        print(f"Error fetching net profit this month data: {str(e)}")
        return jsonify(0)  # Default value in case of an error

    finally:
        if connection:
            connection.close()


def fetch_net_profit_this_month(connection):
    cursor = connection.cursor()
    net_profit = 0

    try:
        current_month = datetime.now().month
        current_year = datetime.now().year

        cursor.execute("""
            SELECT SUM(amount * type)
            FROM transactions
            WHERE MONTH(submission_datetime) = %s
            AND YEAR(submission_datetime) = %s
            AND income_id != 7
        """, (current_month, current_year))

        data = cursor.fetchone()
        net_profit = data[0] if data and data[0] is not None else 0
        net_profit = round(net_profit, 1)
        print(f"The net profit: {net_profit}")
        return net_profit

    except Exception as e:
        print(f"Error fetching net profit this month data: {str(e)}")
        return net_profit

    finally:
        cursor.close()


@app.route('/get_cash_on_hand', methods=['GET'])
def get_cash_on_hand():
    connection = check_database_connection()

    try:
        if connection:
            data = fetch_cash_on_hand(connection)
            return jsonify(data)

        return jsonify(0)  # Default value if no connection

    except Exception as e:
        print(f"Error fetching cash on hand data: {str(e)}")
        return jsonify(0)  # Default value in case of an error

    finally:
        if connection:
            connection.close()


def fetch_cash_on_hand(connection):
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT COALESCE(SUM(accounts_balance), 0) "
                       "FROM accounts WHERE accounts_name IN ('Cash', 'Bank')")
        data = cursor.fetchone()
        cash_on_hand = data[0] if data and data[0] is not None else 0
        cash_on_hand_rounded = round(cash_on_hand, 1)  # Round to one decimal place
        return cash_on_hand_rounded

    except Exception as e:
        print(f"Error fetching cash on hand data: {str(e)}")
        return 0

    finally:
        cursor.close()


##HOME

##EXPENSES_LIST

@app.route('/expenses_list')
def expenses_list():
    connection = check_database_connection()

    try:
        if connection:
            # Fetch expenses data from your database
            expenses_data = fetch_expenses_data(connection)
            return render_template('expenses_list.html', expenses_data=expenses_data)
        else:
            return "Error: No database connection"

    except Exception as e:
        print(f"Error in expenses_list route: {str(e)}")
        return "Error in expenses_list route"

    finally:
        if connection:
            connection.close()

# Function to fetch expenses data from the database

def fetch_expenses_data(connection):
    cursor = connection.cursor()

    try:
        cursor.execute('SELECT income_id, source, payment_by, payment_to, submission_datetime, amount, type FROM Transactions')
        expenses_data = cursor.fetchall()

        formatted_expenses = []

        for row in expenses_data:
            if row[6] == -1:
                # Fetch expense category from expense_type table using income_id
                print(row[0])
                cursor.execute('SELECT expense_title FROM expense_type WHERE expense_id = %s', (row[0],))
                data = cursor.fetchone()
                category = data[0] if data and data[0] is not None else None
                print(category)

                # Fetch payment method from accounts table using payment_by
                cursor.execute('SELECT accounts_name FROM accounts WHERE account_id = %s', (row[2],))
                data = cursor.fetchone()
                payment_method = data[0] if data and data[0] is not None else None

                # Fetch payment by from accounts table using payment_to
                cursor.execute('SELECT accounts_name FROM accounts WHERE account_id = %s', (row[3],))
                data = cursor.fetchone()
                payment_by = data[0] if data and data[0] is not None else None

                formatted_expense = {
                    'expense_category': category,
                    'sub_category': row[1],  # Assuming source represents sub-category
                    'amount': row[5],
                    'payment_method': payment_method,
                    'payment_by': payment_by,
                    'submission_datetime': row[4]
                }

                formatted_expenses.append(formatted_expense)

        return formatted_expenses

    except Exception as e:
        print(f"Error fetching expenses data: {str(e)}")
        return []

    finally:
        cursor.close()
def get_filtered_expenses_data(connection, from_date, to_date):
    cursor = connection.cursor()

    try:
        # Convert input date strings to datetime objects with a specific format
        from_date = datetime.strptime(from_date, "%Y-%m-%d").strftime("%Y-%m-%d 00:00:00")
        to_date = datetime.strptime(to_date, "%Y-%m-%d").strftime("%Y-%m-%d 23:59:59")

        # Execute the SQL query
        query = 'SELECT income_id, source, payment_by, payment_to, submission_datetime, amount, type ' \
                'FROM Transactions ' \
                'WHERE submission_datetime BETWEEN %s AND %s AND type = -1'
        cursor.execute(query, (from_date, to_date))
        expenses_data = cursor.fetchall()

        # Format the expenses data
        formatted_expenses = []

        for row in expenses_data:
            if row[6] == -1:
                # Fetch expense category from expense_type table using income_id
                cursor.execute('SELECT expense_title FROM expense_type WHERE expense_id = %s', (row[0],))
                data = cursor.fetchone()
                category = data[0] if data and data[0] is not None else None

                # Fetch payment method from accounts table using payment_by
                cursor.execute('SELECT accounts_name FROM accounts WHERE account_id = %s', (row[2],))
                data = cursor.fetchone()
                payment_method = data[0] if data and data[0] is not None else None

                # Fetch payment by from accounts table using payment_to
                cursor.execute('SELECT accounts_name FROM accounts WHERE account_id = %s', (row[3],))
                data = cursor.fetchone()
                payment_by = data[0] if data and data[0] is not None else None

                formatted_expense = {
                    'expense_category': category,
                    'sub_category': row[1],  # Assuming source represents sub-category
                    'amount': row[5],
                    'payment_method': payment_method,
                    'payment_by': payment_by,
                    'submission_datetime': row[4]
                }

                formatted_expenses.append(formatted_expense)

        return formatted_expenses

    except Exception as e:
        print(f"Error fetching filtered expenses data: {str(e)}")
        return []

    finally:
        cursor.close()

@app.route('/get_filtered_expenses', methods=['POST'])
def get_filtered_expenses():
    connection = check_database_connection()

    try:
        if connection:
            from_date = request.form.get('fromDate')
            to_date = request.form.get('toDate')

            print(f"Received filter parameters - From: {from_date}, To: {to_date}")

            expenses_data = get_filtered_expenses_data(connection, from_date, to_date)

            print(f"Filtered expenses data: {expenses_data}")

            return jsonify({'expenses_data': expenses_data})

        else:
            return jsonify({})  # Return an empty dictionary if there's no database connection

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error fetching filtered expenses data: {str(e)}")
        return jsonify({})  # Return an empty dictionary in case of an error

    finally:
        if connection:
            connection.close()




#income_list.html
@app.route('/income_list')
def income_list():
    connection = check_database_connection()

    try:
        if connection:
            # Fetch income data from your database
            income_data = fetch_income_data(connection)
            return render_template('income_list.html', income_data=income_data)
        else:
            return "Error: No database connection"

    except Exception as e:
        print(f"Error in income_list route: {str(e)}")
        return "Error in income_list route"

    finally:
        if connection:
            connection.close()

# Function to fetch income data from the database

def fetch_income_data(connection):
    cursor = connection.cursor()

    try:
        cursor.execute('SELECT income_id, source, payment_by, payment_to, submission_datetime, amount, type FROM Transactions')
        income_data = cursor.fetchall()

        formatted_income = []

        for row in income_data:
            if row[6] == 1:
                # Fetch income category from income_type table using income_id
                cursor.execute('SELECT income_title FROM income_type WHERE income_id = %s', (row[0],))
                data = cursor.fetchone()
                category = data[0] if data and data[0] is not None else None

                # Fetch payment method from accounts table using payment_by
                cursor.execute('SELECT accounts_name FROM accounts WHERE account_id = %s', (row[2],))
                data = cursor.fetchone()
                payment_method = data[0] if data and data[0] is not None else None

                # Fetch received by from accounts table using payment_to
                cursor.execute('SELECT accounts_name FROM accounts WHERE account_id = %s', (row[3],))
                data = cursor.fetchone()
                received_by = data[0] if data and data[0] is not None else None

                formatted_income_item = {
                    'income_category': category,
                    'sub_category': row[1],  # Assuming source represents sub-category
                    'amount': row[5],
                    'payment_method': payment_method,
                    'received_by': received_by,
                    'submission_datetime': row[4]
                }

                formatted_income.append(formatted_income_item)

        return formatted_income

    except Exception as e:
        print(f"Error fetching income data: {str(e)}")
        return []

    finally:
        cursor.close()

def get_filtered_income_data(connection, from_date, to_date):
    cursor = connection.cursor()

    try:
        # Convert input date strings to datetime objects with a specific format
        from_date = datetime.strptime(from_date, "%Y-%m-%d").strftime("%Y-%m-%d 00:00:00")
        to_date = datetime.strptime(to_date, "%Y-%m-%d").strftime("%Y-%m-%d 23:59:59")

        # Execute the SQL query
        query = 'SELECT income_id, source, payment_by, payment_to, submission_datetime, amount, type ' \
                'FROM Transactions ' \
                'WHERE submission_datetime BETWEEN %s AND %s AND type = 1'
        cursor.execute(query, (from_date, to_date))
        income_data = cursor.fetchall()

        # Format the income data
        formatted_income = []

        for row in income_data:
            if row[6] == 1:
                # Fetch income category from income_type table using income_id
                cursor.execute('SELECT income_title FROM income_type WHERE income_id = %s', (row[0],))
                data = cursor.fetchone()
                category = data[0] if data and data[0] is not None else None

                # Fetch payment method from accounts table using payment_by
                cursor.execute('SELECT accounts_name FROM accounts WHERE account_id = %s', (row[2],))
                data = cursor.fetchone()
                payment_method = data[0] if data and data[0] is not None else None

                # Fetch received by from accounts table using payment_to
                cursor.execute('SELECT accounts_name FROM accounts WHERE account_id = %s', (row[3],))
                data = cursor.fetchone()
                received_by = data[0] if data and data[0] is not None else None

                formatted_income_item = {
                    'income_category': category,
                    'sub_category': row[1],  # Assuming source represents sub-category
                    'amount': row[5],
                    'payment_method': payment_method,
                    'received_by': received_by,
                    'submission_datetime': row[4]
                }

                formatted_income.append(formatted_income_item)

        return formatted_income

    except Exception as e:
        print(f"Error fetching filtered income data: {str(e)}")
        return []

    finally:
        cursor.close()

@app.route('/get_filtered_income', methods=['POST'])
def get_filtered_income():
    connection = check_database_connection()

    try:
        if connection:
            from_date = request.form.get('fromDate')
            to_date = request.form.get('toDate')

            print(f"Received filter parameters - From: {from_date}, To: {to_date}")

            income_data = get_filtered_income_data(connection, from_date, to_date)

            print(f"Filtered income data: {income_data}")

            return jsonify({'income_data': income_data})

        else:
            return jsonify({})  # Return an empty dictionary if there's no database connection

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error fetching filtered income data: {str(e)}")
        return jsonify({})  # Return an empty dictionary in case of an error

    finally:
        if connection:
            connection.close()

#income_list.html

#Account_Balance.html
# Your route to render the account balances page
@app.route('/account_balance')
def account_balances():
    connection = check_database_connection()

    try:
        if connection:
            # Fetch account data from your database
            accounts = fetch_accounts_data(connection)
            return render_template('account_balance.html', accounts=accounts)
        else:
            return "Error: No database connection"

    except Exception as e:
        print(f"Error in account_balances route: {str(e)}")
        return "Error in account_balances route"

    finally:
        if connection:
            connection.close()

# Function to fetch accounts data from the database
def fetch_accounts_data(connection):
    cursor = connection.cursor()

    try:
        cursor.execute('SELECT accounts_name, accounts_balance FROM accounts')  # Adjust the query accordingly
        accounts_data = cursor.fetchall()

        formatted_accounts = []

        for row in accounts_data:
            formatted_account = {
                'person_name': row[0],
                'balance': row[1],
                'color': generate_random_color()  # Generate a random color for each account
            }

            formatted_accounts.append(formatted_account)

        return formatted_accounts

    except Exception as e:
        print(f"Error fetching accounts data: {str(e)}")
        return []

    finally:
        cursor.close()

# Function to generate a random hex color
def generate_random_color():
    color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    return color



#account_balance.html



#Accounts.html


@app.route('/accounts')
def accounts():
    return render_template("accounts.html")

#accounts.html

#logout

@app.route('/logout')
def logout():
    # Clear the session data
    session.clear()
    # Redirect to the login page
    return redirect(url_for('login'))

#logout

@app.route('/get_expenses_and_incomes', methods=['GET'])
def get_expenses_and_incomes():
    connection = check_database_connection()

    try:
        if connection:
            expense_data = fetch_expenses(connection)
            income_data = fetch_incomes(connection)
            return jsonify({"expense_data": expense_data, "income_data": income_data})

        return jsonify(0)  # Default value if no connection

    except Exception as e:
        print(f"Error fetching expenses and incomes data: {str(e)}")
        return jsonify(0)  # Default value in case of an error

    finally:
        if connection:
            connection.close()

def fetch_expenses(connection):
    cursor = connection.cursor()

    try:
        cursor.execute("""
                    SELECT Income_Expense_Name, SUM(CAST(Amount AS FLOAT)) AS Amount
                    FROM TransactionDetails 
                    WHERE Amount < 0
                    GROUP BY Income_Expense_Name
                    ORDER BY Amount ASC
                """)

        expense_data = cursor.fetchall()
        return expense_data

    except Exception as e:
        print(f"Error fetching expenses data: {str(e)}")
        return []

    finally:
        cursor.close()


def fetch_incomes(connection):
    cursor = connection.cursor()

    try:
        cursor.execute("""
                    SELECT Income_Expense_Name, SUM(CAST(Amount AS FLOAT)) AS Amount
                    FROM TransactionDetails 
                    WHERE Amount > 0
                    GROUP BY Income_Expense_Name
                    ORDER BY Amount DESC
                """)

        income_data = cursor.fetchall()
        return income_data

    except Exception as e:
        print(f"Error fetching incomes data: {str(e)}")
        return []

    finally:
        cursor.close()


if __name__ == '__main__':
    app.run(debug=True)
