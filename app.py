import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import urllib.parse
import bcrypt
from fpdf import FPDF
import random

# --- KONFIGURASI DAN INISIALISASI ---
DB = "pos.db"
st.set_page_config(layout="wide", page_title="Orca Cafe") # Mengganti nama cafe

# =====================================================================
# --- FUNGSI MIGRASI & INISIALISASI DATABASE ---
# =====================================================================
def update_db_schema(conn):
    """Memeriksa dan memperbarui skema database jika diperlukan."""
    c = conn.cursor()

    # Employees table updates
    c.execute("PRAGMA table_info(employees)")
    emp_columns = {info[1] for info in c.fetchall()}
    if 'password' not in emp_columns: 
        c.execute("ALTER TABLE employees ADD COLUMN password TEXT")
    if 'role' not in emp_columns: 
        c.execute("ALTER TABLE employees ADD COLUMN role TEXT")
    if 'is_active' not in emp_columns: 
        c.execute("ALTER TABLE employees ADD COLUMN is_active BOOLEAN DEFAULT 1")
    if 'hourly_wage' in emp_columns:
         c.execute("ALTER TABLE employees RENAME TO employees_old")
         c.execute("""CREATE TABLE employees (
             id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, wage_amount REAL, 
             wage_period TEXT, password TEXT, role TEXT, is_active BOOLEAN DEFAULT 1
         )""")
         c.execute("INSERT INTO employees (id, name, wage_amount, wage_period, is_active) SELECT id, name, hourly_wage, 'Per Jam', 1 FROM employees_old")
         c.execute("DROP TABLE employees_old")
         st.toast("Skema database karyawan telah diperbarui.")

    # Expenses table updates
    c.execute("PRAGMA table_info(expenses)")
    exp_columns = {info[1] for info in c.fetchall()}
    if 'category' not in exp_columns:
        c.execute("ALTER TABLE expenses ADD COLUMN category TEXT DEFAULT 'Lainnya'")
        st.toast("Skema database pengeluaran telah diperbarui.")
    # NEW: Add account_id to expenses for accounting integration
    if 'account_id' not in exp_columns:
        c.execute("ALTER TABLE expenses ADD COLUMN account_id INTEGER")
        st.toast("Skema database pengeluaran telah diperbarui dengan account_id.")

    conn.commit()

def insert_initial_data(conn):
    """Membuat akun default jika belum ada."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM employees WHERE name = 'admin'")
    if c.fetchone()[0] == 0:
        st.info("Akun admin tidak ditemukan, membuat akun default...")
        initial_users = [
            ('admin', bcrypt.hashpw('admin'.encode('utf8'), bcrypt.gensalt()), 'Admin', 0, 'Per Bulan', 1),
            ('operator', bcrypt.hashpw('operator'.encode('utf8'), bcrypt.gensalt()), 'Operator', 0, 'Per Jam', 1)
        ]
        c.executemany("INSERT INTO employees (name, password, role, wage_amount, wage_period, is_active) VALUES (?, ?, ?, ?, ?, ?)", initial_users)
        conn.commit()
        st.success("Akun awal (admin/admin, operator/operator) berhasil dibuat.")
        st.rerun()

def insert_initial_products(conn):
    """Memasukkan daftar produk awal jika tabel produk kosong."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        st.info("Daftar produk tidak ditemukan, menambahkan produk awal...")
        products = [
            ("Espresso", 10000), ("Americano", 11000), ("Orange Americano", 14000),
            ("Lemon Americano", 14000), ("Cocof (BN Signature)", 15000), ("Coffee Latte", 15000),
            ("Cappuccino", 15000), ("Spanish Latte", 16000), ("Caramel Latte", 16000),
            ("Vanilla Latte", 16000), ("Hazelnut Latte", 16000), ("Butterscotch Latte", 16000),
            ("Tiramisu Latte", 16000), ("Mocca Latte", 16000), ("Coffee Chocolate", 18000),
            ("Taro Coffee Latte", 18000), ("Coffee Gula Aren", 18000), ("Lychee Coffee", 20000),
            ("Markisa Coffee", 20000), ("Raspberry Latte", 20000), ("Strawberry Latte", 20000),
            ("Manggo Latte", 20000), ("Bubblegum Latte", 20000),
            ("Lemon Tea", 10000), ("Lychee Tea", 10000), ("Milk Tea", 12000),
            ("Green Tea", 14000), ("Thai Tea", 14000), ("Melon Susu", 14000),
            ("Manggo Susu", 15000), ("Mocca Susu", 15000), ("Orange Susu", 15000),
            ("Taro Susu", 15000), ("Coklat Susu", 15000), ("Vanilla Susu", 15000),
            ("Strawberry Susu", 15000), ("Matcha Susu", 18000), ("Blueberry Susu", 18000),
            ("Bubblegum Susu", 18000), ("Raspberry Susu", 18000), ("Grenadine Susu", 14000),
            ("Banana Susu", 16000),
            ("Melon Soda", 10000), ("Manggo Soda", 12000), ("Orange Soda", 12000),
            ("Strawberry Soda", 12000), ("Bluesky Soda", 14000), ("Banana Soda", 16000),
            ("Grenadine Soda", 14000), ("Blueberry Soda", 16000), ("Coffee Bear", 16000),
            ("Mocca Soda", 16000), ("Raspberry Soda", 16000), ("Coffee Soda", 17000),
            ("Strawberry Coffee Soda", 18000), ("Melon Blue Sky", 18000), ("Blue Manggo Soda", 18000),
            ("Nasi Goreng Kampung", 10000), ("Nasi Goreng Biasa", 10000), ("Nasi Goreng Ayam", 18000),
            ("Nasi Ayam Sambal Matah", 13000), ("Nasi Ayam Penyet", 13000), ("Nasi Ayam Teriyaki", 15000),
            ("Mie Goreng", 12000), ("Mie Rebus", 12000), ("Mie Nyemek", 12000), ("Bihun Goreng", 12000),
            ("Burger Telur", 10000), ("Burger Ayam", 12000), ("Burger Telur + Keju", 13000),
            ("Burger Telur + Ayam", 15000), ("Burger Ayam + Telur + Keju", 18000),
            ("Roti Bakar Coklat", 10000), ("Roti Bakar Strawberry", 10000), ("Roti Bakar Srikaya", 10000),
            ("Roti Bakar Coklat Keju", 12000),
            ("Kentang Goreng", 12000), ("Nugget", 12000), ("Sosis", 12000),
            ("Mix Platter Jumbo", 35000), ("Tahu/Tempe", 5000),
            ("Double Shoot", 3000), ("Yakult", 3000), ("Mineral Water", 4000),
            ("Mineral Water Gelas", 500), ("Nasi Putih", 3000), ("Le Mineralle", 4000)
        ]
        c.executemany("INSERT INTO products (name, price) VALUES (?, ?)", products)
        conn.commit()
        st.success("Daftar produk awal berhasil ditambahkan.")
        st.rerun()

