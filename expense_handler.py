# expense_handler.py
from flask import Blueprint, request, jsonify, render_template
from database_helper import check_database_connection, get_expense_types, fetch_source_data, fetch_payment_to_data, add_expense_transaction, get_expense_ids

handle_expense_routes = Blueprint('handle_expense_routes', __name__)

@handle_expense_routes.route('/add_expense', methods=['POST'])
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

@handle_expense_routes.route('/get_source_data', methods=['POST'])
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

@handle_expense_routes.route('/get_payment_to_data', methods=['POST'])
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

@handle_expense_routes.route('/get_expense_ids', methods=['POST'])
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
