import psycopg2
from psycopg2 import extras
import sqlite3
import os
import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("Debug: File database.py is loading")


class Database:
    _instance = None
    is_postgres = False  # Default value, will be set by initialize
    db_file = 'rentmaster.db'  # File-based SQLite fallback

    @classmethod
    def initialize(cls):
        print("Debug: Entering initialize method")
        if cls._instance is None:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                print("ERROR: DATABASE_URL environment variable not found!")
                print(
                    "Please add your PostgreSQL connection string to the Secrets tab."
                )
                cls._fallback_to_sqlite()
                return
            max_retries = 3
            retry_delay = 2
            for attempt in range(max_retries):
                try:
                    print(
                        f"Debug: Attempting to connect to database (Attempt {attempt + 1}/{max_retries})"
                    )
                    cls._instance = cls()
                    cls._instance.connection = psycopg2.connect(database_url)
                    cls._instance.connection.autocommit = True
                    print("Successfully connected to PostgreSQL database")
                    cls.is_postgres = True
                    return
                except psycopg2.OperationalError as e:
                    logger.error(
                        f"Connection attempt {attempt + 1}/{max_retries} failed: {e}"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        logger.warning(
                            "Max retries reached for PostgreSQL. Falling back to SQLite."
                        )
                        cls._fallback_to_sqlite()
                        return

    @classmethod
    def _fallback_to_sqlite(cls):
        print("Debug: Falling back to SQLite")
        cls._instance = cls()
        cls._instance.connection = sqlite3.connect(cls.db_file)
        cls._instance.connection.row_factory = sqlite3.Row
        cls.is_postgres = False
        cls.setup_tables_sqlite()
        print("Debug: SQLite fallback initialized")

    @classmethod
    def get_connection(cls):
        print("Debug: Entering get_connection method")
        if cls._instance is None:
            cls.initialize()

        if cls._instance is None:
            logger.warning(
                "WARNING: Using fallback in-memory SQLite database due to initialization failure!"
            )
            cls._fallback_to_sqlite()

        # Check if connection is still active and reconnect if closed
        if cls._instance.connection.closed:
            logger.warning(
                "Database connection closed. Attempting to reconnect...")
            cls.initialize()
            if cls._instance.connection.closed:
                logger.error("Reconnection failed. Using existing fallback.")
                cls._fallback_to_sqlite()

        return cls._instance.connection

    @staticmethod
    def setup_tables_sqlite():
        print("Debug: Entering setup_tables_sqlite")
        conn = Database._instance.connection
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            mobile TEXT,
            country TEXT NOT NULL,
            city TEXT,
            sales_agent TEXT,
            branch TEXT,
            status TEXT NOT NULL,
            sales_stage TEXT DEFAULT 'Lead',
            address TEXT,
            phone TEXT,
            website TEXT,
            description TEXT,
            account_id INTEGER
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            name TEXT NOT NULL,
            rates TEXT NOT NULL,
            insurance TEXT,
            mileage INTEGER,
            fuel_level INTEGER,
            year INTEGER,
            status TEXT,
            type TEXT,
            features TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            car_id INTEGER,
            user_name TEXT,
            start_date TEXT,
            end_date TEXT,
            duration TEXT,
            cost REAL,
            contract_number TEXT UNIQUE,
            payment_type TEXT,
            account_id INTEGER
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            name TEXT NOT NULL,
            permissions TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            id_number TEXT,
            license_number TEXT,
            license_country TEXT,
            license_expiry TEXT,
            rating INTEGER,
            blacklisted INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            vat_amount REAL DEFAULT 0,
            account_id INTEGER,
            payment_type TEXT,
            date TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            account_type TEXT NOT NULL,
            account_name TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS pos_machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            serial_number TEXT NOT NULL,
            account_id INTEGER
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS languages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lang_code TEXT,
            key TEXT NOT NULL,
            value TEXT NOT NULL
        )''')
        conn.commit()
        print("Debug: setup_tables_sqlite completed")

    @staticmethod
    def setup_tables():
        print("Debug: setup_tables function is defined and being executed")
        conn = Database.get_connection()
        c = conn.cursor()
        if Database.is_postgres:
            c.execute('''CREATE TABLE IF NOT EXISTS vendors (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                mobile TEXT,
                country TEXT NOT NULL,
                city TEXT,
                sales_agent TEXT,
                branch TEXT,
                status TEXT NOT NULL,
                sales_stage TEXT DEFAULT 'Lead',
                address TEXT,
                phone TEXT,
                website TEXT,
                description TEXT,
                account_id INTEGER REFERENCES accounts(id)
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS cars (
                id SERIAL PRIMARY KEY,
                vendor_id INTEGER REFERENCES vendors(id),
                name TEXT NOT NULL,
                rates JSONB NOT NULL,
                insurance TEXT,
                mileage INTEGER,
                fuel_level INTEGER,
                year INTEGER,
                status TEXT,
                type TEXT,
                features JSONB
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                vendor_id INTEGER REFERENCES vendors(id),
                car_id INTEGER REFERENCES cars(id),
                user_name TEXT,
                start_date DATE,
                end_date DATE,
                duration TEXT,
                cost REAL,
                contract_number TEXT UNIQUE,
                payment_type TEXT,
                account_id INTEGER
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS roles (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER,
                name TEXT NOT NULL,
                permissions TEXT NOT NULL
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                vendor_id INTEGER REFERENCES vendors(id),
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                id_number TEXT,
                license_number TEXT,
                license_country TEXT,
                license_expiry DATE,
                rating INTEGER,
                blacklisted BOOLEAN DEFAULT FALSE
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                vat_amount REAL DEFAULT 0,
                account_id INTEGER,
                payment_type TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS accounts (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER,
                account_type TEXT NOT NULL,
                account_name TEXT NOT NULL
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS pos_machines (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER,
                serial_number TEXT NOT NULL,
                account_id INTEGER REFERENCES accounts(id)
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS languages (
                id SERIAL PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS translations (
                id SERIAL PRIMARY KEY,
                lang_code TEXT REFERENCES languages(code),
                key TEXT NOT NULL,
                value TEXT NOT NULL
            )''')
            conn.commit()
            print("Debug: setup_tables for PostgreSQL completed")
        else:
            print("Debug: Delegating to setup_tables_sqlite")
            Database.setup_tables_sqlite()
        print("Debug: setup_tables completed")


# Global Database instance
db = Database()


# Module-level functions with implementation using the db instance
def init_db():
    print("Debug: Entering init_db")
    Database.setup_tables()


def add_vendor(name,
               email,
               mobile,
               country,
               city=None,
               sales_agent=None,
               branch=None,
               status='Lead',
               sales_stage='Lead'):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO vendors (name, email, mobile, country, city, sales_agent, branch, status, sales_stage) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (name, email, mobile, country, city, sales_agent,
                               branch, status, sales_stage))
        conn.commit()
        print(f"Debug: Vendor {name} added successfully")
    except Exception as e:
        logger.error(f"Error adding vendor: {e}")
    finally:
        cursor.close()


def get_vendors(filters=None):
    try:
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if db.
                             is_postgres else None)
        query = "SELECT * FROM vendors"
        if filters:
            conditions = [f"{k} = %s" for k in filters.keys()]
            query += " WHERE " + " AND ".join(conditions)
            cursor.execute(query, list(filters.values()))
        else:
            cursor.execute(query)
        vendors = cursor.fetchall()
        return [dict(v) for v in vendors
                ] if db.is_postgres else [dict(v) for v in vendors]
    except Exception as e:
        logger.error(f"Error getting vendors: {e}")
        return []
    finally:
        cursor.close()


def update_vendor(vendor_id,
                  name=None,
                  email=None,
                  mobile=None,
                  country=None,
                  city=None,
                  sales_agent=None,
                  branch=None,
                  status=None,
                  sales_stage=None):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        updates = {
            k: v
            for k, v in locals().items() if v is not None and k != 'vendor_id'
            and k != 'conn' and k != 'cursor'
        }
        if updates:
            set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
            query = f"UPDATE vendors SET {set_clause} WHERE id = %s"
            cursor.execute(query, list(updates.values()) + [vendor_id])
            conn.commit()
            print(f"Debug: Vendor {vendor_id} updated successfully")
    except Exception as e:
        logger.error(f"Error updating vendor: {e}")
    finally:
        cursor.close()


def remove_vendor(vendor_id):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vendors WHERE id = %s", (vendor_id, ))
        conn.commit()
        print(f"Debug: Vendor {vendor_id} removed successfully")
    except Exception as e:
        logger.error(f"Error removing vendor: {e}")
    finally:
        cursor.close()


def add_car(vendor_id,
            name,
            rates,
            insurance,
            mileage,
            fuel_level,
            year=None,
            status='Available',
            type=None,
            features=None):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO cars (vendor_id, name, rates, insurance, mileage, fuel_level, year, status, type, features) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (vendor_id, name, rates, insurance, mileage,
                               fuel_level, year, status, type, features))
        conn.commit()
        print(f"Debug: Car {name} added successfully")
    except Exception as e:
        logger.error(f"Error adding car: {e}")
    finally:
        cursor.close()


def get_cars(vendor_id=None):
    try:
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if db.
                             is_postgres else None)
        query = "SELECT * FROM cars WHERE vendor_id = %s OR %s IS NULL"
        cursor.execute(query, (vendor_id, vendor_id))
        cars = cursor.fetchall()
        return [dict(c)
                for c in cars] if db.is_postgres else [dict(c) for c in cars]
    except Exception as e:
        logger.error(f"Error getting cars: {e}")
        return []
    finally:
        cursor.close()


def update_car(car_id,
               name,
               rates,
               insurance,
               mileage,
               fuel_level,
               status,
               year=None,
               type=None,
               features=None):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "UPDATE cars SET name = %s, rates = %s, insurance = %s, mileage = %s, fuel_level = %s, status = %s, year = %s, type = %s, features = %s WHERE id = %s"
        cursor.execute(query, (name, rates, insurance, mileage, fuel_level,
                               status, year, type, features, car_id))
        conn.commit()
        print(f"Debug: Car {car_id} updated successfully")
    except Exception as e:
        logger.error(f"Error updating car: {e}")
    finally:
        cursor.close()


def remove_car(car_id):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cars WHERE id = %s", (car_id, ))
        conn.commit()
        print(f"Debug: Car {car_id} removed successfully")
    except Exception as e:
        logger.error(f"Error removing car: {e}")
    finally:
        cursor.close()


def add_booking(vendor_id, car_id, user_name, start_date, end_date, duration,
                cost, contract_number, payment_type, account_id):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO bookings (vendor_id, car_id, user_name, start_date, end_date, duration, cost, contract_number, payment_type, account_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(
            query, (vendor_id, car_id, user_name, start_date, end_date,
                    duration, cost, contract_number, payment_type, account_id))
        conn.commit()
        print(f"Debug: Booking {contract_number} added successfully")
    except Exception as e:
        logger.error(f"Error adding booking: {e}")
    finally:
        cursor.close()


def get_bookings(vendor_id, filters=None, future_only=False):
    try:
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if db.
                             is_postgres else None)
        query = "SELECT * FROM bookings WHERE vendor_id = %s OR %s IS NULL"
        params = [vendor_id, vendor_id]
        if future_only:
            query += " AND start_date > CURRENT_DATE"
        if filters:
            conditions = [f"{k} = %s" for k in filters.keys()]
            query += " AND " + " AND ".join(conditions)
            params.extend(filters.values())
        cursor.execute(query, params)
        bookings = cursor.fetchall()
        return [dict(b) for b in bookings
                ] if db.is_postgres else [dict(b) for b in bookings]
    except Exception as e:
        logger.error(f"Error getting bookings: {e}")
        return []
    finally:
        cursor.close()


def add_role(name, permissions, tenant_id):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO roles (name, permissions, tenant_id) VALUES (%s, %s, %s)"
        cursor.execute(query, (name, permissions, tenant_id))
        conn.commit()
        print(f"Debug: Role {name} added successfully")
    except Exception as e:
        logger.error(f"Error adding role: {e}")
    finally:
        cursor.close()


def get_roles(tenant_id):
    try:
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if db.
                             is_postgres else None)
        query = "SELECT * FROM roles WHERE tenant_id = %s OR %s IS NULL"
        cursor.execute(query, (tenant_id, tenant_id))
        roles = cursor.fetchall()
        return [dict(r) for r in roles
                ] if db.is_postgres else [dict(r) for r in roles]
    except Exception as e:
        logger.error(f"Error getting roles: {e}")
        return []
    finally:
        cursor.close()


def check_permission(username, permission):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "SELECT permissions FROM roles JOIN users ON roles.id = users.role_id WHERE users.username = %s"
        cursor.execute(query, (username, ))
        result = cursor.fetchone()
        if result:
            permissions = result[0]
            return permission in permissions.split(',')
        return False
    except Exception as e:
        logger.error(f"Error checking permission: {e}")
        return False
    finally:
        cursor.close()


def add_customer(vendor_id, name, email, phone, id_number, license_number,
                 license_country, license_expiry, rating):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO customers (vendor_id, name, email, phone, id_number, license_number, license_country, license_expiry, rating) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(
            query, (vendor_id, name, email, phone, id_number, license_number,
                    license_country, license_expiry, rating))
        conn.commit()
        print(f"Debug: Customer {name} added successfully")
    except Exception as e:
        logger.error(f"Error adding customer: {e}")
    finally:
        cursor.close()


def get_customers(vendor_id):
    try:
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if db.
                             is_postgres else None)
        query = "SELECT * FROM customers WHERE vendor_id = %s OR %s IS NULL"
        cursor.execute(query, (vendor_id, vendor_id))
        customers = cursor.fetchall()
        return [dict(c) for c in customers
                ] if db.is_postgres else [dict(c) for c in customers]
    except Exception as e:
        logger.error(f"Error getting customers: {e}")
        return []
    finally:
        cursor.close()


def blacklist_customer(customer_id, blacklisted):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "UPDATE customers SET blacklisted = %s WHERE id = %s"
        cursor.execute(query, (blacklisted, customer_id))
        conn.commit()
        print(f"Debug: Customer {customer_id} blacklist status updated")
    except Exception as e:
        logger.error(f"Error blacklisting customer: {e}")
    finally:
        cursor.close()


def add_transaction(tenant_id,
                    category,
                    amount,
                    description,
                    vat_amount=0,
                    account_id=None,
                    payment_type=None):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO transactions (tenant_id, category, amount, description, vat_amount, account_id, payment_type) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (tenant_id, category, amount, description,
                               vat_amount, account_id, payment_type))
        conn.commit()
        print(f"Debug: Transaction added successfully")
    except Exception as e:
        logger.error(f"Error adding transaction: {e}")
    finally:
        cursor.close()


def get_transactions(tenant_id, filters=None):
    try:
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if db.
                             is_postgres else None)
        query = "SELECT * FROM transactions WHERE tenant_id = %s OR %s IS NULL"
        params = [tenant_id, tenant_id]
        if filters:
            conditions = [f"{k} = %s" for k in filters.keys()]
            query += " AND " + " AND ".join(conditions)
            params.extend(filters.values())
        cursor.execute(query, params)
        transactions = cursor.fetchall()
        return [dict(t) for t in transactions
                ] if db.is_postgres else [dict(t) for t in transactions]
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        return []
    finally:
        cursor.close()


def add_account(tenant_id, account_type, account_name):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO accounts (tenant_id, account_type, account_name) VALUES (%s, %s, %s)"
        cursor.execute(query, (tenant_id, account_type, account_name))
        conn.commit()
        print(f"Debug: Account {account_name} added successfully")
    except Exception as e:
        logger.error(f"Error adding account: {e}")
    finally:
        cursor.close()


def get_accounts(tenant_id):
    try:
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if db.
                             is_postgres else None)
        query = "SELECT * FROM accounts WHERE tenant_id = %s OR %s IS NULL"
        cursor.execute(query, (tenant_id, tenant_id))
        accounts = cursor.fetchall()
        return [dict(a) for a in accounts
                ] if db.is_postgres else [dict(a) for a in accounts]
    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
        return []
    finally:
        cursor.close()


def add_pos_machine(tenant_id, serial_number, account_id):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO pos_machines (tenant_id, serial_number, account_id) VALUES (%s, %s, %s)"
        cursor.execute(query, (tenant_id, serial_number, account_id))
        conn.commit()
        print(f"Debug: POS machine {serial_number} added successfully")
    except Exception as e:
        logger.error(f"Error adding POS machine: {e}")
    finally:
        cursor.close()


def get_pos_machines(tenant_id):
    try:
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if db.
                             is_postgres else None)
        query = "SELECT * FROM pos_machines WHERE tenant_id = %s OR %s IS NULL"
        cursor.execute(query, (tenant_id, tenant_id))
        pos_machines = cursor.fetchall()
        return [dict(p) for p in pos_machines
                ] if db.is_postgres else [dict(p) for p in pos_machines]
    except Exception as e:
        logger.error(f"Error getting POS machines: {e}")
        return []
    finally:
        cursor.close()


def add_language(code, name):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO languages (code, name) VALUES (%s, %s)"
        cursor.execute(query, (code, name))
        conn.commit()
        print(f"Debug: Language {name} added successfully")
    except Exception as e:
        logger.error(f"Error adding language: {e}")
    finally:
        cursor.close()


def get_languages():
    try:
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if db.
                             is_postgres else None)
        query = "SELECT * FROM languages"
        cursor.execute(query)
        languages = cursor.fetchall()
        return [dict(l) for l in languages
                ] if db.is_postgres else [dict(l) for l in languages]
    except Exception as e:
        logger.error(f"Error getting languages: {e}")
        return [{'code': 'en', 'name': 'English'}]  # Default fallback
    finally:
        cursor.close()


def add_translation(lang_code, key, value):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO translations (lang_code, key, value) VALUES (%s, %s, %s)"
        cursor.execute(query, (lang_code, key, value))
        conn.commit()
        print(f"Debug: Translation for {key} added successfully")
    except Exception as e:
        logger.error(f"Error adding translation: {e}")
    finally:
        cursor.close()


def get_translations(lang_code):
    try:
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor if db.
                             is_postgres else None)
        query = "SELECT * FROM translations WHERE lang_code = %s"
        cursor.execute(query, (lang_code, ))
        translations = cursor.fetchall()
        return [dict(t) for t in translations
                ] if db.is_postgres else [dict(t) for t in translations]
    except Exception as e:
        logger.error(f"Error getting translations: {e}")
        return []
    finally:
        cursor.close()


def add_vendor_detailed(name, city, branch, address, phone, email, website,
                        description, account_id):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO vendors (name, city, branch, address, phone, email, website, description, account_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (name, city, branch, address, phone, email,
                               website, description, account_id))
        conn.commit()
        print(f"Debug: Vendor {name} added with details successfully")
    except Exception as e:
        logger.error(f"Error adding vendor detailed: {e}")
    finally:
        cursor.close()


# Ensure these functions are exported
__all__ = [
    'init_db', 'add_vendor', 'get_vendors', 'update_vendor', 'remove_vendor',
    'add_car', 'get_cars', 'update_car', 'remove_car', 'add_booking',
    'get_bookings', 'add_role', 'get_roles', 'check_permission',
    'add_customer', 'get_customers', 'blacklist_customer', 'add_transaction',
    'get_transactions', 'add_account', 'get_accounts', 'add_pos_machine',
    'get_pos_machines', 'add_language', 'get_languages', 'add_translation',
    'get_translations', 'add_vendor_detailed'
]

print("Debug: database.py fully loaded")

if __name__ == "__main__":
    Database.initialize()
    # setup_tables()  # Use this for new setups
    # migrate_vendors_table()  # Uncomment and run once if updating an existing schema