# NEW: Insert initial Chart of Accounts
def insert_initial_accounts(conn):
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM accounts")
    if c.fetchone()[0] == 0:
        st.info("Daftar akun tidak ditemukan, menambahkan akun standar...")
        initial_accounts = [
            (1000, 'Kas', 'Aset', 'Debit'),
            (1010, 'Bank', 'Aset', 'Debit'),
            (1020, 'Piutang Usaha', 'Aset', 'Debit'),
            (1030, 'Persediaan Bahan Baku', 'Aset', 'Debit'),
            (1040, 'Aktiva Tetap', 'Aset', 'Debit'),
            (2000, 'Utang Usaha', 'Liabilitas', 'Kredit'),
            (2010, 'Utang Gaji', 'Liabilitas', 'Kredit'),
            (3000, 'Modal Pemilik', 'Ekuitas', 'Kredit'),
            (3010, 'Laba Ditahan', 'Ekuitas', 'Kredit'),
            (4000, 'Pendapatan Penjualan', 'Pendapatan', 'Kredit'),
            (5000, 'Harga Pokok Penjualan', 'Beban', 'Debit'),
            (6000, 'Beban Gaji', 'Beban', 'Debit'),
            (6010, 'Beban Listrik & Air', 'Beban', 'Debit'),
            (6020, 'Beban Sewa', 'Beban', 'Debit'),
            (6030, 'Beban Lain-lain', 'Beban', 'Debit'),
            (7000, 'Pendapatan Lain-lain', 'Pendapatan', 'Kredit')
        ]
        c.executemany("INSERT INTO accounts (account_code, account_name, account_type, normal_balance) VALUES (?, ?, ?, ?)", initial_accounts)
        conn.commit()
        st.success("Daftar akun awal berhasil ditambahkan.")
        st.rerun()


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, wage_amount REAL, 
        wage_period TEXT, password TEXT, role TEXT, is_active BOOLEAN DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, unit TEXT,
        cost_per_unit REAL, stock REAL, pack_weight REAL DEFAULT 0.0, pack_price REAL DEFAULT 0.0
    )""")
    c.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, price REAL)")
    c.execute("""CREATE TABLE IF NOT EXISTS recipes (
        product_id INTEGER, ingredient_id INTEGER, qty_per_unit REAL, PRIMARY KEY (product_id, ingredient_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_date TEXT, total_amount REAL, 
        payment_method TEXT, employee_id INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS transaction_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id INTEGER, product_id INTEGER, 
        quantity INTEGER, price_per_unit REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, category TEXT, 
        description TEXT, amount REAL, payment_method TEXT, account_id INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, check_in TEXT, check_out TEXT
    )""")
    # NEW TABLES FOR ACCOUNTING AND ERP FEATURES
    c.execute("""CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_code INTEGER UNIQUE,
        account_name TEXT UNIQUE,
        account_type TEXT, -- e.g., Aset, Liabilitas, Ekuitas, Pendapatan, Beban
        normal_balance TEXT -- e.g., Debit, Kredit
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS journal_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT,
        description TEXT,
        transaction_id INTEGER, -- Link to transactions table
        expense_id INTEGER, -- Link to expenses table
        FOREIGN KEY (transaction_id) REFERENCES transactions(id),
        FOREIGN KEY (expense_id) REFERENCES expenses(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS journal_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        journal_entry_id INTEGER,
        account_id INTEGER,
        debit REAL DEFAULT 0.0,
        kredit REAL DEFAULT 0.0,
        FOREIGN KEY (journal_entry_id) REFERENCES journal_entries(id),
        FOREIGN KEY (account_id) REFERENCES accounts(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        address TEXT,
        phone TEXT,
        email TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        address TEXT,
        phone TEXT,
        email TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS fixed_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_name TEXT,
        acquisition_date TEXT,
        acquisition_cost REAL,
        useful_life_years INTEGER,
        salvage_value REAL,
        depreciation_method TEXT, -- e.g., Straight-line
        current_book_value REAL
    )""")

    update_db_schema(conn)
    conn.commit()
    insert_initial_data(conn)
    insert_initial_products(conn) 
    insert_initial_accounts(conn) # NEW: Insert initial accounts
    conn.close()

# =====================================================================
# --- BAGIAN LOGIN ---
# =====================================================================
def check_login():
    if "logged_in" not in st.session_state: 
        st.session_state.logged_in = False
    if st.session_state.logged_in:
        st.sidebar.success(f"Welcome, {st.session_state.username} ({st.session_state.role})")
        if st.sidebar.button("Logout"):
            for key in st.session_state.keys(): del st.session_state[key]
            st.rerun()
        run_main_app()
    else:
        st.title("☕ Orca Cafe") # Mengganti nama cafe
        # --- PERUBAHAN: Variasi Quotes bertema laut ---
        quotes = [
            "Selamat datang di kedalaman rasa. Secangkir kopi sehangat pelukan ombak.",
            "Hidup itu seperti laut, penuh misteri dan keindahan. Nikmati setiap tegukan di Orca Cafe.",
            "Di setiap tetes kopi, ada bisikan samudra yang menanti untuk dinikmati.",
            "Satu tegukan kopi, sejuta inspirasi dari birunya laut.",
            "Kopi pagi ini secerah mentari di atas permukaan laut.",
            "Jangan biarkan kopimu dingin, dan jangan biarkan semangatmu tenggelam.",
            "Temukan ketenangan dalam secangkir kopi, seperti menemukan damai di dasar samudra.",
            "Kopi adalah caraku mengatakan 'mari kita arungi hari ini'.",
            "Setiap cangkir adalah petualangan, dan barista adalah nahkodanya.",
            "Selamat menikmati kopi pilihan terbaik, sebiru lautan lepas."
        ]
        st.markdown(f"> *{random.choice(quotes)}*")
        st.markdown("---")
        with st.form("login_form"):
            username = st.text_input("Username").lower()
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                conn = sqlite3.connect(DB)
                c = conn.cursor()
                c.execute("SELECT id, password, role FROM employees WHERE name = ? AND is_active = 1", (username,))
                user_data = c.fetchone()
                conn.close()
                if user_data and user_data[1] is not None:
                    user_id, hashed_password_from_db, role = user_data
                    if bcrypt.checkpw(password.encode('utf8'), hashed_password_from_db):
                        st.session_state.logged_in = True; st.session_state.user_id = user_id
                        st.session_state.username = username; st.session_state.role = role
                        st.rerun()
                    else: 
                        st.error("Password salah!")
                else: 
                    st.error("Username tidak ditemukan atau akun tidak aktif!")

# =====================================================================
# --- APLIKASI UTAMA ---
# =====================================================================
def run_main_app():
    # --- PERUBAHAN: Injeksi CSS untuk tema Biru Muda dan perbaikan input/select ---
    custom_css = """
        <style>
            /* Color Palette (Biru Muda) */
            :root {
                --primary-color: #87CEEB; /* Light Sky Blue */
                --secondary-color: #ADD8E6; /* Light Blue */
                --background-color: #E0FFFF; /* Light Cyan */
                --text-color: #2F4F4F; /* Dark Slate Gray */
                --widget-background: #F0F8FF; /* Alice Blue */
                --accent-color: #4682B4; /* Steel Blue for highlights */
            }

            /* General Body */
            body {
                color: var(--text-color);
                background-color: var(--background-color);
            }

            /* Sidebar */
            .st-emotion-cache-16txtl3 { /* Target the sidebar container */
                background-color: var(--widget-background);
                border-right: 1px solid rgba(0, 0, 0, 0.1); /* Subtle border */
            }
            .st-emotion-cache-16txtl3 .stButton > button { /* Sidebar buttons */
                background-color: var(--widget-background);
                color: var(--text-color);
                border: 1px solid var(--primary-color);
            }
            .st-emotion-cache-16txtl3 .stButton > button:hover {
                background-color: var(--primary-color);
                color: white;
            }


            /* Main Content */
            .st-emotion-cache-1y4p8pa { /* Target the main content container */
                background-color: var(--background-color);
            }

            /* Tombol Utama */
            .stButton>button {
                background-color: var(--primary-color);
                color: white;
                border: 2px solid var(--primary-color);
                font-weight: bold;
                padding: 0.5rem 1rem;
                border-radius: 8px;
                transition: all 0.2s ease-in-out;
            }
            .stButton>button:hover {
                background-color: var(--secondary-color);
                color: white;
                border: 2px solid var(--secondary-color);
                transform: translateY(-2px);
            }
            
            /* Tombol Hapus & Aksi Berbahaya */
            .stButton>button[kind="primary"] { /* Streamlit's primary button */
                background-color: #DC143C; /* Crimson */
                color: white;
                border: none;
            }
             .stButton>button[kind="primary"]:hover {
                background-color: #B22222; /* FireBrick */
                color: white;
            }

            /* Header dan Subheader */
            h1, h2, h3, h4, h5, h6 {
                color: var(--accent-color); /* Menggunakan accent-color untuk header */
                font-weight: bold;
                margin-top: 1.5rem;
                margin-bottom: 1rem;
            }
            h1 { font-size: 2.5rem; }
            h2 { font-size: 2rem; }
            h3 { font-size: 1.75rem; }

            /* Widget Styling - Perbaikan untuk input dan selectbox */
            .stTextInput>div>div>input, 
            .stNumberInput>div>div>input, 
            .stTextArea>div>div>textarea {
                background-color: var(--widget-background);
                color: var(--text-color);
                border: 1px solid rgba(0, 0, 0, 0.2);
                border-radius: 5px;
                padding: 0.5rem 1rem; /* Menambah padding horizontal */
                line-height: 1.5; /* Menyesuaikan tinggi baris */
                min-height: 38px; /* Menjamin tinggi minimum */
            }
            
            /* Styling untuk Selectbox */
            .stSelectbox>div>div { /* Container utama selectbox */
                background-color: var(--widget-background);
                color: var(--text-color);
                border: 1px solid rgba(0, 0, 0, 0.2);
                border-radius: 5px;
                padding: 0.25rem 1rem; /* Padding lebih kecil untuk selectbox */
                min-height: 38px; /* Menjamin tinggi minimum */
                display: flex;
                align-items: center; /* Pusatkan teks secara vertikal */
            }

            .stSelectbox>div>div:focus {
                border-color: var(--primary-color);
                box-shadow: 0 0 0 0.2rem rgba(135, 206, 235, 0.25);
            }

            /* Styling untuk opsi dropdown (saat dibuka) */
            .stSelectbox div[role="listbox"] {
                background-color: var(--widget-background);
                color: var(--text-color);
                border: 1px solid rgba(0, 0, 0, 0.2);
                border-radius: 5px;
            }

            .stSelectbox div[role="option"] {
                padding: 0.5rem 1rem;
                color: var(--text-color);
            }

            .stSelectbox div[role="option"]:hover {
                background-color: var(--secondary-color);
                color: white;
            }

            /* Metric Styling */
            .st-emotion-cache-1g6gooi { /* Target the metric container */
                background-color: var(--widget-background);
                border-radius: 10px;
                padding: 1rem;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                text-align: center;
            }
            .st-emotion-cache-1g6gooi > div > div:first-child { /* Metric label */
                color: var(--text-color);
                font-size: 0.9rem;
                opacity: 0.8;
            }
            .st-emotion-cache-1g6gooi > div > div:last-child { /* Metric value */
                color: var(--accent-color); /* Menggunakan accent-color untuk nilai metric */
                font-size: 1.8rem;
                font-weight: bold;
            }

            /* Expander Styling */
            .st-emotion-cache-p5m000 { /* Expander header */
                background-color: var(--widget-background);
                border-radius: 8px;
                padding: 0.8rem;
                margin-bottom: 0.5rem;
                border: 1px solid rgba(0, 0, 0, 0.1);
            }
            .st-emotion-cache-p5m000:hover {
                background-color: rgba(240, 248, 255, 0.8);
            }

            /* Tabs Styling */
            .stTabs [data-baseweb="tab-list"] {
                gap: 10px;
            }
            .stTabs [data-baseweb="tab"] {
                height: 50px;
                white-space: nowrap;
                background-color: var(--widget-background);
                border-radius: 8px 8px 0 0;
                gap: 10px;
                padding-left: 20px;
                padding-right: 20px;
                color: var(--text-color);
                font-weight: bold;
            }
            .stTabs [data-baseweb="tab"]:hover {
                background-color: rgba(240, 248, 255, 0.8);
            }
            .stTabs [data-baseweb="tab"][aria-selected="true"] {
                background-color: var(--primary-color);
                color: white;
                border-bottom: 3px solid var(--primary-color);
            }

            /* Dataframe Styling */
            .st-emotion-cache-1r4qj8v { /* Dataframe container */
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                overflow: hidden;
            }
            .st-emotion-cache-1r4qj8v table {
                background-color: var(--widget-background);
                color: var(--text-color);
            }
            .st-emotion-cache-1r4qj8v th {
                background-color: var(--primary-color);
                color: white;
                font-weight: bold;
            }
            .st-emotion-cache-1r4qj8v tr:nth-child(even) {
                background-color: rgba(240, 248, 255, 0.8);
            }
            /* Memastikan teks di dalam sel dataframe tidak terpotong secara vertikal */
            .st-emotion-cache-1r4qj8v td {
                white-space: normal !important; /* Izinkan teks untuk wrap */
                word-break: break-word; /* Pecah kata jika terlalu panjang */
                padding: 8px 10px; /* Sesuaikan padding */
            }
        </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


    # --- Fungsi Helper ---
    def run_query(query, params=(), fetch=None):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(query, params)
        if fetch == 'one': 
            result = c.fetchone()
        elif fetch == 'all': 
            result = c.fetchall()
        else: 
            result = None
        conn.commit()
        conn.close()
        return result

    def get_df(query, params=()):
        conn = sqlite3.connect(DB)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    # --- NEW: Accounting Functions ---
    def create_journal_entry(entry_date, description, entries, transaction_id=None, expense_id=None):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("BEGIN TRANSACTION")
            c.execute("INSERT INTO journal_entries (entry_date, description, transaction_id, expense_id) VALUES (?, ?, ?, ?)",
                      (entry_date, description, transaction_id, expense_id))
            journal_entry_id = c.lastrowid

            total_debit = 0
            total_kredit = 0
            for entry in entries:
                account_id = entry['account_id']
                debit = entry.get('debit', 0)
                kredit = entry.get('kredit', 0)
                c.execute("INSERT INTO journal_items (journal_entry_id, account_id, debit, kredit) VALUES (?, ?, ?, ?)",
                          (journal_entry_id, account_id, debit, kredit))
                total_debit += debit
                total_kredit += kredit
            
            if round(total_debit, 2) != round(total_kredit, 2):
                raise ValueError(f"Jurnal tidak seimbang! Debit: {total_debit}, Kredit: {total_kredit}")

            conn.commit()
            return True, "Jurnal berhasil dibuat."
        except Exception as e:
            conn.rollback()
            return False, f"Gagal membuat jurnal: {e}"
        finally:
            conn.close()

    def get_account_balance(account_id, end_date=None):
        conn = sqlite3.connect(DB)
        query = """
            SELECT 
                SUM(CASE WHEN ji.debit > 0 THEN ji.debit ELSE 0 END) AS total_debit,
                SUM(CASE WHEN ji.kredit > 0 THEN ji.kredit ELSE 0 END) AS total_kredit,
                a.normal_balance
            FROM journal_items ji
            JOIN journal_entries je ON ji.journal_entry_id = je.id
            JOIN accounts a ON ji.account_id = a.id
            WHERE ji.account_id = ?
        """
        params = [account_id]
        if end_date:
            query += " AND je.entry_date <= ?"
            params.append(end_date)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        if df.empty or df['total_debit'].isnull().all():
            return 0.0

        total_debit = df['total_debit'].iloc[0] if df['total_debit'].iloc[0] is not None else 0.0
        total_kredit = df['total_kredit'].iloc[0] if df['total_kredit'].iloc[0] is not None else 0.0
        normal_balance = df['normal_balance'].iloc[0]

        if normal_balance == 'Debit':
            balance = total_debit - total_kredit
        else: # Kredit
            balance = total_kredit - total_debit
        return balance

    # --- Fungsi Logika Bisnis ---
    def process_atomic_sale(cart, payment_method, employee_id, cash_received=0):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("BEGIN TRANSACTION")
            insufficient_items, products_map = [], {row['name']: {'id': row['id'], 'price': row['price']} for _, row in get_df("SELECT id, name, price FROM products").iterrows()}
            for product_name, qty in cart.items():
                product_id = products_map[product_name]['id']
                c.execute("SELECT i.name, i.stock, r.qty_per_unit FROM recipes r JOIN ingredients i ON r.ingredient_id = i.id WHERE r.product_id=?", (product_id,))
                for ing_name, stock, qty_per_unit in c.fetchall():
                    if stock < qty_per_unit * qty: 
                        insufficient_items.append(f"{ing_name} untuk {product_name}")
            if insufficient_items: 
                raise ValueError(f"Stok tidak cukup: {', '.join(insufficient_items)}")
            total_amount = sum(products_map[name]['price'] * qty for name, qty in cart.items())
            c.execute("INSERT INTO transactions (transaction_date, total_amount, payment_method, employee_id) VALUES (?, ?, ?, ?)", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total_amount, payment_method, employee_id))
            transaction_id = c.lastrowid
            for product_name, qty in cart.items():
                product_info = products_map[product_name]
                c.execute("INSERT INTO transaction_items (transaction_id, product_id, quantity, price_per_unit) VALUES (?, ?, ?, ?)", (transaction_id, product_info['id'], qty, product_info['price']))
                c.execute("SELECT ingredient_id, qty_per_unit FROM recipes WHERE product_id=?", (product_info['id'],))
                for ing_id, qty_per_unit in c.fetchall():
                    c.execute("UPDATE ingredients SET stock = stock - ? WHERE id=?", (qty_per_unit * qty, ing_id))
            
            # NEW: Create Journal Entry for Sale
            journal_entries = []
            # Debit Cash/Bank/Piutang Usaha
            if payment_method == 'Cash':
                cash_account_id = run_query("SELECT id FROM accounts WHERE account_name = 'Kas'", fetch='one')[0]
                journal_entries.append({'account_id': cash_account_id, 'debit': total_amount})
            elif payment_method == 'Qris' or payment_method == 'Card':
                bank_account_id = run_query("SELECT id FROM accounts WHERE account_name = 'Bank'", fetch='one')[0]
                journal_entries.append({'account_id': bank_account_id, 'debit': total_amount})
            # else: # Assume Piutang Usaha for other methods or if not specified
            #     ar_account_id = run_query("SELECT id FROM accounts WHERE account_name = 'Piutang Usaha'", fetch='one')[0]
            #     journal_entries.append({'account_id': ar_account_id, 'debit': total_amount})

            # Kredit Pendapatan Penjualan
            sales_revenue_account_id = run_query("SELECT id FROM accounts WHERE account_name = 'Pendapatan Penjualan'", fetch='one')[0]
            journal_entries.append({'account_id': sales_revenue_account_id, 'kredit': total_amount})

            # Jurnal HPP (Cost of Goods Sold) - ini lebih kompleks karena butuh HPP per produk
            # Untuk sementara, kita bisa asumsikan HPP dihitung terpisah atau diabaikan dulu
            # atau kita bisa ambil total modal dari fungsi laporan
            total_modal_sale = 0
            for product_name, qty in cart.items():
                product_id = products_map[product_name]['id']
                hpp_product_df = get_df("SELECT SUM(r.qty_per_unit * i.cost_per_unit) as hpp FROM recipes r JOIN ingredients i ON r.ingredient_id = i.id WHERE r.product_id=?", (product_id,))
                hpp_per_unit = hpp_product_df['hpp'].iloc[0] if not hpp_product_df.empty and hpp_product_df['hpp'].iloc[0] is not None else 0
                total_modal_sale += hpp_per_unit * qty
            
            if total_modal_sale > 0:
                hpp_account_id = run_query("SELECT id FROM accounts WHERE account_name = 'Harga Pokok Penjualan'", fetch='one')[0]
                inventory_account_id = run_query("SELECT id FROM accounts WHERE account_name = 'Persediaan Bahan Baku'", fetch='one')[0] # Asumsi ini akun persediaan
                journal_entries.append({'account_id': hpp_account_id, 'debit': total_modal_sale})
                journal_entries.append({'account_id': inventory_account_id, 'kredit': total_modal_sale})

            success_journal, msg_journal = create_journal_entry(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                f"Penjualan Transaksi #{transaction_id}",
                journal_entries,
                transaction_id=transaction_id
            )
            if not success_journal:
                raise ValueError(f"Gagal membuat jurnal penjualan: {msg_journal}")

            conn.commit()
            change = cash_received - total_amount if payment_method == 'Cash' and cash_received > 0 else 0
            return True, "Pesanan berhasil diproses!", transaction_id, change
        except Exception as e:
            conn.rollback()
            return False, str(e), None, 0
        finally: conn.close()

    def generate_receipt_pdf(transaction_id):
        conn = sqlite3.connect(DB)
        transaction = pd.read_sql_query("SELECT * FROM transactions WHERE id = ?", conn, params=(transaction_id,)).iloc[0]
        items_df = pd.read_sql_query("SELECT p.name, ti.quantity, ti.price_per_unit FROM transaction_items ti JOIN products p ON ti.product_id = p.id WHERE ti.transaction_id = ?", conn, params=(transaction_id,))
        conn.close()
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, 'Orca Cafe', 0, 1, 'C'); pdf.set_font("Arial", '', 10) # Mengganti nama cafe
        pdf.cell(0, 5, 'Struk Pembayaran', 0, 1, 'C'); pdf.ln(5); pdf.set_font("Arial", '', 12)
        pdf.cell(0, 8, f"No. Transaksi: {transaction['id']}", 0, 1)
        pdf.cell(0, 8, f"Tanggal: {transaction['transaction_date']}", 0, 1); pdf.ln(5); pdf.set_font("Arial", 'B', 12)
        pdf.cell(100, 10, 'Produk', 1); pdf.cell(30, 10, 'Qty', 1); pdf.cell(50, 10, 'Subtotal', 1, 1); pdf.set_font("Arial", '', 12)
        for _, item in items_df.iterrows():
            pdf.cell(100, 10, item['name'], 1); pdf.cell(30, 10, str(item['quantity']), 1); pdf.cell(50, 10, f"Rp {item['quantity'] * item['price_per_unit']:,.0f}", 1, 1)
        pdf.ln(10); pdf.set_font("Arial", 'B', 14)
        pdf.cell(130, 10, 'Total', 1); pdf.cell(50, 10, f"Rp {transaction['total_amount']:,.0f}", 1, 1)
        pdf.cell(130, 10, 'Metode Bayar', 1); pdf.cell(50, 10, transaction['payment_method'], 1, 1)
        return bytes(pdf.output())

    def delete_transaction(transaction_id):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("BEGIN TRANSACTION")
            c.execute("SELECT product_id, quantity FROM transaction_items WHERE transaction_id=?", (transaction_id,))
            for product_id, quantity in c.fetchall():
                c.execute("SELECT ingredient_id, qty_per_unit FROM recipes WHERE product_id=?", (product_id,))
                for ing_id, qty_per_unit in c.fetchall():
                    c.execute("UPDATE ingredients SET stock = stock + ? WHERE id=?", (qty_per_unit * quantity, ing_id))
            c.execute("DELETE FROM transaction_items WHERE transaction_id=?", (transaction_id,))
            c.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
            # NEW: Delete associated journal entries
            c.execute("DELETE FROM journal_items WHERE journal_entry_id IN (SELECT id FROM journal_entries WHERE transaction_id = ?)", (transaction_id,))
            c.execute("DELETE FROM journal_entries WHERE transaction_id = ?", (transaction_id,))
            conn.commit()
            return True, "Transaksi berhasil dihapus dan stok dikembalikan."
        except Exception as e:
            conn.rollback()
            return False, f"Gagal menghapus transaksi: {e}"
        finally: conn.close()

    # --- Menu Sidebar (Susunan Menu Ergonomis) ---
    menu_options = [
        "🛒 Kasir", 
        "📜 Riwayat Transaksi", 
        "📊 Laporan & Analisa", # Menggabungkan Laporan dan Analisa
        "💰 Harga Pokok Penjualan", # Mengganti nama menu HPP
        "📦 Manajemen Stok Bahan", # Mengganti nama menu Manajemen Stok
        "🍔 Manajemen Produk & Resep", # Mengganti nama menu Manajemen Produk
        "💸 Catat Pengeluaran", # Mengganti nama menu Pengeluaran
        "👥 Manajemen Karyawan",
        "📚 Akuntansi",
        "👤 Pelanggan & Pemasok",
        "🏢 Aktiva Tetap"
    ]
    if st.session_state.role == 'Admin':
        menu_options.append("🕒 Riwayat Absensi")
    menu_options.append("🗑️ Kelola & Hapus Data") # Selalu di akhir
    
    menu = st.sidebar.radio("Pilih Menu", menu_options)

    # --- Halaman Kasir (POS) ---
    if menu == "🛒 Kasir":
        st.header("🌺 Kasir (Point of Sale)")
        if 'cart' not in st.session_state: 
            st.session_state.cart = {}
        
        # Use columns for better layout
        col1, col2 = st.columns([3, 2]) # Adjusted column ratio for more product space

        with col1:
            st.subheader("Katalog Produk")
            search_term = st.text_input("Cari Nama Produk...", key="product_search", placeholder="Ketik nama produk...")
            
            query, params = ("SELECT name, price FROM products ORDER BY name", ())
            if search_term: 
                query, params = "SELECT name, price FROM products WHERE name LIKE ? ORDER BY name", (f'%{search_term}%',)
            
            products = run_query(query, params, fetch='all')
            
            if products:
                # Dynamic columns based on screen width or preference
                num_cols = 4 
                cols = st.columns(num_cols) 
                for i, (name, price) in enumerate(products):
                    with cols[i % num_cols]:
                        # Use a container for each product button for better visual separation
                        with st.container(border=True):
                            st.markdown(f"**{name}**")
                            st.markdown(f"Rp {price:,.0f}")
                            if st.button("Tambah", key=f"prod_{name}", use_container_width=True):
                                st.session_state.cart[name] = st.session_state.cart.get(name, 0) + 1
                                st.toast(f"'{name}' ditambahkan ke keranjang!"); st.rerun()
            else: 
                st.info("Produk tidak ditemukan.")

        with col2:
            st.subheader("Keranjang Belanja")
            if not st.session_state.cart: 
                st.info("Keranjang masih kosong. Silakan pilih produk dari katalog.")
            else:
                total_price = 0
                products_df = get_df("SELECT name, price FROM products")
                
                # Display cart items in a more structured way
                st.markdown("---")
                st.markdown("**Daftar Item:**")
                for name, qty in list(st.session_state.cart.items()):
                    price = products_df[products_df['name'] == name]['price'].iloc[0]
                    subtotal = price * qty
                    total_price += subtotal
                    
                    # Memperbaiki lebar kolom agar tulisan tidak terpotong
                    cart_col1, cart_col2, cart_col3 = st.columns([4, 2, 1]) 
                    with cart_col1:
                        st.write(f"**{name}** (x{qty})")
                    with cart_col2:
                        st.write(f"Rp {subtotal:,.0f}")
                    with cart_col3:
                        if st.button("Hapus", key=f"del_{name}", use_container_width=True):
                            del st.session_state.cart[name]
                            st.rerun()
                st.markdown("---")
                st.metric("Total Harga", f"Rp {total_price:,.0f}")

                with st.expander("Proses Pembayaran", expanded=True):
                    payment_method = st.selectbox("Metode Pembayaran", ["Cash", "Qris", "Card"])
                    cash_received = 0
                    if payment_method == 'Cash':
                        cash_received = st.number_input("Jumlah Uang Diterima (Rp)", min_value=0, step=1000, key="cash_input")
                        if cash_received >= total_price:
                            st.metric("Kembalian", f"Rp {cash_received - total_price:,.0f}")
                        else: 
                            st.warning("Uang diterima kurang dari total.")
                    
                    if st.button("✅ Proses Pembayaran", use_container_width=True, disabled=(payment_method == 'Cash' and cash_received < total_price)):
                        success, message, transaction_id, change_amount = process_atomic_sale(st.session_state.cart, payment_method, st.session_state.user_id, cash_received)
                        if success:
                            st.success(f"{message} (ID: {transaction_id})")
                            if payment_method == 'Cash': 
                                st.info(f"Kembalian: Rp {change_amount:,.0f}")
                            st.session_state.last_transaction_id = transaction_id; st.session_state.cart = {}
                        else: 
                            st.error(f"Gagal: {message}")
                        st.rerun()

            if 'last_transaction_id' in st.session_state and st.session_state.last_transaction_id:
                st.markdown("---")
                st.subheader("Opsi Transaksi Terakhir")
                last_id = st.session_state.last_transaction_id
                pdf_bytes = generate_receipt_pdf(last_id)
                
                col_receipt_btn1, col_receipt_btn2 = st.columns(2)
                with col_receipt_btn1:
                    st.download_button(label="📄 Cetak Struk (PDF)", data=pdf_bytes, file_name=f"struk_{last_id}.pdf", mime="application/pdf", use_container_width=True)
                with col_receipt_btn2:
                    if st.button("❌ Batalkan Pesanan", use_container_width=True, type="primary"):
                        success, message = delete_transaction(last_id)
                        if success: 
                            st.success(message); del st.session_state['last_transaction_id']
                        else: 
                            st.error(message)
                        st.rerun()
                st.caption("Membatalkan pesanan akan menghapus riwayat transaksi dan mengembalikan stok bahan baku.")

    # --- Halaman Manajemen Stok ---
    elif menu == "📦 Manajemen Stok Bahan": # Mengganti nama menu
        st.header("🌴 Manajemen Stok Bahan")
        low_stock_threshold = 10 
        low_stock_df = get_df(f"SELECT name, stock, unit FROM ingredients WHERE stock <= {low_stock_threshold}")
        
        if not low_stock_df.empty: 
            st.warning(f"⚠️ **Perhatian!** Bahan berikut hampir habis (stok <= {low_stock_threshold}):")
            st.dataframe(low_stock_df, use_container_width=True)
        
        tabs = st.tabs(["📊 Daftar Bahan", "➕ Tambah Bahan", "✏️ Edit Bahan"])
        
        with tabs[0]:
            st.subheader("Daftar Bahan Saat Ini")
            search_ing = st.text_input("Cari Nama Bahan...", key="ingredient_search", placeholder="Ketik nama bahan...")
            query, params = ("SELECT id, name AS 'Nama', unit AS 'Unit', stock AS 'Stok', cost_per_unit AS 'HPP/Unit', pack_price AS 'Harga Kemasan', pack_weight AS 'Berat Kemasan' FROM ingredients", ())
            if search_ing: 
                query += " WHERE name LIKE ?"; params = (f'%{search_ing}%',)
            # Memperbaiki lebar kolom agar tulisan tidak terpotong
            st.dataframe(get_df(query, params).style.format({'HPP/Unit': 'Rp {:,.2f}', 'Harga Kemasan': 'Rp {:,.2f}'}), use_container_width=True, column_config={
                "Nama": st.column_config.Column(width="medium"),
                "Unit": st.column_config.Column(width="small"),
                "Stok": st.column_config.Column(width="small"),
                "HPP/Unit": st.column_config.Column(width="medium"),
                "Harga Kemasan": st.column_config.Column(width="medium"),
                "Berat Kemasan": st.column_config.Column(width="medium")
            })
        
        with tabs[1]:
            st.subheader("Tambah Bahan Baru")
            with st.form("add_ingredient_form"):
                name = st.text_input("Nama Bahan", placeholder="Contoh: Biji Kopi Arabika")
                unit = st.text_input("Satuan/Unit (e.g., gr, ml, pcs)", placeholder="Contoh: gram")
                stock = st.number_input("Jumlah Stok Awal", value=0.0, format="%.2f")
                
                st.markdown("---")
                st.info("Kalkulator Harga Pokok per Satuan (HPP/Unit)")
                pack_price = st.number_input("Harga Beli per Kemasan (Rp)", value=0.0, format="%.2f")
                pack_weight = st.number_input("Isi/Berat per Kemasan (sesuai satuan)", value=0.0, format="%.2f")
                
                cost_per_unit = (pack_price / pack_weight) if pack_weight > 0 else 0
                st.metric("Harga Pokok per Satuan", f"Rp {cost_per_unit:,.2f}")
                
                if st.form_submit_button("Tambah Bahan"):
                    if name and unit:
                        run_query("INSERT INTO ingredients (name, unit, cost_per_unit, stock, pack_weight, pack_price) VALUES (?, ?, ?, ?, ?, ?)", (name, unit, cost_per_unit, stock, pack_weight, pack_price))
                        st.success(f"Bahan '{name}' berhasil ditambahkan."); st.rerun()
                    else:
                        st.error("Nama dan Satuan Bahan tidak boleh kosong.")
        
        with tabs[2]:
            st.subheader("Edit Bahan")
            search_term = st.text_input("Ketik nama bahan untuk diedit", key="edit_ing_search", placeholder="Cari bahan...")
            
            if search_term:
                ingredient_data = run_query("SELECT * FROM ingredients WHERE name LIKE ?", (f'%{search_term}%',), fetch='one')
                if ingredient_data:
                    with st.form("edit_ingredient_form"):
                        st.info(f"Mengedit data untuk: **{ingredient_data[1]}**")
                        name = st.text_input("Nama Bahan", value=ingredient_data[1])
                        unit = st.text_input("Satuan/Unit", value=ingredient_data[2])
                        stock = st.number_input("Jumlah Stok", value=float(ingredient_data[4]), format="%.2f")
                        pack_price = st.number_input("Harga Beli per Kemasan (Rp)", value=float(ingredient_data[6]), format="%.2f")
                        pack_weight = st.number_input("Isi/Berat per Kemasan", value=float(ingredient_data[5]), format="%.2f")
                        
                        cost_per_unit = (pack_price / pack_weight) if pack_weight > 0 else 0
                        st.metric("Harga Pokok per Satuan", f"Rp {cost_per_unit:,.2f}")
                        
                        if st.form_submit_button("Simpan Perubahan"):
                            run_query("UPDATE ingredients SET name=?, unit=?, cost_per_unit=?, stock=?, pack_weight=?, pack_price=? WHERE id=?", (name, unit, cost_per_unit, stock, pack_weight, pack_price, ingredient_data[0]))
                            st.success(f"Bahan '{name}' diperbarui."); st.rerun()
                else:
                    st.warning("Bahan tidak ditemukan. Silakan cek kembali nama yang dimasukkan.")
            else:
                st.info("Ketik nama bahan di atas untuk mulai mengedit.")

    # --- Halaman Manajemen Produk ---
    elif menu == "🍔 Manajemen Produk & Resep": # Mengganti nama menu
        st.header("🍛 Manajemen Produk & Resep")
        tabs = st.tabs(["Daftar Produk", "➕ Tambah Produk", "✏️ Edit Produk", "🍲 Kelola Resep"])
        
        with tabs[0]:
            st.subheader("Daftar Produk Saat Ini")
            # Memperbaiki lebar kolom agar tulisan tidak terpotong
            st.dataframe(get_df("SELECT id, name AS 'Nama Produk', price AS 'Harga Jual' FROM products").style.format({'Harga Jual': 'Rp {:,.0f}'}), use_container_width=True, column_config={
                "Nama Produk": st.column_config.Column(width="medium"),
                "Harga Jual": st.column_config.Column(width="small")
            })
        
        with tabs[1]:
            st.subheader("Tambah Produk Baru")
            with st.form("add_product_form"):
                name = st.text_input("Nama Produk", placeholder="Contoh: Coffee Latte")
                price = st.number_input("Harga Jual", value=0.0, format="%.2f")
                if st.form_submit_button("Tambah Produk"):
                    if name and price > 0:
                        run_query("INSERT INTO products (name, price) VALUES (?, ?)", (name, price)); st.success(f"Produk '{name}' ditambahkan!"); st.rerun()
                    else:
                        st.error("Nama Produk dan Harga Jual tidak boleh kosong atau nol.")
        
        with tabs[2]:
            st.subheader("Edit Produk")
            search_term = st.text_input("Ketik nama produk untuk diedit", key="edit_prod_search", placeholder="Cari produk...")
            if search_term:
                prod_data = run_query("SELECT * FROM products WHERE name LIKE ?", (f'%{search_term}%',), fetch='one')
                if prod_data:
                    with st.form("edit_product_form"):
                        st.info(f"Mengedit data untuk: **{prod_data[1]}**")
                        name = st.text_input("Nama Produk", value=prod_data[1])
                        price = st.number_input("Harga Jual", value=float(prod_data[2]), format="%.2f")
                        if st.form_submit_button("Simpan Perubahan"):
                            if name and price > 0:
                                run_query("UPDATE products SET name=?, price=? WHERE id=?", (name, price, prod_data[0])); st.success("Produk diperbarui!"); st.rerun()
                            else:
                                st.error("Nama Produk dan Harga Jual tidak boleh kosong atau nol.")
                else:
                    st.warning("Produk tidak ditemukan.")
            else:
                st.info("Ketik nama produk di atas untuk mulai mengedit.")
        
        with tabs[3]:
            st.subheader("Kelola Resep per Produk")
            products_df = get_df("SELECT id, name FROM products")
            if not products_df.empty:
                product_id = st.selectbox("Pilih Produk", products_df['id'], format_func=lambda x: products_df[products_df['id'] == x]['name'].iloc[0], key="recipe_prod_select")
                
                st.markdown("#### Resep Saat Ini:")
                current_recipe_df = get_df("SELECT i.name AS 'Bahan', r.qty_per_unit AS 'Jumlah Dibutuhkan', i.unit AS 'Satuan' FROM recipes r JOIN ingredients i ON r.ingredient_id = i.id WHERE r.product_id=?", (product_id,))
                if not current_recipe_df.empty:
                    # Memperbaiki lebar kolom agar tulisan tidak terpotong
                    st.dataframe(current_recipe_df, use_container_width=True, column_config={
                        "Bahan": st.column_config.Column(width="medium"),
                        "Jumlah Dibutuhkan": st.column_config.Column(width="small"),
                        "Satuan": st.column_config.Column(width="small")
                    })
                else:
                    st.info("Produk ini belum memiliki resep. Tambahkan bahan di bawah.")

                st.markdown("---")
                st.markdown("#### Tambah/Update Bahan ke Resep:")
                with st.form("recipe_form"):
                    ingredients_df = get_df("SELECT id, name, unit FROM ingredients")
                    if not ingredients_df.empty:
                        ingredient_options = {f"{row['name']} ({row['unit']})": row['id'] for _, row in ingredients_df.iterrows()}
                        selected_ing_name = st.selectbox("Pilih Bahan", list(ingredient_options.keys()), key="recipe_ing_select")
                        ingredient_id = ingredient_options[selected_ing_name]
                        
                        qty = st.number_input("Jumlah Dibutuhkan", format="%.2f", min_value=0.01)
                        
                        if st.form_submit_button("Tambah/Update Bahan ke Resep"):
                            run_query("REPLACE INTO recipes (product_id, ingredient_id, qty_per_unit) VALUES (?, ?, ?)", (product_id, ingredient_id, qty)); st.success("Resep diperbarui."); st.rerun()
                    else: 
                        st.warning("Tidak ada bahan baku. Tambahkan di menu Manajemen Stok terlebih dahulu.")
            else: 
                st.info("Tidak ada produk untuk dikelola resepnya. Tambahkan produk terlebih dahulu.")

    # --- Halaman Riwayat Transaksi ---
    elif menu == "📜 Riwayat Transaksi":
        st.header("🌊 Riwayat Transaksi")
        
        col_search, col_filter = st.columns([2, 1])
        with col_search:
            search_id = st.text_input("Cari dengan ID Transaksi...", placeholder="Ketik ID transaksi...")
        with col_filter:
            # Optional: Add date range filter for transactions
            today = date.today()
            default_start = today.replace(day=1)
            transaction_start_date = st.date_input("Dari Tanggal", default_start)
            transaction_end_date = st.date_input("Sampai Tanggal", today)

        query = "SELECT t.id AS 'ID', t.transaction_date AS 'Waktu', t.total_amount AS 'Total', t.payment_method AS 'Metode', e.name AS 'Kasir' FROM transactions t JOIN employees e ON t.employee_id = e.id WHERE 1=1"
        params = []

        if search_id.isdigit(): 
            query += " AND t.id = ?"
            params.append(int(search_id))
        
        query += " AND t.transaction_date BETWEEN ? AND ?"
        params.append(transaction_start_date.strftime("%Y-%m-%d 00:00:00"))
        params.append(transaction_end_date.strftime("%Y-%m-%d 23:59:59"))

        query += " ORDER BY t.id DESC"
        transactions_df = get_df(query, params)
        
        # Memperbaiki lebar kolom agar tulisan tidak terpotong
        st.dataframe(transactions_df.style.format({'Total': 'Rp {:,.0f}'}), use_container_width=True, column_config={
            "ID": st.column_config.Column(width="small"),
            "Waktu": st.column_config.Column(width="medium"),
            "Total": st.column_config.Column(width="small"),
            "Metode": st.column_config.Column(width="small"),
            "Kasir": st.column_config.Column(width="small")
        })
        
        st.markdown("---")
        st.subheader("Kelola Transaksi")
        if not transactions_df.empty:
            selected_id = st.selectbox("Pilih ID dari tabel di atas untuk melihat detail atau menghapus", options=transactions_df['ID'].tolist(), key="selected_trans_id")
            if selected_id:
                col_detail, col_action = st.columns(2)
                with col_detail:
                    st.markdown(f"#### Detail Item Transaksi #{selected_id}:")
                    items_df = get_df("SELECT p.name AS 'Produk', ti.quantity AS 'Jumlah', ti.price_per_unit AS 'Harga Satuan', (ti.quantity * ti.price_per_unit) AS 'Subtotal' FROM transaction_items ti JOIN products p ON ti.product_id = p.id WHERE ti.transaction_id = ?", (selected_id,))
                    # Memperbaiki lebar kolom agar tulisan tidak terpotong
                    st.dataframe(items_df.style.format({'Harga Satuan': 'Rp {:,.0f}', 'Subtotal': 'Rp {:,.0f}'}), use_container_width=True, column_config={
                        "Produk": st.column_config.Column(width="medium"),
                        "Jumlah": st.column_config.Column(width="small"),
                        "Harga Satuan": st.column_config.Column(width="small"),
                        "Subtotal": st.column_config.Column(width="small")
                    })
                with col_action:
                    st.markdown("#### Opsi:")
                    if st.button("Hapus Transaksi Ini", type="primary", key=f"del_trans_{selected_id}", use_container_width=True):
                        success, message = delete_transaction(selected_id)
                        if success: 
                            st.success(message)
                        else: 
                            st.error(message)
                        st.rerun()
                    st.caption("Penghapusan transaksi akan mengembalikan stok bahan baku dan menghapus jurnal terkait.")
        else: 
            st.info("Tidak ada transaksi untuk dikelola dalam rentang tanggal ini.")

    # --- Halaman Laporan (REVISI BESAR) ---
    elif menu == "📊 Laporan & Analisa": # Mengganti nama menu
        st.header("📈 Laporan & Analisa Bisnis")
        
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input("Tanggal Mulai", date.today().replace(day=1))
        with col_date2:
            end_date = st.date_input("Tanggal Akhir", date.today())
        
        start_datetime, end_datetime = datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date, datetime.max.time())
        
        st.subheader("Ringkasan Kinerja Bisnis")
        
        trans_df = get_df("SELECT * FROM transactions WHERE transaction_date BETWEEN ? AND ?", (start_datetime.strftime("%Y-%m-%d %H:%M:%S"), end_datetime.strftime("%Y-%m-%d %H:%M:%S")))
        expenses_df = get_df("SELECT * FROM expenses WHERE date BETWEEN ? AND ?", (start_date.isoformat(), end_date.isoformat()))
        
        salary_details = []
        total_gaji = 0
        employees_df = get_df("SELECT id, name, wage_amount, wage_period FROM employees WHERE is_active = 1")
        attendance_df = get_df("SELECT * FROM attendance WHERE check_in BETWEEN ? AND ?", (start_datetime.strftime("%Y-%m-%d %H:%M:%S"), end_datetime.strftime("%Y-%m-%d %H:%M:%S")))
        
        if not attendance_df.empty:
            attendance_df['check_in'] = pd.to_datetime(attendance_df['check_in'])
            attendance_df['check_out'] = pd.to_datetime(attendance_df['check_out'])
            for _, emp in employees_df.iterrows():
                emp_attendance = attendance_df[attendance_df['employee_id'] == emp['id']].copy()
                if not emp_attendance.empty:
                    emp_salary = 0
                    if emp['wage_period'] == 'Per Jam':
                        emp_attendance['duration'] = (emp_attendance['check_out'] - emp_attendance['check_in']).dt.total_seconds() / 3600
                        total_hours = emp_attendance['duration'].sum()
                        emp_salary = total_hours * emp['wage_amount']
                        salary_details.append({'Karyawan': emp['name'], 'Detail': f'{total_hours:.2f} jam kerja', 'Total Gaji': emp_salary})
                    elif emp['wage_period'] == 'Per Hari':
                        work_days = emp_attendance['check_in'].dt.date.nunique()
                        emp_salary = work_days * emp['wage_amount']
                        salary_details.append({'Karyawan': emp['name'], 'Detail': f'{work_days} hari kerja', 'Total Gaji': emp_salary})
                    elif emp['wage_period'] == 'Per Bulan':
                        days_in_range = (end_date - start_date).days + 1
                        emp_salary = (emp['wage_amount'] / 30) * days_in_range
                        salary_details.append({'Karyawan': emp['name'], 'Detail': f'{days_in_range} hari dalam rentang', 'Total Gaji': emp_salary})
                    total_gaji += emp_salary
        salary_df = pd.DataFrame(salary_details)

        total_pendapatan = trans_df['total_amount'].sum()
        total_modal = 0
        if not trans_df.empty:
            items_df = get_df(f"SELECT ti.quantity, r.qty_per_unit, i.cost_per_unit FROM transaction_items ti JOIN recipes r ON ti.product_id = r.product_id JOIN ingredients i ON r.ingredient_id = i.id WHERE ti.transaction_id IN ({','.join(map(str, trans_df['id']))})")
            if not items_df.empty: 
                total_modal = (items_df['quantity'] * items_df['qty_per_unit'] * items_df['cost_per_unit']).sum()
        
        op_expenses_df = expenses_df[expenses_df['category'] == 'Operasional']
        other_expenses_df = expenses_df[expenses_df['category'] == 'Lainnya']
        total_biaya_operasional = op_expenses_df['amount'].sum()
        total_pengeluaran_lainnya = other_expenses_df['amount'].sum()

        laba_kotor = total_pendapatan - total_modal
        laba_bersih = laba_kotor - total_biaya_operasional - total_pengeluaran_lainnya - total_gaji
        margin_laba_kotor = (laba_kotor / total_pendapatan * 100) if total_pendapatan > 0 else 0
        margin_laba_bersih = (laba_bersih / total_pendapatan * 100) if total_pendapatan > 0 else 0
        
        kpi_cols = st.columns(5)
        kpi_cols[0].metric("Total Pendapatan", f"Rp {total_pendapatan:,.0f}")
        kpi_cols[1].metric("Total Modal (HPP)", f"Rp {total_modal:,.0f}")
        kpi_cols[2].metric("Total Gaji Karyawan", f"Rp {total_gaji:,.0f}")
        kpi_cols[3].metric("Biaya Operasional", f"Rp {total_biaya_operasional:,.0f}")
        kpi_cols[4].metric("Pengeluaran Lain", f"Rp {total_pengeluaran_lainnya:,.0f}")
        
        st.markdown("---")
        st.metric("Laba Bersih", f"Rp {laba_bersih:,.0f}", delta=f"{margin_laba_bersih:.1f}% Margin")

        if total_modal > 0 or total_biaya_operasional > 0 or total_pengeluaran_lainnya > 0 or total_gaji > 0:
            st.markdown("#### Komposisi Biaya")
            fig_pie = go.Figure(data=[go.Pie(labels=['Modal (HPP)', 'Gaji Karyawan', 'Biaya Operasional', 'Pengeluaran Lain'], values=[total_modal, total_gaji, total_biaya_operasional, total_pengeluaran_lainnya], hole=.3)])
            fig_pie.update_layout(title_text='Distribusi Biaya', title_x=0.5) # Center title
            st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("---")
        st.subheader("💡 Analisa & Saran Manajemen")
        
        # Initialize laris_df to prevent UnboundLocalError
        laris_df = pd.DataFrame(columns=['Produk', 'Jumlah Terjual'])
        
        col_an1, col_an2 = st.columns(2)
        with col_an1:
            if not trans_df.empty:
                st.markdown("#### Kinerja Produk Terlaris")
                laris_df = get_df(f"SELECT p.name AS 'Produk', SUM(ti.quantity) as 'Jumlah Terjual' FROM transaction_items ti JOIN products p ON ti.product_id = p.id WHERE ti.transaction_id IN ({','.join(map(str, trans_df['id']))}) GROUP BY p.name ORDER BY total_qty DESC LIMIT 5")
                st.dataframe(laris_df, hide_index=True, use_container_width=True)

                st.markdown("#### Produk Paling Menguntungkan")
                hpp_df = get_df("SELECT p.id, p.name, p.price, IFNULL(SUM(r.qty_per_unit * i.cost_per_unit), 0) as hpp FROM products p LEFT JOIN recipes r ON p.id = r.product_id LEFT JOIN ingredients i ON r.ingredient_id = i.id GROUP BY p.id")
                trans_items_df = get_df(f"SELECT product_id, quantity FROM transaction_items WHERE transaction_id IN ({','.join(map(str, trans_df['id']))})")
                merged_df = pd.merge(trans_items_df, hpp_df, left_on='product_id', right_on='id')
                merged_df['profit'] = (merged_df['price'] - merged_df['hpp']) * merged_df['quantity']
                profit_summary = merged_df.groupby('name')['profit'].sum().reset_index().sort_values(by='profit', ascending=False).head(5)
                st.dataframe(profit_summary.style.format({'profit': 'Rp {:,.0f}'}), hide_index=True, use_container_width=True)

                st.markdown("#### Tren Pendapatan Harian")
                trans_df['transaction_date'] = pd.to_datetime(trans_df['transaction_date'])
                daily_revenue = trans_df.set_index('transaction_date').resample('D')['total_amount'].sum().reset_index()
                fig_trend = go.Figure(data=go.Scatter(x=daily_revenue['transaction_date'], y=daily_revenue['total_amount'], mode='lines+markers'))
                fig_trend.update_layout(title_text='Tren Pendapatan Harian', xaxis_title='Tanggal', yaxis_title='Pendapatan (Rp)', title_x=0.5)
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("Belum ada data penjualan pada rentang tanggal ini.")
        
        with col_an2:
            st.markdown("#### Saran Santai untuk Bisnis Anda")
            saran = []
            total_biaya = total_modal + total_gaji + total_biaya_operasional + total_pengeluaran_lainnya
            
            # Inisialisasi variabel untuk menghindari UnboundLocalError
            produk_laris = ""
            produk_untung = ""
            
            if total_pendapatan > 0:
                if laba_bersih < 0:
                    saran.append(" Waduh, profitnya lagi merah nih. Coba cek lagi harga modal (HPP) atau biaya operasional, mungkin ada yang bisa ditekan. Naikin harga dikit buat produk best seller juga boleh dicoba, lho.")
                if total_biaya > 0 and (total_gaji / total_biaya) > 0.5:
                    saran.append(" Gaji karyawan porsinya gede banget, nih. Mungkin bisa dicek lagi jadwalnya, biar jam kerja lebih efisien dan nggak banyak lemburan yang nggak perlu.")
                
                # Periksa apakah laris_df dan profit_summary ada dan tidak kosong
                if 'laris_df' in locals() and not laris_df.empty and 'profit_summary' in locals() and not profit_summary.empty:
                    produk_laris = laris_df['Produk'].iloc[0]
                    produk_untung = profit_summary['name'].iloc[0]
                    if produk_laris != produk_untung:
                        saran.append(f" Eh, tau gak? '{produk_laris}' paling laku, tapi '{produk_untung}' paling untung. Gimana kalau kasir diajarin buat nawarin '{produk_untung}' tiap ada yang beli '{produk_laris}'? Cuan dobel!")
            
            if 'laris_df' in locals() and not laris_df.empty:
                saran.append(f" Mantap! '{laris_df['Produk'].iloc[0]}' lagi naik daun. Stoknya jangan sampai kosong, ya. Mungkin bisa dibikinin varian baru biar makin hits?")
            
            if total_biaya > 0 and (total_biaya_operasional / total_biaya) > 0.4:
                saran.append(" Biaya operasional kayaknya agak boros. Coba deh ngobrol lagi sama supplier, siapa tau bisa dapet harga lebih miring. Cek juga tagihan listrik sama air, kali aja ada yang bocor.")
            
            if len(saran) < 3:
                saran.extend([
                    " Coba deh, luangin waktu tiap minggu buat liat laporan ini. Biar makin jago baca situasi dan ambil keputusan.",
                    " Produk yang lagi laris itu 'harta karun'. Sering-sering pamerin di sosmed biar makin banyak yang penasaran!",
                    " Penasaran pelanggan maunya apa? Coba deh taruh kotak saran atau bikin polling di Instagram. Siapa tau ada masukan emas!"
                ])

            random.shuffle(saran)
            for i in range(min(3, len(saran))):
                st.info(saran[i])

            summary_text = f"Laporan Orca Cafe ({start_date.strftime('%d %b')} - {end_date.strftime('%d %b')})\n- Pendapatan: Rp {total_pendapatan:,.0f}\n- Modal (HPP): Rp {total_modal:,.0f}\n- Gaji: Rp {total_gaji:,.0f}\n- Laba Bersih: Rp {laba_bersih:,.0f}"
            st.link_button("Kirim Ringkasan via WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(summary_text)}")

        st.markdown("---")
        st.subheader("🗃️ Detail Data")
        if not trans_df.empty:
            with st.expander("Detail Data Transaksi (Data Mentah)"): st.dataframe(trans_df, use_container_width=True)
        if not salary_df.empty:
            with st.expander("Detail Gaji Karyawan"): st.dataframe(salary_df.style.format({'Total Gaji': 'Rp {:,.2f}'}), use_container_width=True)
        if not op_expenses_df.empty:
            with st.expander("Detail Biaya Operasional"): st.dataframe(op_expenses_df, use_container_width=True)
        if not other_expenses_df.empty:
            with st.expander("Detail Pengeluaran Lainnya"): st.dataframe(other_expenses_df, use_container_width=True)

    # --- Halaman Pengeluaran ---
    elif menu == "💸 Catat Pengeluaran": # Mengganti nama menu
        st.header("💸 Catat Pengeluaran")
        tabs = st.tabs(["Daftar Pengeluaran", "➕ Tambah Pengeluaran", "✏️ Edit Pengeluaran"])
        
        with tabs[0]:
            st.subheader("Daftar Pengeluaran")
            # Memperbaiki lebar kolom agar tulisan tidak terpotong
            st.dataframe(get_df("SELECT id, date AS 'Tanggal', category AS 'Kategori', description AS 'Deskripsi', amount AS 'Jumlah', payment_method AS 'Metode Pembayaran', account_id AS 'ID Akun' FROM expenses").style.format({'Jumlah': 'Rp {:,.2f}'}), use_container_width=True, column_config={
                "Tanggal": st.column_config.Column(width="small"),
                "Kategori": st.column_config.Column(width="small"),
                "Deskripsi": st.column_config.Column(width="medium"),
                "Jumlah": st.column_config.Column(width="small"),
                "Metode Pembayaran": st.column_config.Column(width="small"),
                "ID Akun": st.column_config.Column(width="small")
            })
        
        with tabs[1]:
            st.subheader("Tambah Pengeluaran Baru")
            accounts_df = get_df("SELECT id, account_code, account_name FROM accounts WHERE account_type = 'Beban' OR account_type = 'Aset'")
            account_options = {f"{row['account_code']} - {row['account_name']}": row['id'] for _, row in accounts_df.iterrows()}
            
            with st.form("add_expense_form"):
                date_exp = st.date_input("Tanggal", date.today())
                category = st.selectbox("Kategori", ["Operasional", "Lainnya"])
                description = st.text_input("Deskripsi", placeholder="Contoh: Pembelian ATK, Bayar Listrik")
                amount = st.number_input("Jumlah", value=0.01, format="%.2f", min_value=0.01)
                payment_method = st.selectbox("Metode Pembayaran", ["Cash", "Transfer"])
                
                # Ensure account_options is not empty before creating selectbox
                if account_options:
                    selected_account_name = st.selectbox("Pilih Akun Beban/Aset", list(account_options.keys()))
                else:
                    st.warning("Tidak ada akun Beban/Aset yang tersedia. Harap tambahkan di menu Akuntansi > Daftar Akun.")
                    selected_account_name = None # Prevent error if no accounts

                if st.form_submit_button("Tambah"):
                    if selected_account_name and description and amount > 0:
                        selected_account_id = account_options[selected_account_name]
                        conn = sqlite3.connect(DB)
                        c = conn.cursor()
                        try:
                            c.execute("BEGIN TRANSACTION")
                            c.execute("INSERT INTO expenses (date, category, description, amount, payment_method, account_id) VALUES (?, ?, ?, ?, ?, ?)", 
                                      (date_exp.isoformat(), category, description, amount, payment_method, selected_account_id))
                            expense_id = c.lastrowid
                            conn.commit()

                            # NEW: Create Journal Entry for Expense
                            journal_entries = []
                            # Debit Beban/Aset
                            journal_entries.append({'account_id': selected_account_id, 'debit': amount})
                            # Kredit Kas/Bank
                            if payment_method == 'Cash':
                                cash_account_id = run_query("SELECT id FROM accounts WHERE account_name = 'Kas'", fetch='one')[0]
                                journal_entries.append({'account_id': cash_account_id, 'kredit': amount})
                            elif payment_method == 'Transfer':
                                bank_account_id = run_query("SELECT id FROM accounts WHERE account_name = 'Bank'", fetch='one')[0]
                                journal_entries.append({'account_id': bank_account_id, 'kredit': amount})
                            
                            success_journal, msg_journal = create_journal_entry(
                                date_exp.isoformat(),
                                f"Pengeluaran: {description}",
                                journal_entries,
                                expense_id=expense_id
                            )
                            if success_journal:
                                st.success("Ditambahkan dan jurnal dibuat!"); st.rerun()
                            else:
                                st.error(f"Ditambahkan, tapi gagal membuat jurnal: {msg_journal}. Harap periksa jurnal secara manual.")
                                st.rerun() # Rerun anyway to show the expense
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Gagal menambahkan pengeluaran: {e}")
                        finally:
                            conn.close()
                    else:
                        st.error("Harap lengkapi semua kolom yang wajib diisi (Deskripsi, Jumlah, dan Akun).")

        with tabs[2]:
            st.subheader("Edit Pengeluaran")
            search_term = st.text_input("Ketik deskripsi pengeluaran untuk diedit", key="edit_exp_search", placeholder="Cari pengeluaran...")
            if search_term:
                exp_data = run_query("SELECT * FROM expenses WHERE description LIKE ?", (f'%{search_term}%',), fetch='one')
                if exp_data:
                    accounts_df = get_df("SELECT id, account_code, account_name FROM accounts WHERE account_type = 'Beban' OR account_type = 'Aset'")
                    account_options = {f"{row['account_code']} - {row['account_name']}": row['id'] for _, row in accounts_df.iterrows()}
                    
                    # Get current account name for default selection
                    current_account_name_tuple = run_query("SELECT account_code || ' - ' || account_name FROM accounts WHERE id = ?", (exp_data[6],), fetch='one')
                    current_account_name = current_account_name_tuple[0] if current_account_name_tuple else list(account_options.keys())[0]

                    with st.form("edit_expense_form"):
                        st.info(f"Mengedit data untuk: **{exp_data[3]}**")
                        date_exp = st.date_input("Tanggal", value=datetime.strptime(exp_data[1], '%Y-%m-%d').date())
                        category = st.selectbox("Kategori", ["Operasional", "Lainnya"], index=["Operasional", "Lainnya"].index(exp_data[2] if exp_data[2] else "Lainnya"))
                        description = st.text_input("Deskripsi", value=exp_data[3])
                        amount = st.number_input("Jumlah", value=float(exp_data[4]), format="%.2f", min_value=0.01)
                        payment_method = st.selectbox("Metode Pembayaran", ["Cash", "Transfer"], index=["Cash", "Transfer"].index(exp_data[5]))
                        
                        if account_options:
                            selected_account_name_edit = st.selectbox("Pilih Akun Beban/Aset", list(account_options.keys()), index=list(account_options.keys()).index(current_account_name))
                        else:
                            st.warning("Tidak ada akun Beban/Aset yang tersedia. Harap tambahkan di menu Akuntansi > Daftar Akun.")
                            selected_account_name_edit = None

                        if st.form_submit_button("Simpan Perubahan"):
                            if selected_account_name_edit and description and amount > 0:
                                selected_account_id_edit = account_options[selected_account_name_edit]
                                run_query("UPDATE expenses SET date=?, category=?, description=?, amount=?, payment_method=?, account_id=? WHERE id=?", (date_exp.isoformat(), category, description, amount, payment_method, selected_account_id_edit, exp_data[0])); st.success("Diperbarui!"); st.rerun()
                            else:
                                st.error("Harap lengkapi semua kolom yang wajib diisi (Deskripsi, Jumlah, dan Akun).")
                else:
                    st.warning("Pengeluaran tidak ditemukan.")
            else:
                st.info("Ketik deskripsi pengeluaran di atas untuk mulai mengedit.")

    # --- Halaman HPP ---
    elif menu == "💰 Harga Pokok Penjualan": # Mengganti nama menu
        st.header("💰 Harga Pokok Penjualan (HPP)")
        def get_product_hpp(product_id):
            df = get_df("SELECT SUM(r.qty_per_unit * i.cost_per_unit) as hpp FROM recipes r JOIN ingredients i ON r.ingredient_id = i.id WHERE r.product_id=?", (product_id,))
            return df['hpp'].iloc[0] if not df.empty and df['hpp'].iloc[0] is not None else 0
        prods_df = get_df("SELECT * FROM products")
        if not prods_df.empty:
            hpp_data = []
            for _, row in prods_df.iterrows():
                hpp = get_product_hpp(row['id'])
                profit = row['price'] - hpp
                hpp_data.append({"Nama Produk": row['name'], "Harga Jual": row['price'], "HPP (Modal)": hpp, "Profit Kotor": profit})
            df_hpp = pd.DataFrame(hpp_data)
            # Memperbaiki lebar kolom agar tulisan tidak terpotong
            st.dataframe(df_hpp.style.format({'Harga Jual': 'Rp {:,.0f}', 'HPP (Modal)': 'Rp {:,.2f}', 'Profit Kotor': 'Rp {:,.2f}'}), use_container_width=True, column_config={
                "Nama Produk": st.column_config.Column(width="medium"),
                "Harga Jual": st.column_config.Column(width="small"),
                "HPP (Modal)": st.column_config.Column(width="small"),
                "Profit Kotor": st.column_config.Column(width="small")
            })
        else:
            st.info("Tidak ada produk untuk menghitung HPP. Silakan tambahkan produk terlebih dahulu.")

    # --- Halaman Manajemen Karyawan ---
    elif menu == "👥 Manajemen Karyawan":
        st.header("👥 Manajemen Karyawan")
        tabs = st.tabs(["Daftar Karyawan", "➕ Tambah Karyawan", "✏️ Edit Karyawan", "🕒 Absensi Hari Ini"])
        
        with tabs[0]:
            st.subheader("Daftar Karyawan")
            # Memperbaiki lebar kolom agar tulisan tidak terpotong
            st.dataframe(get_df("SELECT id, name AS 'Nama', role AS 'Peran', wage_amount AS 'Jumlah Gaji', wage_period AS 'Periode Gaji', is_active AS 'Aktif' FROM employees").style.format({'Jumlah Gaji': 'Rp {:,.2f}'}), use_container_width=True, column_config={
                "Nama": st.column_config.Column(width="medium"),
                "Peran": st.column_config.Column(width="small"),
                "Jumlah Gaji": st.column_config.Column(width="small"),
                "Periode Gaji": st.column_config.Column(width="small"),
                "Aktif": st.column_config.Column(width="small")
            })
        
        with tabs[1]:
            st.subheader("Tambah Karyawan Baru")
            with st.form("add_employee_form"):
                name = st.text_input("Nama Karyawan").lower()
                role = st.selectbox("Peran", ["Operator", "Admin"])
                wage_period = st.selectbox("Periode Gaji", ["Per Jam", "Per Hari", "Per Bulan"])
                wage_amount = st.number_input("Jumlah Gaji", value=0.0, format="%.2f", min_value=0.0)
                password = st.text_input("Password", type="password")
                is_active = st.checkbox("Aktif", value=True)
                if st.form_submit_button("Tambah"):
                    if name and password:
                        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
                        run_query("INSERT INTO employees (name, wage_amount, wage_period, password, role, is_active) VALUES (?, ?, ?, ?, ?, ?)", (name, wage_amount, wage_period, hashed_pw, role, is_active)); st.success("Ditambahkan!"); st.rerun()
                    else: 
                        st.error("Nama dan Password tidak boleh kosong.")
        
        with tabs[2]:
            st.subheader("Edit Karyawan")
            search_term = st.text_input("Ketik nama karyawan untuk diedit", key="edit_emp_search", placeholder="Cari karyawan...")
            if search_term:
                emp_data = run_query("SELECT * FROM employees WHERE name LIKE ?", (f'%{search_term}%',), fetch='one')
                if emp_data:
                    with st.form("edit_employee_form"):
                        st.info(f"Mengedit data untuk: **{emp_data[1]}**")
                        name = st.text_input("Nama", value=emp_data[1]).lower()
                        role = st.selectbox("Peran", ["Operator", "Admin"], index=["Operator", "Admin"].index(emp_data[5]))
                        wage_period = st.selectbox("Periode Gaji", ["Per Jam", "Per Hari", "Per Bulan"], index=["Per Jam", "Per Hari", "Per Bulan"].index(emp_data[3]))
                        wage_amount = st.number_input("Jumlah Gaji", value=float(emp_data[2]), format="%.2f", min_value=0.0)
                        password = st.text_input("Password Baru (kosongkan jika tidak diubah)", type="password")
                        is_active = st.checkbox("Aktif", value=bool(emp_data[6]))
                        if st.form_submit_button("Simpan"):
                            if password:
                                hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
                                run_query("UPDATE employees SET name=?, wage_amount=?, wage_period=?, role=?, is_active=?, password=? WHERE id=?", (name, wage_amount, wage_period, role, is_active, hashed_pw, emp_data[0]))
                            else:
                                run_query("UPDATE employees SET name=?, wage_amount=?, wage_period=?, role=?, is_active=? WHERE id=?", (name, wage_amount, wage_period, role, is_active, emp_data[0]))
                            st.success("Diperbarui!"); st.rerun()
                else:
                    st.warning("Karyawan tidak ditemukan.")
            else:
                st.info("Ketik nama karyawan di atas untuk mulai mengedit.")
        
        with tabs[3]:
            st.subheader("Absensi Karyawan Hari Ini")
            employees_df = get_df("SELECT id, name FROM employees WHERE is_active = 1")
            if not employees_df.empty:
                employee_id = st.selectbox("Pilih Karyawan", employees_df['id'], format_func=lambda x: employees_df[employees_df['id'] == x]['name'].iloc[0], key="attendance_emp_select")
                today_str = date.today().isoformat()
                attendance = run_query("SELECT * FROM attendance WHERE employee_id=? AND date(check_in)=?", (employee_id, today_str), fetch='one')
                
                if not attendance:
                    if st.button("Check In", use_container_width=True):
                        run_query("INSERT INTO attendance (employee_id, check_in) VALUES (?, ?)", (employee_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); st.success("Check in berhasil!"); st.rerun()
                elif not attendance[3]: # Check-out is null
                    st.info(f"Sudah check in pada: **{attendance[2]}**")
                    if st.button("Check Out", use_container_width=True):
                        run_query("UPDATE attendance SET check_out=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attendance[0])); st.success("Check out berhasil!"); st.rerun()
                else: 
                    st.success(f"Sudah check in ({attendance[2]}) dan check out ({attendance[3]}) hari ini.")
            else: 
                st.info("Tidak ada karyawan aktif untuk absensi.")

    # --- Halaman Riwayat Absensi ---
    elif menu == "🕒 Riwayat Absensi":
        st.header("🕒 Riwayat Absensi Karyawan")
        tabs = st.tabs(["Daftar Absensi", "✏️ Edit Absensi"])
        
        with tabs[0]:
            st.subheader("Daftar Riwayat Absensi")
            # Memperbaiki lebar kolom agar tulisan tidak terpotong
            df = get_df("SELECT a.id, e.name AS 'Nama Karyawan', a.check_in AS 'Waktu Check In', a.check_out AS 'Waktu Check Out' FROM attendance a JOIN employees e ON a.employee_id = e.id ORDER BY a.check_in DESC")
            st.dataframe(df, use_container_width=True, column_config={
                "ID": st.column_config.Column(width="small"),
                "Nama Karyawan": st.column_config.Column(width="medium"),
                "Waktu Check In": st.column_config.Column(width="medium"),
                "Waktu Check Out": st.column_config.Column(width="medium")
            })
        
        with tabs[1]:
            st.subheader("Edit Data Absensi")
            attendance_df = get_df("SELECT a.id, e.name, a.check_in FROM attendance a JOIN employees e ON a.employee_id = e.id ORDER BY a.check_in DESC")
            if not attendance_df.empty:
                attendance_options = {f"ID: {row['id']} - {row['name']} ({row['check_in']})": row['id'] for _, row in attendance_df.iterrows()}
                selected_att_str = st.selectbox("Pilih absensi untuk diedit", list(attendance_options.keys()), key="edit_att_select")
                if selected_att_str:
                    att_id = attendance_options[selected_att_str]
                    att_data = run_query("SELECT * FROM attendance WHERE id=?", (att_id,), fetch='one')
                    if att_data:
                        with st.form("attendance_form"):
                            check_in_val = datetime.strptime(att_data[2], '%Y-%m-%d %H:%M:%S')
                            check_out_val = datetime.strptime(att_data[3], '%Y-%m-%d %H:%M:%S') if att_data[3] else None
                            
                            st.markdown("Format Waktu: `YYYY-MM-DD HH:MM:SS`")
                            new_check_in = st.text_input("Waktu Check In", value=check_in_val.strftime('%Y-%m-%d %H:%M:%S'))
                            new_check_out = st.text_input("Waktu Check Out", value=check_out_val.strftime('%Y-%m-%d %H:%M:%S') if check_out_val else "")
                            
                            if st.form_submit_button("Simpan Perubahan"):
                                try:
                                    # Validate date format
                                    datetime.strptime(new_check_in, '%Y-%m-%d %H:%M:%S')
                                    if new_check_out: datetime.strptime(new_check_out, '%Y-%m-%d %H:%M:%S')
                                    
                                    run_query("UPDATE attendance SET check_in=?, check_out=? WHERE id=?", (new_check_in, new_check_out if new_check_out else None, att_id)); st.success("Data diperbarui!"); st.rerun()
                                except ValueError:
                                    st.error("Format tanggal/waktu tidak valid. Gunakan format YYYY-MM-DD HH:MM:SS.")
            else: 
                st.info("Tidak ada data absensi untuk dikelola.")

    # --- NEW: Halaman Akuntansi ---
    elif menu == "📚 Akuntansi":
        st.header("📚 Modul Akuntansi")
        tabs = st.tabs(["Daftar Akun", "Jurnal Umum", "Laporan Keuangan"])

        with tabs[0]:
            st.subheader("Daftar Akun (Chart of Accounts)")
            # Memperbaiki lebar kolom agar tulisan tidak terpotong
            st.dataframe(get_df("SELECT id, account_code AS 'Kode Akun', account_name AS 'Nama Akun', account_type AS 'Tipe Akun', normal_balance AS 'Saldo Normal' FROM accounts"), use_container_width=True, column_config={
                "Kode Akun": st.column_config.Column(width="small"),
                "Nama Akun": st.column_config.Column(width="medium"),
                "Tipe Akun": st.column_config.Column(width="small"),
                "Saldo Normal": st.column_config.Column(width="small")
            })
            
            st.markdown("---")
            st.subheader("Tambah/Edit Akun")
            accounts_df = get_df("SELECT id, account_code, account_name FROM accounts")
            account_options = {f"{row['account_code']} - {row['account_name']}": row['id'] for _, row in accounts_df.iterrows()}
            
            edit_mode = st.checkbox("Mode Edit Akun yang Ada?", key="edit_account_mode_checkbox")
            selected_account_id = None
            
            if edit_mode and not accounts_df.empty:
                selected_account_str = st.selectbox("Pilih Akun untuk Diedit", list(account_options.keys()), key="select_account_to_edit")
                selected_account_id = account_options[selected_account_str]
                account_data = run_query("SELECT * FROM accounts WHERE id = ?", (selected_account_id,), fetch='one')
                
                with st.form("edit_account_form"):
                    st.info(f"Mengedit akun: **{account_data[2]}**")
                    new_account_code = st.number_input("Kode Akun", value=account_data[1], format="%d", key="edit_acc_code")
                    new_account_name = st.text_input("Nama Akun", value=account_data[2], key="edit_acc_name")
                    new_account_type = st.selectbox("Tipe Akun", ["Aset", "Liabilitas", "Ekuitas", "Pendapatan", "Beban"], index=["Aset", "Liabilitas", "Ekuitas", "Pendapatan", "Beban"].index(account_data[3]), key="edit_acc_type")
                    new_normal_balance = st.selectbox("Saldo Normal", ["Debit", "Kredit"], index=["Debit", "Kredit"].index(account_data[4]), key="edit_normal_balance")
                    if st.form_submit_button("Simpan Perubahan Akun"):
                        if new_account_name and new_account_code > 0:
                            run_query("UPDATE accounts SET account_code=?, account_name=?, account_type=?, normal_balance=? WHERE id=?", (new_account_code, new_account_name, new_account_type, new_normal_balance, selected_account_id))
                            st.success("Akun berhasil diperbarui!"); st.rerun()
                        else:
                            st.error("Kode dan Nama Akun tidak boleh kosong atau nol.")
            else:
                with st.form("add_account_form"):
                    new_account_code = st.number_input("Kode Akun Baru", value=0, format="%d", key="add_acc_code")
                    new_account_name = st.text_input("Nama Akun Baru", placeholder="Contoh: Beban Gaji Karyawan", key="add_acc_name")
                    new_account_type = st.selectbox("Tipe Akun Baru", ["Aset", "Liabilitas", "Ekuitas", "Pendapatan", "Beban"], key="add_acc_type")
                    new_normal_balance = st.selectbox("Saldo Normal Baru", ["Debit", "Kredit"], key="add_normal_balance")
                    if st.form_submit_button("Tambah Akun Baru"):
                        if new_account_name and new_account_code > 0:
                            run_query("INSERT INTO accounts (account_code, account_name, account_type, normal_balance) VALUES (?, ?, ?, ?)", (new_account_code, new_account_name, new_account_type, new_normal_balance))
                            st.success("Akun baru berhasil ditambahkan!"); st.rerun()
                        else:
                            st.error("Kode dan Nama Akun tidak boleh kosong atau nol.")

        with tabs[1]:
            st.subheader("Jurnal Umum")
            
            col_journal_filter1, col_journal_filter2 = st.columns(2)
            with col_journal_filter1:
                journal_start_date = st.date_input("Dari Tanggal Jurnal", date.today().replace(day=1), key="journal_start_date")
            with col_journal_filter2:
                journal_end_date = st.date_input("Sampai Tanggal Jurnal", date.today(), key="journal_end_date")

            journal_query = f"""
                SELECT 
                    je.entry_date AS 'Tanggal',
                    je.description AS 'Deskripsi',
                    a.account_code || ' - ' || a.account_name AS 'Akun',
                    ji.debit AS 'Debit',
                    ji.kredit AS 'Kredit'
                FROM journal_entries je
                JOIN journal_items ji ON je.id = ji.journal_entry_id
                JOIN accounts a ON ji.account_id = a.id
                WHERE je.entry_date BETWEEN ? AND ?
                ORDER BY je.entry_date DESC, je.id DESC
            """
            journal_params = [journal_start_date.isoformat(), journal_end_date.isoformat()]
            journal_df = get_df(journal_query, journal_params)
            
            # Memperbaiki lebar kolom agar tulisan tidak terpotong
            st.dataframe(journal_df.style.format({'Debit': 'Rp {:,.2f}', 'Kredit': 'Rp {:,.2f}'}), use_container_width=True, column_config={
                "Tanggal": st.column_config.Column(width="small"),
                "Deskripsi": st.column_config.Column(width="medium"),
                "Akun": st.column_config.Column(width="medium"),
                "Debit": st.column_config.Column(width="small"),
                "Kredit": st.column_config.Column(width="small")
            })

            st.markdown("---")
            st.subheader("Buat Jurnal Manual")
            st.info("Pastikan total Debit dan Kredit seimbang sebelum posting jurnal.")
            with st.form("manual_journal_form"):
                journal_date = st.date_input("Tanggal Jurnal", date.today(), key="manual_journal_date")
                journal_description = st.text_input("Deskripsi Jurnal", placeholder="Contoh: Penyesuaian Akhir Bulan", key="manual_journal_desc")
                
                st.markdown("#### Entri Jurnal:")
                num_entries = st.number_input("Jumlah Baris Entri", min_value=2, value=2, step=1, key="num_journal_entries")
                
                manual_entries = []
                accounts_for_journal = get_df("SELECT id, account_code, account_name FROM accounts")
                account_journal_options = {f"{row['account_code']} - {row['account_name']}": row['id'] for _, row in accounts_for_journal.iterrows()}

                if not account_journal_options:
                    st.warning("Tidak ada akun yang tersedia untuk jurnal. Harap tambahkan di menu Akuntansi > Daftar Akun.")
                else:
                    for i in range(num_entries):
                        st.markdown(f"**Baris {i+1}**")
                        col_acc, col_deb, col_kre = st.columns(3)
                        with col_acc:
                            selected_acc_name = st.selectbox(f"Akun {i+1}", list(account_journal_options.keys()), key=f"acc_select_{i}")
                            account_id = account_journal_options[selected_acc_name]
                        with col_deb:
                            debit_val = st.number_input(f"Debit {i+1}", value=0.0, format="%.2f", key=f"debit_{i}")
                        with col_kre:
                            kredit_val = st.number_input(f"Kredit {i+1}", value=0.0, format="%.2f", key=f"kredit_{i}")
                        manual_entries.append({'account_id': account_id, 'debit': debit_val, 'kredit': kredit_val})
                    
                    if st.form_submit_button("Posting Jurnal"):
                        if journal_description:
                            success, message = create_journal_entry(journal_date.isoformat(), journal_description, manual_entries)
                            if success:
                                st.success(message); st.rerun()
                            else:
                                st.error(message)
                        else:
                            st.error("Deskripsi jurnal tidak boleh kosong.")

        with tabs[2]:
            st.subheader("Laporan Keuangan")
            report_type = st.selectbox("Pilih Laporan", ["Laba Rugi", "Neraca"], key="financial_report_type")
            report_date = st.date_input("Tanggal Laporan", date.today(), key="financial_report_date")

            if report_type == "Laba Rugi":
                st.markdown(f"### Laporan Laba Rugi per {report_date.strftime('%d %B %Y')}")
                
                # Pendapatan
                st.markdown("#### Pendapatan")
                pendapatan_sales_id = run_query("SELECT id FROM accounts WHERE account_name = 'Pendapatan Penjualan'", fetch='one')
                pendapatan_lain_id = run_query("SELECT id FROM accounts WHERE account_name = 'Pendapatan Lain-lain'", fetch='one')
                
                total_pendapatan_sales = get_account_balance(pendapatan_sales_id[0], report_date.isoformat()) if pendapatan_sales_id else 0
                total_pendapatan_lain = get_account_balance(pendapatan_lain_id[0], report_date.isoformat()) if pendapatan_lain_id else 0
                
                st.markdown(f"- Pendapatan Penjualan: **Rp {total_pendapatan_sales:,.2f}**")
                st.markdown(f"- Pendapatan Lain-lain: **Rp {total_pendapatan_lain:,.2f}**")
                total_pendapatan = total_pendapatan_sales + total_pendapatan_lain
                st.markdown(f"**Total Pendapatan: Rp {total_pendapatan:,.2f}**")

                # Beban
                st.markdown("#### Beban")
                hpp_id = run_query("SELECT id FROM accounts WHERE account_name = 'Harga Pokok Penjualan'", fetch='one')
                beban_gaji_id = run_query("SELECT id FROM accounts WHERE account_name = 'Beban Gaji'", fetch='one')
                beban_listrik_air_id = run_query("SELECT id FROM accounts WHERE account_name = 'Beban Listrik & Air'", fetch='one')
                beban_sewa_id = run_query("SELECT id FROM accounts WHERE account_name = 'Beban Sewa'", fetch='one')
                beban_lain_id = run_query("SELECT id FROM accounts WHERE account_name = 'Beban Lain-lain'", fetch='one')

                total_hpp = get_account_balance(hpp_id[0], report_date.isoformat()) if hpp_id else 0
                total_beban_gaji = get_account_balance(beban_gaji_id[0], report_date.isoformat()) if beban_gaji_id else 0
                total_beban_listrik_air = get_account_balance(beban_listrik_air_id[0], report_date.isoformat()) if beban_listrik_air_id else 0
                total_beban_sewa = get_account_balance(beban_sewa_id[0], report_date.isoformat()) if beban_sewa_id else 0
                total_beban_lain = get_account_balance(beban_lain_id[0], report_date.isoformat()) if beban_lain_id else 0

                st.markdown(f"- Harga Pokok Penjualan: **Rp {total_hpp:,.2f}**")
                st.markdown(f"- Beban Gaji: **Rp {total_beban_gaji:,.2f}**")
                st.markdown(f"- Beban Listrik & Air: **Rp {total_beban_listrik_air:,.2f}**")
                st.markdown(f"- Beban Sewa: **Rp {total_beban_sewa:,.2f}**")
                st.markdown(f"- Beban Lain-lain: **Rp {total_beban_lain:,.2f}**")
                total_beban = total_hpp + total_beban_gaji + total_beban_listrik_air + total_beban_sewa + total_beban_lain
                st.markdown(f"**Total Beban: Rp {total_beban:,.2f}**")

                laba_bersih = total_pendapatan - total_beban
                st.markdown(f"### **Laba Bersih: Rp {laba_bersih:,.2f}**")

            elif report_type == "Neraca":
                st.markdown(f"### Laporan Neraca per {report_date.strftime('%d %B %Y')}")
                
                # Aset
                st.markdown("#### Aset")
                asset_accounts = get_df("SELECT id, account_name FROM accounts WHERE account_type = 'Aset'")
                total_aset = 0
                for _, acc in asset_accounts.iterrows():
                    balance = get_account_balance(acc['id'], report_date.isoformat())
                    st.markdown(f"- {acc['account_name']}: **Rp {balance:,.2f}**")
                    total_aset += balance
                st.markdown(f"**Total Aset: Rp {total_aset:,.2f}**")

                # Liabilitas
                st.markdown("#### Liabilitas")
                liability_accounts = get_df("SELECT id, account_name FROM accounts WHERE account_type = 'Liabilitas'")
                total_liabilitas = 0
                for _, acc in liability_accounts.iterrows():
                    balance = get_account_balance(acc['id'], report_date.isoformat())
                    st.markdown(f"- {acc['account_name']}: **Rp {balance:,.2f}**")
                    total_liabilitas += balance
                st.markdown(f"**Total Liabilitas: Rp {total_liabilitas:,.2f}**")

                # Ekuitas
                st.markdown("#### Ekuitas")
                equity_accounts = get_df("SELECT id, account_name FROM accounts WHERE account_type = 'Ekuitas'")
                total_ekuitas = 0
                for _, acc in equity_accounts.iterrows():
                    balance = get_account_balance(acc['id'], report_date.isoformat())
                    st.markdown(f"- {acc['account_name']}: **Rp {balance:,.2f}**")
                    total_ekuitas += balance
                
                # Laba Bersih dari Laba Rugi (untuk periode berjalan)
                # Ini adalah penyederhanaan, idealnya laba bersih periode berjalan ditambahkan ke ekuitas
                # Untuk tujuan demo, kita ambil laba bersih dari awal tahun sampai tanggal laporan
                pendapatan_sales_id = run_query("SELECT id FROM accounts WHERE account_name = 'Pendapatan Penjualan'", fetch='one')
                pendapatan_lain_id = run_query("SELECT id FROM accounts WHERE account_name = 'Pendapatan Lain-lain'", fetch='one')
                hpp_id = run_query("SELECT id FROM accounts WHERE account_name = 'Harga Pokok Penjualan'", fetch='one')
                beban_gaji_id = run_query("SELECT id FROM accounts WHERE account_name = 'Beban Gaji'", fetch='one')
                beban_listrik_air_id = run_query("SELECT id FROM accounts WHERE account_name = 'Beban Listrik & Air'", fetch='one')
                beban_sewa_id = run_query("SELECT id FROM accounts WHERE account_name = 'Beban Sewa'", fetch='one')
                beban_lain_id = run_query("SELECT id FROM accounts WHERE account_name = 'Beban Lain-lain'", fetch='one')

                laba_bersih_periode = (get_account_balance(pendapatan_sales_id[0], report_date.isoformat()) if pendapatan_sales_id else 0) + \
                                     (get_account_balance(pendapatan_lain_id[0], report_date.isoformat()) if pendapatan_lain_id else 0) - \
                                     (get_account_balance(hpp_id[0], report_date.isoformat()) if hpp_id else 0) - \
                                     (get_account_balance(beban_gaji_id[0], report_date.isoformat()) if beban_gaji_id else 0) - \
                                     (get_account_balance(beban_listrik_air_id[0], report_date.isoformat()) if beban_listrik_air_id else 0) - \
                                     (get_account_balance(beban_sewa_id[0], report_date.isoformat()) if beban_sewa_id else 0) - \
                                     (get_account_balance(beban_lain_id[0], report_date.isoformat()) if beban_lain_id else 0)
                
                st.markdown(f"- Laba Bersih Periode: **Rp {laba_bersih_periode:,.2f}**")
                total_ekuitas += laba_bersih_periode # Tambahkan laba bersih ke ekuitas untuk neraca

                st.markdown(f"**Total Ekuitas: Rp {total_ekuitas:,.2f}**")

                st.markdown("---")
                st.markdown(f"**Total Liabilitas + Ekuitas: Rp {total_liabilitas + total_ekuitas:,.2f}**")
                if round(total_aset, 2) == round(total_liabilitas + total_ekuitas, 2):
                    st.success("Neraca Seimbang!")
                else:
                    st.error(f"Neraca Tidak Seimbang! Selisih: Rp {total_aset - (total_liabilitas + total_ekuitas):,.2f}")

    # --- NEW: Halaman Pelanggan & Pemasok ---
    elif menu == "👤 Pelanggan & Pemasok":
        st.header("👤 Manajemen Pelanggan & Pemasok")
        tabs = st.tabs(["Pelanggan", "Pemasok"])

        with tabs[0]:
            st.subheader("Daftar Pelanggan")
            # Memperbaiki lebar kolom agar tulisan tidak terpotong
            st.dataframe(get_df("SELECT id, name AS 'Nama', address AS 'Alamat', phone AS 'Telepon', email AS 'Email' FROM customers"), use_container_width=True, column_config={
                "Nama": st.column_config.Column(width="medium"),
                "Alamat": st.column_config.Column(width="medium"),
                "Telepon": st.column_config.Column(width="small"),
                "Email": st.column_config.Column(width="medium")
            })
            st.markdown("---")
            st.subheader("Tambah/Edit Pelanggan")
            customers_df = get_df("SELECT id, name FROM customers")
            customer_options = {row['name']: row['id'] for _, row in customers_df.iterrows()}
            
            edit_cust_mode = st.checkbox("Mode Edit Pelanggan yang Ada?", key="edit_cust_mode_checkbox")
            selected_cust_id = None
            if edit_cust_mode and not customers_df.empty:
                selected_cust_name = st.selectbox("Pilih Pelanggan untuk Diedit", list(customer_options.keys()), key="select_cust_to_edit")
                selected_cust_id = customer_options[selected_cust_name]
                cust_data = run_query("SELECT * FROM customers WHERE id = ?", (selected_cust_id,), fetch='one')
                
                with st.form("edit_customer_form"):
                    st.info(f"Mengedit pelanggan: **{cust_data[1]}**")
                    new_cust_name = st.text_input("Nama Pelanggan", value=cust_data[1], key="edit_cust_name")
                    new_cust_address = st.text_area("Alamat", value=cust_data[2], key="edit_cust_address")
                    new_cust_phone = st.text_input("Telepon", value=cust_data[3], key="edit_cust_phone")
                    new_cust_email = st.text_input("Email", value=cust_data[4], key="edit_cust_email")
                    if st.form_submit_button("Simpan Perubahan Pelanggan"):
                        if new_cust_name:
                            run_query("UPDATE customers SET name=?, address=?, phone=?, email=? WHERE id=?", (new_cust_name, new_cust_address, new_cust_phone, new_cust_email, selected_cust_id))
                            st.success("Pelanggan berhasil diperbarui!"); st.rerun()
                        else:
                            st.error("Nama Pelanggan tidak boleh kosong.")
            else:
                with st.form("add_customer_form"):
                    new_cust_name = st.text_input("Nama Pelanggan Baru", placeholder="Contoh: Budi Santoso", key="add_cust_name")
                    new_cust_address = st.text_area("Alamat", key="add_cust_address")
                    new_cust_phone = st.text_input("Telepon", placeholder="Contoh: 081234567890", key="add_cust_phone")
                    new_cust_email = st.text_input("Email", placeholder="Contoh: budi@example.com", key="add_cust_email")
                    if st.form_submit_button("Tambah Pelanggan Baru"):
                        if new_cust_name:
                            run_query("INSERT INTO customers (name, address, phone, email) VALUES (?, ?, ?, ?)", (new_cust_name, new_cust_address, new_cust_phone, new_cust_email))
                            st.success("Pelanggan baru berhasil ditambahkan!"); st.rerun()
                        else:
                            st.error("Nama Pelanggan tidak boleh kosong.")

        with tabs[1]:
            st.subheader("Daftar Pemasok")
            # Memperbaiki lebar kolom agar tulisan tidak terpotong
            st.dataframe(get_df("SELECT id, name AS 'Nama', address AS 'Alamat', phone AS 'Telepon', email AS 'Email' FROM suppliers"), use_container_width=True, column_config={
                "Nama": st.column_config.Column(width="medium"),
                "Alamat": st.column_config.Column(width="medium"),
                "Telepon": st.column_config.Column(width="small"),
                "Email": st.column_config.Column(width="medium")
            })
            st.markdown("---")
            st.subheader("Tambah/Edit Pemasok")
            suppliers_df = get_df("SELECT id, name FROM suppliers")
            supplier_options = {row['name']: row['id'] for _, row in suppliers_df.iterrows()}
            
            edit_supp_mode = st.checkbox("Mode Edit Pemasok yang Ada?", key="edit_supp_mode_checkbox")
            selected_supp_id = None
            if edit_supp_mode and not suppliers_df.empty:
                selected_supp_name = st.selectbox("Pilih Pemasok untuk Diedit", list(supplier_options.keys()), key="select_supp_to_edit")
                selected_supp_id = supplier_options[selected_supp_name]
                supp_data = run_query("SELECT * FROM suppliers WHERE id = ?", (selected_supp_id,), fetch='one')
                
                with st.form("edit_supplier_form"):
                    st.info(f"Mengedit pemasok: **{supp_data[1]}**")
                    new_supp_name = st.text_input("Nama Pemasok", value=supp_data[1], key="edit_supp_name")
                    new_supp_address = st.text_area("Alamat", value=supp_data[2], key="edit_supp_address")
                    new_supp_phone = st.text_input("Telepon", value=supp_data[3], key="edit_supp_phone")
                    new_supp_email = st.text_input("Email", value=supp_data[4], key="edit_supp_email")
                    if st.form_submit_button("Simpan Perubahan Pemasok"):
                        if new_supp_name:
                            run_query("UPDATE suppliers SET name=?, address=?, phone=?, email=? WHERE id=?", (new_supp_name, new_supp_address, new_supp_phone, new_supp_email, selected_supp_id))
                            st.success("Pemasok berhasil diperbarui!"); st.rerun()
                        else:
                            st.error("Nama Pemasok tidak boleh kosong.")
            else:
                with st.form("add_supplier_form"):
                    new_supp_name = st.text_input("Nama Pemasok Baru", placeholder="Contoh: PT. Kopi Jaya", key="add_supp_name")
                    new_supp_address = st.text_area("Alamat", key="add_supp_address")
                    new_supp_phone = st.text_input("Telepon", placeholder="Contoh: 021-12345678", key="add_supp_phone")
                    new_supp_email = st.text_input("Email", placeholder="Contoh: info@kopijaya.com", key="add_supp_email")
                    if st.form_submit_button("Tambah Pemasok Baru"):
                        if new_supp_name:
                            run_query("INSERT INTO suppliers (name, address, phone, email) VALUES (?, ?, ?, ?)", (new_supp_name, new_supp_address, new_supp_phone, new_supp_email))
                            st.success("Pemasok baru berhasil ditambahkan!"); st.rerun()
                        else:
                            st.error("Nama Pemasok tidak boleh kosong.")

    # --- NEW: Halaman Aktiva Tetap ---
    elif menu == "🏢 Aktiva Tetap":
        st.header("🏢 Manajemen Aktiva Tetap")
        tabs = st.tabs(["Daftar Aktiva", "➕ Tambah Aktiva", "✏️ Edit Aktiva"])

        with tabs[0]:
            st.subheader("Daftar Aktiva Tetap Saat Ini")
            # Memperbaiki lebar kolom agar tulisan tidak terpotong
            st.dataframe(get_df("SELECT id, asset_name AS 'Nama Aset', acquisition_date AS 'Tgl Perolehan', acquisition_cost AS 'Biaya Perolehan', useful_life_years AS 'Umur Ekonomis (Tahun)', salvage_value AS 'Nilai Residu', depreciation_method AS 'Metode Depresiasi', current_book_value AS 'Nilai Buku Saat Ini' FROM fixed_assets").style.format({'Biaya Perolehan': 'Rp {:,.2f}', 'Nilai Residu': 'Rp {:,.2f}', 'Nilai Buku Saat Ini': 'Rp {:,.2f}'}), use_container_width=True, column_config={
                "Nama Aset": st.column_config.Column(width="medium"),
                "Tgl Perolehan": st.column_config.Column(width="small"),
                "Biaya Perolehan": st.column_config.Column(width="small"),
                "Umur Ekonomis (Tahun)": st.column_config.Column(width="small"),
                "Nilai Residu": st.column_config.Column(width="small"),
                "Metode Depresiasi": st.column_config.Column(width="small"),
                "Nilai Buku Saat Ini": st.column_config.Column(width="small")
            })
        
        with tabs[1]:
            st.subheader("Tambah Aktiva Tetap Baru")
            with st.form("add_asset_form"):
                asset_name = st.text_input("Nama Aset", placeholder="Contoh: Mesin Espresso", key="add_asset_name")
                acquisition_date = st.date_input("Tanggal Perolehan", date.today(), key="add_acquisition_date")
                acquisition_cost = st.number_input("Biaya Perolehan (Rp)", value=0.01, format="%.2f", min_value=0.01, key="add_acquisition_cost")
                useful_life_years = st.number_input("Umur Ekonomis (Tahun)", min_value=1, value=5, key="add_useful_life")
                salvage_value = st.number_input("Nilai Residu (Rp)", value=0.0, format="%.2f", min_value=0.0, key="add_salvage_value")
                depreciation_method = st.selectbox("Metode Depresiasi", ["Straight-line"], key="add_depreciation_method") # Hanya Straight-line untuk awal
                
                if st.form_submit_button("Tambah Aktiva"):
                    if asset_name and acquisition_cost > 0:
                        run_query("INSERT INTO fixed_assets (asset_name, acquisition_date, acquisition_cost, useful_life_years, salvage_value, depreciation_method, current_book_value) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                                  (asset_name, acquisition_date.isoformat(), acquisition_cost, useful_life_years, salvage_value, depreciation_method, acquisition_cost)) # current_book_value = acquisition_cost saat awal
                        st.success(f"Aktiva '{asset_name}' berhasil ditambahkan."); st.rerun()
                    else:
                        st.error("Nama Aset dan Biaya Perolehan tidak boleh kosong atau nol.")

        with tabs[2]:
            st.subheader("Edit Aktiva Tetap")
            assets_df = get_df("SELECT id, asset_name FROM fixed_assets")
            if not assets_df.empty:
                asset_options = {row['asset_name']: row['id'] for _, row in assets_df.iterrows()}
                selected_asset_name = st.selectbox("Pilih Aktiva untuk Diedit", list(asset_options.keys()), key="select_asset_to_edit")
                selected_asset_id = asset_options[selected_asset_name]
                asset_data = run_query("SELECT * FROM fixed_assets WHERE id = ?", (selected_asset_id,), fetch='one')

                with st.form("edit_asset_form"):
                    st.info(f"Mengedit aktiva: **{asset_data[1]}**")
                    new_asset_name = st.text_input("Nama Aset", value=asset_data[1], key="edit_asset_name")
                    new_acquisition_date = st.date_input("Tanggal Perolehan", value=datetime.strptime(asset_data[2], '%Y-%m-%d').date(), key="edit_acquisition_date")
                    new_acquisition_cost = st.number_input("Biaya Perolehan (Rp)", value=float(asset_data[3]), format="%.2f", min_value=0.01, key="edit_acquisition_cost")
                    new_useful_life_years = st.number_input("Umur Ekonomis (Tahun)", min_value=1, value=asset_data[4], key="edit_useful_life")
                    new_salvage_value = st.number_input("Nilai Residu (Rp)", value=float(asset_data[5]), format="%.2f", min_value=0.0, key="edit_salvage_value")
                    new_depreciation_method = st.selectbox("Metode Depresiasi", ["Straight-line"], index=["Straight-line"].index(asset_data[6]), key="edit_depreciation_method")
                    
                    if st.form_submit_button("Simpan Perubahan Aktiva"):
                        if new_asset_name and new_acquisition_cost > 0:
                            run_query("UPDATE fixed_assets SET asset_name=?, acquisition_date=?, acquisition_cost=?, useful_life_years=?, salvage_value=?, depreciation_method=? WHERE id=?", 
                                      (new_asset_name, new_acquisition_date.isoformat(), new_acquisition_cost, new_useful_life_years, new_salvage_value, new_depreciation_method, selected_asset_id))
                            st.success(f"Aktiva '{new_asset_name}' berhasil diperbarui."); st.rerun()
                        else:
                            st.error("Nama Aset dan Biaya Perolehan tidak boleh kosong atau nol.")
            else:
                st.info("Tidak ada aktiva tetap untuk diedit.")

    # --- MENU BARU: Kelola & Hapus Data ---
    elif menu == "🗑️ Kelola & Hapus Data":
        st.header("🗑️ Kelola & Hapus Data")
        st.warning("⚠️ **PERHATIAN:** Tindakan menghapus data di halaman ini bersifat permanen dan tidak dapat dibatalkan. Lakukan dengan sangat hati-hati.")
        
        tabs = st.tabs(["Hapus Bahan", "Hapus Produk", "Hapus Pengeluaran", "Hapus Karyawan", "Hapus Absensi", "Hapus Akun", "Hapus Pelanggan", "Hapus Pemasok", "Hapus Aktiva Tetap"])

        with tabs[0]:
            st.subheader("Hapus Bahan Baku")
            all_ingredients = get_df("SELECT id, name FROM ingredients")
            if not all_ingredients.empty:
                options = all_ingredients['name'].tolist()
                ing_to_delete = st.selectbox("Pilih bahan untuk dihapus", options, key="del_ing_select_main")
                
                if st.button(f"Hapus '{ing_to_delete}'", type="primary", key="del_ing_btn"):
                    ing_id_to_delete = all_ingredients[all_ingredients['name'] == ing_to_delete]['id'].iloc[0]
                    run_query("DELETE FROM ingredients WHERE id=?", (ing_id_to_delete,))
                    st.success(f"Bahan '{ing_to_delete}' telah dihapus."); st.rerun()
            else: 
                st.info("Tidak ada bahan untuk dihapus.")

        with tabs[1]:
            st.subheader("Hapus Produk")
            products_df = get_df("SELECT id, name FROM products")
            if not products_df.empty:
                prod_to_delete = st.selectbox("Pilih produk untuk dihapus", products_df['name'].tolist(), key="del_prod_select_main")
                if st.button(f"Hapus '{prod_to_delete}'", type="primary", key="del_prod_btn"):
                    prod_id_to_delete = products_df[products_df['name'] == prod_to_delete]['id'].iloc[0]
                    run_query("DELETE FROM products WHERE id=?", (prod_id_to_delete,))
                    st.success(f"Produk '{prod_to_delete}' telah dihapus."); st.rerun()
            else: 
                st.info("Tidak ada produk untuk dihapus.")

        with tabs[2]:
            st.subheader("Hapus Pengeluaran")
            expenses_df = get_df("SELECT id, description FROM expenses")
            if not expenses_df.empty:
                exp_to_delete = st.selectbox("Pilih pengeluaran untuk dihapus", expenses_df['description'].tolist(), key="del_exp_select_main")
                if st.button(f"Hapus '{exp_to_delete}'", type="primary", key="del_exp_btn"):
                    exp_id_to_delete = expenses_df[expenses_df['description'] == exp_to_delete]['id'].iloc[0]
                    # NEW: Delete associated journal entries for expense
                    run_query("DELETE FROM journal_items WHERE journal_entry_id IN (SELECT id FROM journal_entries WHERE expense_id = ?)", (exp_id_to_delete,))
                    run_query("DELETE FROM journal_entries WHERE expense_id = ?", (exp_id_to_delete,))
                    run_query("DELETE FROM expenses WHERE id=?", (exp_id_to_delete,)); 
                    st.success(f"Pengeluaran '{exp_to_delete}' dihapus.")
                    st.rerun()
            else: 
                st.info("Tidak ada pengeluaran untuk dihapus.")

        with tabs[3]:
            st.subheader("Hapus Karyawan")
            emp_df = get_df("SELECT id, name FROM employees")
            if not emp_df.empty:
                emp_to_delete = st.selectbox("Pilih karyawan untuk dihapus", emp_df['name'].tolist(), key="del_emp_select_main")
                if st.button(f"Hapus '{emp_to_delete}'", type="primary", key="del_emp_btn"):
                    emp_id_to_delete = emp_df[emp_df['name'] == emp_to_delete]['id'].iloc[0]
                    run_query("DELETE FROM employees WHERE id=?", (emp_id_to_delete,)); 
                    st.success(f"Karyawan '{emp_to_delete}' dihapus.")
                    st.rerun()
            else: 
                st.info("Tidak ada karyawan untuk dihapus.")
        
        with tabs[4]:
            st.subheader("Hapus Data Absensi")
            attendance_df = get_df("SELECT a.id, e.name, a.check_in FROM attendance a JOIN employees e ON a.employee_id = e.id ORDER BY a.check_in DESC")
            if not attendance_df.empty:
                attendance_options = {f"ID: {row['id']} - {row['name']} ({row['check_in']})": row['id'] for _, row in attendance_df.iterrows()}
                selected_att_str = st.selectbox("Pilih absensi untuk dihapus", list(attendance_options.keys()), key="del_att_select_main")
                if st.button("Hapus Absensi Ini", type="primary", key="del_att_btn"):
                    att_id = attendance_options[selected_att_str]
                    run_query("DELETE FROM attendance WHERE id=?", (att_id,)); 
                    st.success("Data absensi dihapus.")
                    st.rerun()
            else: 
                st.info("Tidak ada data absensi untuk dihapus.")

        # NEW: Delete Account
        with tabs[5]:
            st.subheader("Hapus Akun")
            accounts_df = get_df("SELECT id, account_code, account_name FROM accounts")
            if not accounts_df.empty:
                account_options = {f"{row['account_code']} - {row['account_name']}": row['id'] for _, row in accounts_df.iterrows()}
                acc_to_delete_str = st.selectbox("Pilih akun untuk dihapus", list(account_options.keys()), key="del_acc_select_main")
                if st.button(f"Hapus Akun '{acc_to_delete_str}'", type="primary", key="del_acc_btn"):
                    acc_id_to_delete = account_options[acc_to_delete_str]
                    # Check if account is used in journal_items
                    if run_query("SELECT COUNT(*) FROM journal_items WHERE account_id = ?", (acc_id_to_delete,), fetch='one')[0] > 0:
                        st.error("Akun ini tidak bisa dihapus karena sudah digunakan dalam jurnal.")
                    else:
                        run_query("DELETE FROM accounts WHERE id=?", (acc_id_to_delete,)); 
                        st.success(f"Akun '{acc_to_delete_str}' dihapus.")
                        st.rerun()
            else: 
                st.info("Tidak ada akun untuk dihapus.")

        # NEW: Delete Customer
        with tabs[6]:
            st.subheader("Hapus Pelanggan")
            customers_df = get_df("SELECT id, name FROM customers")
            if not customers_df.empty:
                customer_options = {row['name']: row['id'] for _, row in customers_df.iterrows()}
                cust_to_delete_name = st.selectbox("Pilih pelanggan untuk dihapus", list(customer_options.keys()), key="del_cust_select_main")
                if st.button(f"Hapus Pelanggan '{cust_to_delete_name}'", type="primary", key="del_cust_btn"):
                    cust_id_to_delete = customer_options[cust_to_delete_name]
                    run_query("DELETE FROM customers WHERE id=?", (cust_id_to_delete,)); 
                    st.success(f"Pelanggan '{cust_to_delete_name}' dihapus.")
                    st.rerun()
            else: 
                st.info("Tidak ada pelanggan untuk dihapus.")

        # NEW: Delete Supplier
        with tabs[7]:
            st.subheader("Hapus Pemasok")
            suppliers_df = get_df("SELECT id, name FROM suppliers")
            if not suppliers_df.empty:
                supplier_options = {row['name']: row['id'] for _, row in suppliers_df.iterrows()}
                supp_to_delete_name = st.selectbox("Pilih pemasok untuk dihapus", list(supplier_options.keys()), key="del_supp_select_main")
                if st.button(f"Hapus Pemasok '{supp_to_delete_name}'", type="primary", key="del_supp_btn"):
                    supp_id_to_delete = supplier_options[supp_to_delete_name]
                    run_query("DELETE FROM suppliers WHERE id=?", (supp_id_to_delete,)); 
                    st.success(f"Pemasok '{supp_to_delete_name}' dihapus.")
                    st.rerun()
            else: 
                st.info("Tidak ada pemasok untuk dihapus.")

        # NEW: Delete Fixed Asset
        with tabs[8]:
            st.subheader("Hapus Aktiva Tetap")
            assets_df = get_df("SELECT id, asset_name FROM fixed_assets")
            if not assets_df.empty:
                asset_options = {row['asset_name']: row['id'] for _, row in assets_df.iterrows()}
                asset_to_delete_name = st.selectbox("Pilih aktiva untuk dihapus", list(asset_options.keys()), key="del_asset_select_main")
                if st.button(f"Hapus Aktiva '{asset_to_delete_name}'", type="primary", key="del_asset_btn"):
                    asset_id_to_delete = asset_options[asset_to_delete_name]
                    run_query("DELETE FROM fixed_assets WHERE id=?", (asset_id_to_delete,))
                    st.success(f"Aktiva '{asset_to_delete_name}' dihapus.")
                    st.rerun()
            else: 
                st.info("Tidak ada aktiva tetap untuk dihapus.")


# =====================================================================
# --- TITIK MASUK APLIKASI ---
# =====================================================================
if __name__ == "__main__":
    init_db()
    check_login()
