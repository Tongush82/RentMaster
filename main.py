from flask import Flask, jsonify, request, session, redirect, url_for, flash
from database import (Database, init_db, add_vendor, get_vendors,
                      update_vendor, remove_vendor, add_car, get_cars,
                      add_booking, get_bookings, add_role, get_roles,
                      check_permission, add_customer, get_customers,
                      blacklist_customer, add_transaction, get_transactions,
                      add_account, get_accounts, add_pos_machine,
                      get_pos_machines, add_language, get_languages,
                      add_translation, add_vendor_detailed)
import os
from flask_babel import Babel, gettext as _  # Import Babel for translations
import logging
import time
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key in production

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize database
init_db()

# Flask-Babel configuration (without localeselector for now)
babel = Babel(app)

# Sample data for dynamic dropdowns and context
makes = ['Toyota', 'Honda', 'Ford']
models_by_make = {
    'Toyota': ['Camry', 'Corolla', 'RAV4'],
    'Honda': ['Civic', 'Accord', 'CR-V'],
    'Ford': ['Focus', 'Escape', 'F-150']
}
colors_by_model = {
    'Toyota': {
        'Camry': ['Red', 'Blue', 'Black'],
        'Corolla': ['Silver', 'White'],
        'RAV4': ['Green', 'Gray']
    },
    'Honda': {
        'Civic': ['Blue', 'Red'],
        'Accord': ['Black', 'White'],
        'CR-V': ['Silver']
    },
    'Ford': {
        'Focus': ['Red', 'Gray'],
        'Escape': ['Blue'],
        'F-150': ['Black', 'White']
    }
}
vehicle_status = ['Available', 'Rented', 'Maintenance', 'Unknown']
vehicle_types = ['Sedan', 'SUV', 'Truck']
countries = ['USA', 'UK', 'Canada', 'Australia', 'Germany']


# API Endpoints
@app.route('/api/login', methods=['POST'])
def api_login():
    username = request.form.get('username')
    password = request.form.get('password')
    if username == 'vendor1' and password == 'vendorpass':
        session['username'] = username
        session['role'] = 'vendor'
        session['vendor_id'] = 1
        return jsonify({
            'status':
            'success',
            'message':
            _('Welcome to RentMaster, %(username)s!', username=username)
        })
    return jsonify({
        'status': 'error',
        'message': _('Invalid credentials')
    }), 401


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('username', None)
    session.pop('role', None)
    session.pop('vendor_id', None)
    return jsonify({
        'status': 'success',
        'message': _('Logged out successfully')
    })


@app.route('/api/cars', methods=['GET'])
def api_get_cars():
    if 'username' not in session or session.get('role') != 'vendor':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    cars = get_cars(session.get('vendor_id', None))
    return jsonify({'status': 'success', 'data': cars})


@app.route('/api/bookings', methods=['GET', 'POST'])
def api_bookings():
    if 'username' not in session or session.get('role') != 'vendor':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    if request.method == 'POST':
        car_id = request.form.get('car_id')
        user_name = request.form.get('user_name')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        duration = request.form.get('duration')
        cost = float(request.form.get('cost'))
        contract_number = request.form.get('contract_number')
        payment_type = request.form.get('payment_type')
        account_id = request.form.get('account_id')
        add_booking(session.get('vendor_id',
                                None), car_id, user_name, start_date, end_date,
                    duration, cost, contract_number, payment_type, account_id)
        return jsonify({
            'status': 'success',
            'message': _('Booking added successfully!')
        })
    bookings = get_bookings(session.get('vendor_id', None), future_only=False)
    return jsonify({'status': 'success', 'data': bookings})


@app.route('/api/customers', methods=['GET', 'POST'])
def api_customers():
    if 'username' not in session or session.get('role') != 'vendor':
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    if request.method == 'POST':
        if request.form.get('add_customer'):
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            id_number = request.form.get('id_number')
            license_number = request.form.get('license_number')
            license_country = request.form.get('license_country')
            license_expiry = request.form.get('license_expiry')
            rating = int(request.form.get('rating'))
            add_customer(session.get('vendor_id', None), name, email, phone,
                         id_number, license_number, license_country,
                         license_expiry, rating)
            return jsonify({
                'status': 'success',
                'message': _('Customer added successfully!')
            })
        elif request.form.get('blacklist') or request.form.get('unblacklist'):
            customer_id = request.form.get('customer_id')
            blacklisted = bool(request.form.get('blacklist'))
            blacklist_customer(customer_id, blacklisted)
            return jsonify({
                'status':
                'success',
                'message':
                _('Customer status updated successfully!')
            })
    customers = get_customers(session.get('vendor_id', None))
    return jsonify({'status': 'success', 'data': customers})


# Legacy Routes (for transition)
@app.route('/vendor_dashboard')
def vendor_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return "Please use the React frontend at /app", 302


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'vendor1' and password == 'vendorpass':
            session['username'] = username
            session['role'] = 'vendor'
            session['vendor_id'] = 1
            return redirect(url_for('vendor_dashboard'))
        flash(_('Invalid credentials'), 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    session.pop('vendor_id', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
