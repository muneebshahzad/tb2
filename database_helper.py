# database_helper.py
import pyodbc
import datetime

def check_database_connection():
    server = 'localhost'
    database = 'tickbags'
    driver = 'SQL Server'
    connection_string = 'DRIVER={SQL Server};SERVER=DESKTOP-7IJ8SAC\SQLEXPRESS;DATABASE=tickbags;Trusted_Connection=yes;'

    try:
        return pyodbc.connect(connection_string)
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

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
        cursor.execute('INSERT INTO accounts (accounts_name) VALUES (?)', received_by)
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
            cursor.execute('SELECT income_id FROM income_type WHERE income_title = ?', income_type)
            result = cursor.fetchone()
            if result:
                income_id = result[0]

            cursor.execute('SELECT account_id FROM accounts WHERE accounts_name = ?', payment_via)
            result = cursor.fetchone()
            if result:
                payment_by = result[0]

            cursor.execute('SELECT account_id FROM accounts WHERE accounts_name = ?', received_by)
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
            cursor.execute('SELECT expense_id FROM expense_type WHERE expense_title = ?', expense_type)
            result = cursor.fetchone()
            if result:
                expense_id = result[0]

            cursor.execute('SELECT account_id FROM accounts WHERE accounts_name = ?', payment_via)
            result = cursor.fetchone()
            if result:
                payment_by = result[0]

            cursor.execute('SELECT account_id FROM accounts WHERE accounts_name = ?', received_by)
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
            WHERE accounts_name = ? 
              AND accounts_name NOT IN ('Bank', 'Cash');
            ''',
            source
        )

        result = cursor.fetchone()
        source_exists = result[0] if result else None

        return source_exists > 0 if source_exists is not None else None

    except Exception as e:
        print(f"Error checking source existence: {str(e)}")
        return None

    finally:
        cursor.close()

def add_transaction(connection, transaction_data):
    cursor = connection.cursor()

    try:
        cursor.execute(
            '''
            INSERT INTO transactions (transaction_type, transaction_date, 
                                      transaction_description, amount, 
                                      income_id, expense_id, 
                                      payment_by, payment_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            transaction_data['transaction_type'],
            transaction_data['transaction_date'],
            transaction_data['transaction_description'],
            transaction_data['amount'],
            transaction_data['income_id'],
            transaction_data['expense_id'],
            transaction_data['payment_by'],
            transaction_data['payment_to']
        )

        connection.commit()
        return True

    except Exception as e:
        print(f"Error adding transaction: {str(e)}")
        connection.rollback()
        return False

    finally:
        cursor.close()

def add_income_transaction(connection, transaction_data):
    cursor = connection.cursor()

    try:
        cursor.execute(
            '''
            INSERT INTO transactions (transaction_type, transaction_date, 
                                      transaction_description, amount, 
                                      income_id, expense_id, 
                                      payment_by, payment_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            "Income",  # Set the transaction_type to "Income"
            transaction_data['transaction_date'],
            transaction_data['transaction_description'],
            transaction_data['amount'],
            transaction_data['income_id'],
            None,  # Set expense_id to None for income transactions
            transaction_data['payment_by'],
            transaction_data['payment_to']
        )

        connection.commit()
        return True

    except Exception as e:
        print(f"Error adding income transaction: {str(e)}")
        connection.rollback()
        return False

    finally:
        cursor.close()

def add_expense_transaction(connection, transaction_data):
    cursor = connection.cursor()

    try:
        cursor.execute(
            '''
            INSERT INTO transactions (transaction_type, transaction_date, 
                                      transaction_description, amount, 
                                      income_id, expense_id, 
                                      payment_by, payment_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            "Expense",  # Set the transaction_type to "Expense"
            transaction_data['transaction_date'],
            transaction_data['transaction_description'],
            transaction_data['amount'],
            None,  # Set income_id to None for expense transactions
            transaction_data['expense_id'],
            transaction_data['payment_by'],
            transaction_data['payment_to']
        )

        connection.commit()
        return True

    except Exception as e:
        print(f"Error adding expense transaction: {str(e)}")
        connection.rollback()
        return False

    finally:
        cursor.close()
