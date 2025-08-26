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
DB = "pos_orca.db"
st.set_page_config(layout="wide", page_title="Orca Café")

# =====================================================================
# --- FUNGSI MIGRASI & INISIALISASI DATABASE ---
# =====================================================================
def update_db_schema(conn):
    """Memeriksa dan memperbarui skema database jika diperlukan."""
    c = conn.cursor()
    c.execute("PRAGMA table_info(employees)")
    emp_columns = {info[1] for info in c.fetchall()}
    if 'password' not in emp_columns: c.execute("ALTER TABLE employees ADD COLUMN password TEXT")
    if 'role' not in emp_columns: c.execute("ALTER TABLE employees ADD COLUMN role TEXT")
    if 'is_active' not in emp_columns: c.execute("ALTER TABLE employees ADD COLUMN is_active BOOLEAN DEFAULT 1")
    if 'hourly_wage' in emp_columns:
         c.execute("ALTER TABLE employees RENAME TO employees_old")
         c.execute("""CREATE TABLE employees (
             id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, wage_amount REAL,
             wage_period TEXT, password TEXT, role TEXT, is_active BOOLEAN DEFAULT 1
         )""")
         c.execute("INSERT INTO employees (id, name, wage_amount, wage_period, is_active) SELECT id, name, hourly_wage, 'Per Jam', 1 FROM employees_old")
         c.execute("DROP TABLE employees_old")
         st.toast("Skema database karyawan telah diperbarui.")

    c.execute("PRAGMA table_info(expenses)")
    exp_columns = {info[1] for info in c.fetchall()}
    if 'category' not in exp_columns:
        c.execute("ALTER TABLE expenses ADD COLUMN category TEXT DEFAULT 'Lainnya'")
        st.toast("Skema database pengeluaran telah diperbarui.")
    conn.commit()

def insert_initial_data(conn):
    """Membuat akun default jika belum ada."""
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM employees WHERE name = 'operator'")
    if c.fetchone()[0] == 0:
        st.info("Akun default tidak ditemukan, membuat akun 'operator'...")
        # Sesuai permintaan: user 'operator' dengan password 'operator' dan role 'Admin'
        hashed_pw = bcrypt.hashpw('operator'.encode('utf8'), bcrypt.gensalt())
        c.execute("INSERT INTO employees (name, password, role, wage_amount, wage_period, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                  ('operator', hashed_pw, 'Admin', 0, 'Per Jam', 1))
        conn.commit()
        st.success("Akun awal (username: operator, password: operator) berhasil dibuat.")
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
        description TEXT, amount REAL, payment_method TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, check_in TEXT, check_out TEXT
    )""")
    update_db_schema(conn)
    conn.commit()
    insert_initial_data(conn)
    insert_initial_products(conn)
    conn.close()

# =====================================================================
# --- BAGIAN LOGIN ---
# =====================================================================
def check_login():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if st.session_state.logged_in:
        st.sidebar.success(f"Welcome, {st.session_state.username} ({st.session_state.role})")
        if st.sidebar.button("Logout"):
            for key in st.session_state.keys(): del st.session_state[key]
            st.rerun()
        run_main_app()
    else:
        st.title("☕ Orca Café")
        st.subheader("Quotes Hari Ini")
        quotes = [
            "Rahajeng semeng! Secangkir kopi untuk hari yang penuh inspirasi.",
            "Hidup itu seperti kopi, pahit dan manis harus dinikmati.",
            "Di setiap biji kopi, ada cerita yang menanti.",
            "Satu tegukan kopi, sejuta semangat untuk berkarya.",
            "Kopi pagi ini sehangat mentari pagi.",
            "Jangan biarkan kopimu dingin, dan jangan biarkan semangatmu padam.",
            "Temukan ketenangan dalam secangkir kopi.",
            "Kopi adalah caraku mengatakan 'mari kita mulai petualangan hari ini'.",
            "Setiap cangkir adalah kanvas, dan barista adalah senimannya.",
            "Selamat menikmati kopi pilihan terbaik.",
            "Hari ini adalah kesempatan baru. Mulai dengan kopi terbaikmu!",
            "Kopi bukan hanya minuman, tapi ritual untuk memulai hari.",
            "Semangat kerjamu sehangat kopi di pagi hari.",
            "Biarkan aroma kopi mengisi harimu dengan inspirasi.",
            "Keberhasilan dimulai dengan secangkir kopi dan pikiran yang jernih.",
            "Ciptakan momen indahmu, ditemani kopi dari Orca Café.",
            "Setiap tetes kopi adalah energi untuk meraih mimpi.",
            "Nikmati prosesnya, seperti menikmati setiap tegukan kopi.",
            "Kopi hari ini, semangat untuk esok hari.",
            "Jadikan setiap harimu berarti, seperti rasa kopi yang mendalam."
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
                    else: st.error("Password salah!")
                else: st.error("Username tidak ditemukan atau akun tidak aktif!")

# =====================================================================
# --- APLIKASI UTAMA ---
# =====================================================================
def run_main_app():
    # --- Fungsi Helper ---
    def run_query(query, params=(), fetch=None):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(query, params)
        if fetch == 'one': result = c.fetchone()
        elif fetch == 'all': result = c.fetchall()
        else: result = None
        conn.commit()
        conn.close()
        return result

    def get_df(query, params=()):
        conn = sqlite3.connect(DB)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

    def generate_pdf_from_dataframe(df, title):
        pdf = FPDF()
        pdf.add_page(orientation='L') # Landscape
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, title, 0, 1, 'C')
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 8)

        # Headers
        cols = df.columns
        # Simple heuristic for column widths
        effective_page_width = pdf.w - 2 * pdf.l_margin
        # Adjusted column widths for better display in PDF
        col_widths = []
        for col in cols:
            if 'ID' in col or 'Qty' in col or 'Unit' in col:
                col_widths.append(effective_page_width * 0.1) # Smaller width for ID/Qty
            elif 'Tanggal' in col or 'Waktu' in col or 'Date' in col:
                col_widths.append(effective_page_width * 0.18) # Medium width for dates/times
            elif 'Deskripsi' in col or 'Nama' in col or 'Produk' in col or 'Bahan':
                col_widths.append(effective_page_width * 0.25) # Larger width for names/descriptions
            else:
                col_widths.append(effective_page_width * 0.15) # Default width

        # Normalize widths if they exceed total page width
        total_widths = sum(col_widths)
        if total_widths > effective_page_width:
            col_widths = [w * (effective_page_width / total_widths) for w in col_widths]


        for i, col in enumerate(cols):
            pdf.cell(col_widths[i], 10, str(col), 1, 0, 'C')
        pdf.ln()

        # Data
        pdf.set_font("Arial", '', 8)
        for _, row in df.iterrows():
            for i, item in enumerate(row):
                # Ensure all items are strings for pdf.cell
                pdf.cell(col_widths[i], 10, str(item), 1, 0)
            pdf.ln()
        return bytes(pdf.output())

    # --- Pengaturan Tema ---
    if 'theme' not in st.session_state:
        st.session_state.theme = "Gelap"

    if st.session_state.theme == "Gelap":
        dark_theme_css = """
            <style>
                :root {
                    --primary-color: #FFD100; --secondary-color: #FFEE32;
                    --background-color: #202020; --text-color: #D6D6D6;
                    --widget-background: #333533;
                }
                body { color: var(--text-color); background-color: var(--background-color); }
                .st-emotion-cache-16txtl3 { background-color: var(--widget-background); }
                .st-emotion-cache-1y4p8pa { background-color: var(--background-color); }
                .stButton>button {
                    background-color: var(--primary-color); color: var(--background-color);
                    border: 2px solid var(--primary-color); font-weight: bold;
                }
                .stButton>button:hover {
                    background-color: var(--secondary-color); color: var(--background-color);
                    border: 2px solid var(--secondary-color);
                }
                .stButton>button[kind="primary"] { background-color: #D32F2F; color: white; border: none; }
                .stButton>button[kind="primary"]:hover { background-color: #B71C1C; color: white; }
                h1, h2, h3 { color: var(--primary-color); }
                .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div {
                    background-color: var(--widget-background); color: var(--text-color);
                }
                .st-emotion-cache-1g6gooi {
                    background-color: var(--widget-background); border-radius: 10px; padding: 1rem;
                }
            </style>
        """
        st.markdown(dark_theme_css, unsafe_allow_html=True)
    else:
        # Light theme CSS (add if needed, otherwise Streamlit default light theme applies)
        pass


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
                    if stock < qty_per_unit * qty: insufficient_items.append(f"{ing_name} untuk {product_name}")
            if insufficient_items: raise ValueError(f"Stok tidak cukup: {', '.join(insufficient_items)}")
            total_amount = sum(products_map[name]['price'] * qty for name, qty in cart.items())
            c.execute("INSERT INTO transactions (transaction_date, total_amount, payment_method, employee_id) VALUES (?, ?, ?, ?)", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total_amount, payment_method, employee_id))
            transaction_id = c.lastrowid
            for product_name, qty in cart.items():
                product_info = products_map[product_name]
                c.execute("INSERT INTO transaction_items (transaction_id, product_id, quantity, price_per_unit) VALUES (?, ?, ?, ?)", (transaction_id, product_info['id'], qty, product_info['price']))
                c.execute("SELECT ingredient_id, qty_per_unit FROM recipes WHERE product_id=?", (product_info['id'],))
                for ing_id, qty_per_unit in c.fetchall():
                    c.execute("UPDATE ingredients SET stock = stock - ? WHERE id=?", (qty_per_unit * qty, ing_id))
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
        pdf.cell(0, 10, 'Orca Café', 0, 1, 'C'); pdf.set_font("Arial", '', 10)
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
            conn.commit()
            return True, "Transaksi berhasil dihapus dan stok dikembalikan."
        except Exception as e:
            conn.rollback()
            return False, f"Gagal menghapus transaksi: {e}"
        finally: conn.close()

    # --- Menu Sidebar (Urutan Disesuaikan) ---
    menu_options = [
        "🛒 Kasir",
        "📦 Manajemen Stok",
        "🍔 Manajemen Produk",
        "📊 Laporan",
        "📜 Riwayat Transaksi",
        "💸 Pengeluaran",
        "💰 HPP",
        "👥 Manajemen Karyawan",
    ]
    # Role 'Operator' tidak bisa akses Riwayat Absensi
    if st.session_state.role == 'Admin':
        menu_options.append("🕒 Riwayat Absensi")

    menu_options.append("⚙️ Pengaturan Aplikasi") # Selalu di akhir
    menu = st.sidebar.radio("Pilih Menu", menu_options)

    # --- Halaman Kasir (POS) ---
    if menu == "🛒 Kasir":
        st.header("🛒 Kasir (Point of Sale)")
        if 'cart' not in st.session_state: st.session_state.cart = {}
        col1, col2 = st.columns([2, 1.5])
        with col1:
            st.subheader("Katalog Produk")
            search_term = st.text_input("Cari Nama Produk...", key="product_search")
            query, params = ("SELECT name, price FROM products ORDER BY name", ())
            if search_term: query, params = "SELECT name, price FROM products WHERE name LIKE ? ORDER BY name", (f'%{search_term}%',)
            products = run_query(query, params, fetch='all')
            if products:
                cols = st.columns(4)
                for i, (name, price) in enumerate(products):
                    with cols[i % 4]:
                        # Tombol hanya menampilkan nama produk
                        if st.button(name, key=f"prod_{name}", use_container_width=True):
                            st.session_state.cart[name] = st.session_state.cart.get(name, 0) + 1
                            st.toast(f"'{name}' ditambahkan!"); st.rerun()
            else: st.info("Produk tidak ditemukan.")
        with col2:
            st.subheader("Keranjang Belanja")
            if not st.session_state.cart: st.info("Keranjang masih kosong.")
            else:
                total_price = 0
                products_df = get_df("SELECT name, price FROM products")

                for name, qty in list(st.session_state.cart.items()):
                    price = products_df[products_df['name'] == name]['price'].iloc[0]
                    subtotal = price * qty
                    total_price += subtotal

                    c1, c2, c3 = st.columns([2.5, 1.5, 1])
                    c1.write(f"{name} (x{qty})")
                    c2.write(f"Rp {subtotal:,.0f}")
                    if c3.button("Hapus", key=f"del_{name}"):
                        del st.session_state.cart[name]; st.rerun()

                st.markdown("---"); st.metric("Total Harga", f"Rp {total_price:,.0f}")
                with st.expander("Proses Pembayaran", expanded=True):
                    payment_method = st.selectbox("Metode Pembayaran", ["Cash", "Qris", "Card"])
                    cash_received = 0
                    if payment_method == 'Cash':
                        cash_received = st.number_input("Jumlah Uang Diterima (Rp)", min_value=0.0, step=1000.0, format="%.0f")
                        if cash_received >= total_price:
                            st.metric("Kembalian", f"Rp {cash_received - total_price:,.0f}")
                        elif total_price > 0: st.warning("Uang diterima kurang dari total.")

                    if st.button("✅ Proses Pembayaran", use_container_width=True, disabled=(payment_method == 'Cash' and cash_received < total_price and total_price > 0)):
                        success, message, transaction_id, change_amount = process_atomic_sale(st.session_state.cart, payment_method, st.session_state.user_id, cash_received)
                        if success:
                            st.success(f"{message} (ID: {transaction_id})")
                            if payment_method == 'Cash': st.info(f"Kembalian: Rp {change_amount:,.0f}")
                            st.session_state.last_transaction_id = transaction_id; st.session_state.cart = {}
                            st.rerun()
                        else: st.error(f"Gagal: {message}")

            if 'last_transaction_id' in st.session_state and st.session_state.last_transaction_id:
                st.markdown("---"); st.subheader("Opsi Transaksi Terakhir")
                last_id = st.session_state.last_transaction_id
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    pdf_bytes = generate_receipt_pdf(last_id)
                    st.download_button(label="📄 Cetak Struk (PDF)", data=pdf_bytes, file_name=f"struk_{last_id}.pdf", mime="application/pdf", use_container_width=True)
                with col_b2:
                    if st.button("❌ Batalkan Pesanan", use_container_width=True, type="primary"):
                        success, message = delete_transaction(last_id)
                        if success: st.success(message); del st.session_state['last_transaction_id']
                        else: st.error(message)
                        st.rerun()
                st.caption("Membatalkan pesanan akan menghapus riwayat transaksi dan mengembalikan stok bahan baku.")

    # --- Halaman Manajemen Stok ---
    elif menu == "📦 Manajemen Stok":
        st.header("📦 Manajemen Stok Bahan")
        low_stock_threshold = 10
        low_stock_df = get_df(f"SELECT name, stock, unit FROM ingredients WHERE stock <= {low_stock_threshold}")
        if not low_stock_df.empty: st.warning(f"Perhatian! Bahan berikut hampir habis (stok <= {low_stock_threshold}):"); st.dataframe(low_stock_df)

        tabs = st.tabs(["📊 Daftar Bahan", "➕ Tambah Bahan", "✏️ Edit Bahan"])
        with tabs[0]:
            st.subheader("Daftar Bahan Saat Ini")
            search_ing = st.text_input("Cari Nama Bahan...", key="ingredient_search")
            query = "SELECT id, name AS 'Nama', unit AS 'Unit', stock AS 'Stok', cost_per_unit AS 'Harga per Unit', pack_price AS 'Harga per Kemasan', pack_weight AS 'Berat per Kemasan' FROM ingredients"
            params = ()
            if search_ing: query += " WHERE name LIKE ?"; params = (f'%{search_ing}%',)
            df_ing = get_df(query, params)
            st.dataframe(df_ing.style.format({'Harga per Unit': 'Rp {:,.2f}', 'Harga per Kemasan': 'Rp {:,.2f}'}))
            
            pdf_bytes = generate_pdf_from_dataframe(df_ing, "Laporan Stok Bahan")
            st.download_button("📄 Download Laporan Stok (PDF)", pdf_bytes, "laporan_stok.pdf", "application/pdf")

        with tabs[1]:
            st.subheader("Tambah Bahan Baru")
            with st.form("add_ingredient_form"):
                name = st.text_input("Nama Bahan")
                unit = st.text_input("Satuan/Unit (e.g., gr, ml, pcs)")
                stock = st.number_input("Jumlah Stok Saat Ini", value=0.0, format="%.2f")
                st.markdown("---"); st.info("Kalkulator Harga Pokok per Satuan")
                pack_price = st.number_input("Harga Beli per Kemasan (Rp)", value=0.0, format="%.2f")
                pack_weight = st.number_input("Isi/Berat per Kemasan (sesuai satuan)", value=0.0, format="%.2f")
                cost_per_unit = (pack_price / pack_weight) if pack_weight > 0 else 0
                st.metric("Harga per Satuan (Otomatis)", f"Rp {cost_per_unit:,.2f}")
                if st.form_submit_button("Simpan Bahan"):
                    run_query("INSERT INTO ingredients (name, unit, cost_per_unit, stock, pack_weight, pack_price) VALUES (?, ?, ?, ?, ?, ?)", (name, unit, cost_per_unit, stock, pack_weight, pack_price))
                    st.success(f"Bahan '{name}' berhasil ditambahkan."); st.rerun()
        with tabs[2]:
            st.subheader("Edit Bahan")
            search_term = st.text_input("Cari Nama Bahan untuk diedit", key="edit_ing_search")
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
                        st.metric("Harga per Satuan (Otomatis)", f"Rp {cost_per_unit:,.2f}")
                        if st.form_submit_button("Simpan Perubahan"):
                            run_query("UPDATE ingredients SET name=?, unit=?, cost_per_unit=?, stock=?, pack_weight=?, pack_price=? WHERE id=?", (name, unit, cost_per_unit, stock, pack_weight, pack_price, ingredient_data[0]))
                            st.success(f"Bahan '{name}' diperbarui."); st.rerun()
                else: st.warning("Bahan tidak ditemukan.")
            else: st.info("Ketik nama bahan di atas untuk mulai mengedit.")

    # --- Halaman Manajemen Produk ---
    elif menu == "🍔 Manajemen Produk":
        st.header("🍔 Manajemen Produk & Resep")
        tabs = st.tabs(["📊 Daftar Produk", "➕ Tambah Produk", "✏️ Edit Produk", "🍲 Kelola Resep"])
        with tabs[0]:
            search_prod_list = st.text_input("Cari Nama Produk...", key="product_list_search")
            query = "SELECT id, name AS 'Nama Produk', price AS 'Harga Jual' FROM products"
            params = ()
            if search_prod_list:
                query += " WHERE name LIKE ?"
                params = (f'%{search_prod_list}%',)
            prod_df = get_df(query, params)
            st.dataframe(prod_df.style.format({'Harga Jual': 'Rp {:,.0f}'}))

            pdf_bytes = generate_pdf_from_dataframe(prod_df, "Daftar Produk")
            st.download_button("📄 Download Daftar Produk (PDF)", pdf_bytes, "daftar_produk.pdf", "application/pdf")
        with tabs[1]:
            st.subheader("Tambah Produk Baru")
            with st.form("add_product_form"):
                name = st.text_input("Nama Produk")
                price = st.number_input("Harga Jual", value=0, format="%d")
                if st.form_submit_button("Tambah Produk"):
                    run_query("INSERT INTO products (name, price) VALUES (?, ?)", (name, price)); st.success(f"Produk '{name}' ditambahkan!"); st.rerun()
        with tabs[2]:
            st.subheader("Edit Produk")
            search_term = st.text_input("Cari Nama Produk untuk diedit", key="edit_prod_search")
            if search_term:
                prod_data = run_query("SELECT * FROM products WHERE name LIKE ?", (f'%{search_term}%',), fetch='one')
                if prod_data:
                    with st.form("edit_product_form"):
                        st.info(f"Mengedit data untuk: **{prod_data[1]}**")
                        name = st.text_input("Nama Produk", value=prod_data[1])
                        price = st.number_input("Harga Jual", value=int(prod_data[2]))
                        if st.form_submit_button("Simpan Produk"):
                            run_query("UPDATE products SET name=?, price=? WHERE id=?", (name, price, prod_data[0])); st.success("Produk diperbarui!"); st.rerun()
                else: st.warning("Produk tidak ditemukan.")
            else: st.info("Ketik nama produk di atas untuk mulai mengedit.")
        with tabs[3]:
            st.subheader("Atur Resep per Produk")
            products_df = get_df("SELECT id, name FROM products ORDER BY name")
            if not products_df.empty:
                # Menggunakan format_func untuk menampilkan nama produk
                product_id = st.selectbox("Pilih Produk", products_df['id'], format_func=lambda x: products_df[products_df['id'] == x]['name'].iloc[0])
                st.write("Resep saat ini:"); st.dataframe(get_df("SELECT i.name, r.qty_per_unit, i.unit FROM recipes r JOIN ingredients i ON r.ingredient_id = i.id WHERE r.product_id=?", (product_id,)))
                with st.form("recipe_form"):
                    ingredients_df = get_df("SELECT id, name FROM ingredients ORDER BY name")
                    if not ingredients_df.empty:
                        # Menggunakan format_func untuk menampilkan nama bahan
                        ingredient_id = st.selectbox("Pilih Bahan", ingredients_df['id'], format_func=lambda x: ingredients_df[ingredients_df['id'] == x]['name'].iloc[0])
                        qty = st.number_input("Jumlah Dibutuhkan (Unit)", format="%.2f")
                        if st.form_submit_button("Simpan Resep"):
                            run_query("REPLACE INTO recipes (product_id, ingredient_id, qty_per_unit) VALUES (?, ?, ?)", (product_id, ingredient_id, qty)); st.success("Resep diperbarui."); st.rerun()
                    else: st.warning("Tidak ada bahan baku. Tambahkan di menu Manajemen Stok terlebih dahulu.")
            else: st.info("Tidak ada produk untuk dikelola resepnya.")

    # --- Halaman Laporan ---
    elif menu == "📊 Laporan":
        st.header("📊 Laporan & Analisa Bisnis")
        today = date.today()
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Tanggal Mulai", today.replace(day=1))
        end_date = col2.date_input("Tanggal Akhir", today)
        start_datetime, end_datetime = datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date, datetime.max.time())

        st.subheader("Ringkasan Kinerja Bisnis")
        trans_df = get_df("SELECT * FROM transactions WHERE transaction_date BETWEEN ? AND ?", (start_datetime.strftime("%Y-%m-%d %H:%M:%S"), end_datetime.strftime("%Y-%m-%d %H:%M:%S")))
        expenses_df = get_df("SELECT * FROM expenses WHERE date BETWEEN ? AND ?", (start_date.isoformat(), end_date.isoformat()))
        total_gaji = 0 # Dihitung di bawah

        total_pendapatan = trans_df['total_amount'].sum()
        total_modal = 0
        if not trans_df.empty:
            items_df = get_df(f"SELECT ti.quantity, r.qty_per_unit, i.cost_per_unit FROM transaction_items ti JOIN recipes r ON ti.product_id = r.product_id JOIN ingredients i ON r.ingredient_id = i.id WHERE ti.transaction_id IN ({','.join(map(str, trans_df['id']))})")
            if not items_df.empty: total_modal = (items_df['quantity'] * items_df['qty_per_unit'] * items_df['cost_per_unit']).sum()

        total_biaya_operasional = expenses_df[expenses_df['category'] == 'Operasional']['amount'].sum()
        total_pengeluaran_lainnya = expenses_df[expenses_df['category'] == 'Lainnya']['amount'].sum()
        
        laba_kotor = total_pendapatan - total_modal
        laba_bersih = laba_kotor - total_biaya_operasional - total_pengeluaran_lainnya - total_gaji # Total gaji dihitung terpisah
        margin_laba_kotor = (laba_kotor / total_pendapatan * 100) if total_pendapatan > 0 else 0
        margin_laba_bersih = (laba_bersih / total_pendapatan * 100) if total_pendapatan > 0 else 0
        
        kpi_cols = st.columns(4)
        kpi_cols[0].metric("Total Pendapatan", f"Rp {total_pendapatan:,.0f}")
        kpi_cols[1].metric("Total Modal (HPP)", f"Rp {total_modal:,.0f}")
        kpi_cols[2].metric("Biaya Operasional", f"Rp {total_biaya_operasional:,.0f}")
        kpi_cols[3].metric("Pengeluaran Lain", f"Rp {total_pengeluaran_lainnya:,.0f}")

        profit_cols = st.columns(2)
        profit_cols[0].metric("Laba Kotor", f"Rp {laba_kotor:,.0f}", delta=f"{margin_laba_kotor:.1f}% Margin")
        profit_cols[1].metric("Laba Bersih", f"Rp {laba_bersih:,.0f}", delta=f"{margin_laba_bersih:.1f}% Margin")

        if total_modal > 0 or total_biaya_operasional > 0 or total_pengeluaran_lainnya > 0:
            fig_pie = go.Figure(data=[go.Pie(labels=['Modal (HPP)', 'Biaya Operasional', 'Pengeluaran Lain'], values=[total_modal, total_biaya_operasional, total_pengeluaran_lainnya], hole=.3)])
            fig_pie.update_layout(title='Chart Komposisi Biaya')
            st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("---"); st.subheader("Analisa Penjualan")
        col_an1, col_an2 = st.columns(2)
        with col_an1:
            if not trans_df.empty:
                st.write("**Kinerja Produk**")
                laris_df = get_df(f"SELECT p.name AS 'Produk Paling Laris', SUM(ti.quantity) as 'Total Terjual' FROM transaction_items ti JOIN products p ON ti.product_id = p.id WHERE ti.transaction_id IN ({','.join(map(str, trans_df['id']))}) GROUP BY p.name ORDER BY `Total Terjual` DESC LIMIT 5")
                st.dataframe(laris_df, hide_index=True)

                hpp_df = get_df("SELECT p.id, p.name, p.price, IFNULL(SUM(r.qty_per_unit * i.cost_per_unit), 0) as hpp FROM products p LEFT JOIN recipes r ON p.id = r.product_id LEFT JOIN ingredients i ON r.ingredient_id = i.id GROUP BY p.id")
                trans_items_df = get_df(f"SELECT product_id, quantity FROM transaction_items WHERE transaction_id IN ({','.join(map(str, trans_df['id']))})")
                merged_df = pd.merge(trans_items_df, hpp_df, left_on='product_id', right_on='id')
                merged_df['profit'] = (merged_df['price'] - merged_df['hpp']) * merged_df['quantity']
                profit_summary = merged_df.groupby('name')['profit'].sum().reset_index().sort_values(by='profit', ascending=False).head(5)
                profit_summary.rename(columns={'name': 'Produk Paling Menguntungkan', 'profit': 'Total Keuntungan'}, inplace=True)
                st.dataframe(profit_summary.style.format({'Total Keuntungan': 'Rp {:,.0f}'}), hide_index=True)

                st.write("**Tren Pendapatan**")
                trans_df['transaction_date'] = pd.to_datetime(trans_df['transaction_date'])
                daily_revenue = trans_df.set_index('transaction_date').resample('D')['total_amount'].sum().reset_index()
                fig_trend = go.Figure(data=go.Scatter(x=daily_revenue['transaction_date'], y=daily_revenue['total_amount'], mode='lines+markers'))
                fig_trend.update_layout(title='Tren Pendapatan Harian', xaxis_title='Tanggal', yaxis_title='Pendapatan (Rp)')
                st.plotly_chart(fig_trend, use_container_width=True)
            else: st.info("Belum ada data penjualan pada rentang tanggal ini.")
        with col_an2:
            st.write("**Saran Manajemen**")
            saran = []
            if total_pendapatan > 0:
                if laba_bersih < 0: saran.append("Profit sedang negatif. Waktunya evaluasi HPP produk atau tekan biaya operasional. Pertimbangkan sedikit penyesuaian harga pada produk best-seller.")
                else: saran.append(f"Profitabilitas bisnis sehat! Pertimbangkan untuk berinvestasi pada peningkatan kualitas bahan baku atau program loyalitas pelanggan untuk pertumbuhan lebih lanjut.")
                if not laris_df.empty and not profit_summary.empty:
                    if laris_df['Produk Paling Laris'].iloc[0] != profit_summary['Produk Paling Menguntungkan'].iloc[0]:
                        saran.append(f"Produk '{laris_df['Produk Paling Laris'].iloc[0]}' paling laku, tapi '{profit_summary['Produk Paling Menguntungkan'].iloc[0]}' paling untung. Coba tawarkan (upselling) produk yang lebih menguntungkan kepada pelanggan.")
                    else:
                        saran.append(f"Produk terlaris dan paling menguntungkan adalah '{laris_df['Produk Paling Laris'].iloc[0]}'. Fokuskan upaya pemasaran pada produk ini dan pastikan ketersediaan stok selalu terjaga.")

            if not laris_df.empty:
                saran.append(f"Produk '{laris_df['Produk Paling Laris'].iloc[0]}' sedang populer! Pastikan stok bahan bakunya aman dan promosikan lebih gencar di media sosial. Bisa juga membuat paket bundling dengan produk pelengkap.")
            else:
                saran.append("Belum ada produk yang menonjol. Lakukan analisis pasar atau tawarkan diskon untuk beberapa produk baru untuk melihat respons pelanggan.")

            if total_biaya_operasional > total_pendapatan * 0.3:
                saran.append("Biaya operasional terlihat cukup tinggi. Coba negosiasi ulang dengan supplier atau cek kembali pos pengeluaran seperti listrik dan air. Apakah ada langganan yang tidak terpakai?")
            else:
                saran.append("Biaya operasional terkontrol dengan baik. Tetap pantau dan cari peluang efisiensi tambahan tanpa mengurangi kualitas.")

            if total_pengeluaran_lainnya > total_pendapatan * 0.1:
                saran.append("Pengeluaran lain-lain cukup signifikan. Coba identifikasi dan kategorikan pengeluaran ini lebih detail untuk menemukan area penghematan.")
            else:
                saran.append("Pengeluaran lainnya masih dalam batas wajar. Pertahankan kontrol pengeluaran yang ketat ini.")

            saran.extend([
                "Luangkan waktu rutin untuk menganalisa laporan ini agar dapat mengambil keputusan berbasis data yang lebih akurat dan tepat waktu.",
                "Gunakan media sosial untuk mempromosikan produk yang sedang laris atau produk dengan margin keuntungan tertinggi. Buat konten yang menarik dan interaktif.",
                "Dengarkan masukan pelanggan. Kotak saran atau polling di Instagram bisa memberikan ide-ide segar untuk inovasi produk atau peningkatan layanan.",
                "Lakukan training berkala untuk karyawan agar mereka lebih terampil dalam melayani pelanggan dan mengelola operasional.",
                "Pertimbangkan untuk memperluas jangkauan pasar dengan bekerja sama dengan platform pesan antar atau mengadakan event kecil di kafe.",
                "Jaga kualitas produk dan pelayanan. Pelanggan yang puas adalah promosi terbaik.",
                "Periksa kembali resep produk dan harga bahan baku secara berkala. Fluktuasi harga dapat mempengaruhi HPP dan profitabilitas.",
                "Manfaatkan data tren pendapatan untuk mengatur strategi promosi pada periode tertentu, misalnya diskon di hari-hari sepi pengunjung.",
                "Bangun komunitas pelanggan setia. Program loyalitas atau kartu member bisa meningkatkan retensi pelanggan.",
                "Selalu berinovasi dengan menu baru atau variasi dari menu yang sudah ada untuk menarik minat pelanggan."
            ])
            random.shuffle(saran)
            for i in range(min(5, len(saran))): # Display more suggestions
                st.info(saran[i])

            summary_text = f"Ringkasan Laporan Orca Café ({start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')})\n- Pendapatan: Rp {total_pendapatan:,.0f}\n- Modal (HPP): Rp {total_modal:,.0f}\n- Laba Bersih: Rp {laba_bersih:,.0f}"
            st.link_button("Kirim Ringkasan via WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(summary_text)}")

        st.markdown("---"); st.subheader("Detail Data")
        with st.expander("Detail Data Transaksi (Data Mentah)"): st.dataframe(trans_df)
        with st.expander("Detail Biaya Operasional"): st.dataframe(expenses_df[expenses_df['category'] == 'Operasional'])
        with st.expander("Detail Pengeluaran Lainnya"): st.dataframe(expenses_df[expenses_df['category'] == 'Lainnya'])

    # --- Halaman Riwayat Transaksi ---
    elif menu == "📜 Riwayat Transaksi":
        st.header("📜 Riwayat Transaksi")
        search_id = st.text_input("Cari dengan ID Transaksi...")
        query = "SELECT t.id AS 'ID Transaksi', t.transaction_date AS 'Waktu Transaksi', t.total_amount AS 'Total', t.payment_method AS 'Metode Pembayaran', e.name AS 'Kasir' FROM transactions t JOIN employees e ON t.employee_id = e.id"
        params = ()
        if search_id.isdigit(): query += " WHERE t.id = ?"; params = (int(search_id),)
        query += " ORDER BY t.id DESC"
        transactions_df = get_df(query, params)
        st.dataframe(transactions_df.style.format({'Total': 'Rp {:,.0f}'}))
        
        pdf_bytes = generate_pdf_from_dataframe(transactions_df, "Riwayat Transaksi")
        st.download_button("📄 Download Riwayat (PDF)", pdf_bytes, "riwayat_transaksi.pdf", "application/pdf")
        
        st.markdown("---"); st.subheader("Kelola Transaksi")
        if not transactions_df.empty:
            # Menggunakan ID Transaksi langsung dari DataFrame
            selected_id = st.selectbox("Pilih ID Transaksi dari tabel di atas untuk dikelola", options=transactions_df['ID Transaksi'].tolist())
            if selected_id:
                col1, col2 = st.columns(2)
                with col1:
                    items_df = get_df("SELECT p.name, ti.quantity, ti.price_per_unit FROM transaction_items ti JOIN products p ON ti.product_id = p.id WHERE ti.transaction_id = ?", (selected_id,))
                    st.write(f"**Detail Item Transaksi #{selected_id}:**"); st.dataframe(items_df)
                with col2:
                    if st.button("Hapus Transaksi Ini", type="primary", key=f"del_{selected_id}"):
                        success, message = delete_transaction(selected_id)
                        if success: st.success(message); del st.session_state['last_transaction_id']
                        else: st.error(message)
                        st.rerun()
        else: st.info("Tidak ada transaksi untuk dikelola.")
    
    # --- Halaman Pengeluaran ---
    elif menu == "💸 Pengeluaran":
        st.header("💸 Catat Pengeluaran")
        tabs = st.tabs(["📊 Daftar Pengeluaran", "➕ Tambah Pengeluaran", "✏️ Edit Pengeluaran"])
        with tabs[0]:
            df_exp = get_df("SELECT id, date, category, description, amount, payment_method FROM expenses ORDER BY date DESC")
            st.dataframe(df_exp.style.format({'amount': 'Rp {:,.2f}'}))

            pdf_bytes = generate_pdf_from_dataframe(df_exp, "Laporan Pengeluaran")
            st.download_button("📄 Download Pengeluaran (PDF)", pdf_bytes, "laporan_pengeluaran.pdf", "application/pdf")

        with tabs[1]:
            st.subheader("Tambah Pengeluaran Baru")
            with st.form("add_expense_form"):
                date_exp = st.date_input("Tanggal", date.today())
                category = st.selectbox("Kategori", ["Operasional", "Lainnya"])
                description = st.text_input("Deskripsi")
                amount = st.number_input("Jumlah", value=0.0, format="%.2f")
                payment_method = st.selectbox("Metode Pembayaran", ["Cash", "Transfer"])
                if st.form_submit_button("Tambah"):
                    run_query("INSERT INTO expenses (date, category, description, amount, payment_method) VALUES (?, ?, ?, ?, ?)", (date_exp.isoformat(), category, description, amount, payment_method)); st.success("Ditambahkan!"); st.rerun()
        with tabs[2]:
            st.subheader("Edit Pengeluaran")
            all_expenses = get_df("SELECT id, description FROM expenses")
            if not all_expenses.empty:
                # Menggunakan ID sebagai value, menampilkan deskripsi
                expense_options = {f"{row['description']} (ID: {row['id']})": row['id'] for _, row in all_expenses.iterrows()}
                selected_expense_display = st.selectbox("Pilih pengeluaran untuk diedit", list(expense_options.keys()))
                
                exp_id_to_edit = expense_options[selected_expense_display]
                exp_data = run_query("SELECT * FROM expenses WHERE id = ?", (exp_id_to_edit,), fetch='one')
                
                if exp_data:
                    with st.form("edit_expense_form"):
                        st.info(f"Mengedit data untuk: **{exp_data[3]}**")
                        date_exp = st.date_input("Tanggal", value=datetime.strptime(exp_data[1], '%Y-%m-%d').date())
                        category = st.selectbox("Kategori", ["Operasional", "Lainnya"], index=["Operasional", "Lainnya"].index(exp_data[2] or "Lainnya"))
                        description = st.text_input("Deskripsi", value=exp_data[3])
                        amount = st.number_input("Jumlah", value=float(exp_data[4]), format="%.2f")
                        payment_method = st.selectbox("Metode Pembayaran", ["Cash", "Transfer"], index=["Cash", "Transfer"].index(exp_data[5]))
                        if st.form_submit_button("Simpan Perubahan"):
                            run_query("UPDATE expenses SET date=?, category=?, description=?, amount=?, payment_method=? WHERE id=?", (date_exp.isoformat(), category, description, amount, payment_method, exp_data[0])); st.success("Diperbarui!"); st.rerun()
            else: st.info("Tidak ada data pengeluaran untuk diedit.")

    # --- Halaman HPP ---
    elif menu == "💰 HPP":
        st.header("💰 Harga Pokok Penjualan (HPP)")
        prods_df = get_df("SELECT id, name, price FROM products")
        if not prods_df.empty:
            hpp_data = []
            for _, row in prods_df.iterrows():
                hpp_result = get_df("SELECT SUM(r.qty_per_unit * i.cost_per_unit) as hpp FROM recipes r JOIN ingredients i ON r.ingredient_id = i.id WHERE r.product_id=?", (row['id'],))
                hpp = hpp_result['hpp'].iloc[0] if not hpp_result.empty and hpp_result['hpp'].iloc[0] is not None else 0
                profit = row['price'] - hpp
                hpp_data.append({"Nama Produk": row['name'], "Harga Jual": row['price'], "HPP (Modal)": hpp, "Profit Kotor": profit})
            df_hpp = pd.DataFrame(hpp_data)
            st.dataframe(df_hpp.style.format({'Harga Jual': 'Rp {:,.0f}', 'HPP (Modal)': 'Rp {:,.2f}', 'Profit Kotor': 'Rp {:,.2f}'}))

            pdf_bytes = generate_pdf_from_dataframe(df_hpp, "Laporan HPP Produk")
            st.download_button("📄 Download Laporan HPP (PDF)", pdf_bytes, "laporan_hpp.pdf", "application/pdf")

    # --- Halaman Manajemen Karyawan ---
    elif menu == "👥 Manajemen Karyawan":
        st.header("👥 Manajemen Karyawan")
        tabs = st.tabs(["📊 Daftar Karyawan", "➕ Tambah Karyawan", "✏️ Edit Karyawan", "🕒 Absensi Hari Ini"])
        with tabs[0]:
            df_emp = get_df("SELECT id, name AS 'Nama', role AS 'Role', wage_amount AS 'Jumlah Gaji', wage_period AS 'Periode Gaji', is_active AS 'Status Aktif' FROM employees")
            st.dataframe(df_emp.style.format({'Jumlah Gaji': 'Rp {:,.0f}'}))
            
            pdf_bytes = generate_pdf_from_dataframe(df_emp, "Daftar Karyawan")
            st.download_button("📄 Download Daftar Karyawan (PDF)", pdf_bytes, "daftar_karyawan.pdf", "application/pdf")
        with tabs[1]:
            st.subheader("Tambah Karyawan Baru")
            with st.form("add_employee_form"):
                name = st.text_input("Nama").lower()
                role = st.selectbox("Role", ["Operator", "Admin"])
                wage_period = st.selectbox("Periode Gaji", ["Per Jam", "Per Hari", "Per Bulan"])
                wage_amount = st.number_input("Jumlah Gaji", min_value=0)
                password = st.text_input("Password", type="password")
                is_active = st.checkbox("Aktif", value=True)
                if st.form_submit_button("Tambah"):
                    if name and password:
                        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
                        run_query("INSERT INTO employees (name, wage_amount, wage_period, password, role, is_active) VALUES (?, ?, ?, ?, ?, ?)", (name, wage_amount, wage_period, hashed_pw, role, is_active)); st.success("Ditambahkan!"); st.rerun()
                    else: st.error("Nama dan Password tidak boleh kosong.")
        with tabs[2]:
            st.subheader("Edit Karyawan")
            emp_list = get_df("SELECT name FROM employees")
            if not emp_list.empty:
                emp_name_to_edit = st.selectbox("Pilih Karyawan", emp_list['name'].tolist())
                emp_data = run_query("SELECT * FROM employees WHERE name = ?", (emp_name_to_edit,), fetch='one')
                if emp_data:
                    with st.form("edit_employee_form"):
                        st.info(f"Mengedit data untuk: **{emp_data[1]}**")
                        name = st.text_input("Nama", value=emp_data[1]).lower()
                        role = st.selectbox("Role", ["Operator", "Admin"], index=["Operator", "Admin"].index(emp_data[5]))
                        wage_period = st.selectbox("Periode Gaji", ["Per Jam", "Per Hari", "Per Bulan"], index=["Per Jam", "Per Hari", "Per Bulan"].index(emp_data[3]))
                        wage_amount = st.number_input("Jumlah Gaji", value=int(emp_data[2]))
                        password = st.text_input("Password Baru (kosongkan jika tidak diubah)", type="password")
                        is_active = st.checkbox("Aktif", value=bool(emp_data[6]))
                        if st.form_submit_button("Simpan"):
                            if password:
                                hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
                                run_query("UPDATE employees SET name=?, wage_amount=?, wage_period=?, role=?, is_active=?, password=? WHERE id=?", (name, wage_amount, wage_period, role, is_active, hashed_pw, emp_data[0]))
                            else:
                                run_query("UPDATE employees SET name=?, wage_amount=?, wage_period=?, role=?, is_active=? WHERE id=?", (name, wage_amount, wage_period, role, is_active, emp_data[0]))
                            st.success("Diperbarui!"); st.rerun()
            else: st.info("Tidak ada karyawan untuk diedit.")
        with tabs[3]:
            st.subheader("Absensi Karyawan Hari Ini")
            employees_df = get_df("SELECT id, name FROM employees WHERE is_active = 1 ORDER BY name")
            if not employees_df.empty:
                employee_id = st.selectbox("Pilih Karyawan", employees_df['id'], format_func=lambda x: employees_df[employees_df['id'] == x]['name'].iloc[0])
                today_str = date.today().isoformat()
                attendance = run_query("SELECT * FROM attendance WHERE employee_id=? AND date(check_in)=?", (employee_id, today_str), fetch='one')
                if not attendance:
                    if st.button("Check In"):
                        run_query("INSERT INTO attendance (employee_id, check_in) VALUES (?, ?)", (employee_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); st.success("Check in berhasil!"); st.rerun()
                elif not attendance[3]:
                    st.info(f"Sudah check in pada: {attendance[2]}")
                    if st.button("Check Out"):
                        run_query("UPDATE attendance SET check_out=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), attendance[0])); st.success("Check out berhasil!"); st.rerun()
                else: st.success(f"Sudah check in ({attendance[2]}) dan check out ({attendance[3]}) hari ini.")
            else: st.info("Tidak ada karyawan aktif untuk absensi.")

    # --- Halaman Riwayat Absensi ---
    elif menu == "🕒 Riwayat Absensi":
        st.header("🕒 Riwayat Absensi Karyawan")
        tabs = st.tabs(["📊 Daftar Absensi", "✏️ Edit Absensi"])
        with tabs[0]:
            st.subheader("Filter Riwayat Absensi")
            col1, col2 = st.columns(2)
            start_date_att = col1.date_input("Dari Tanggal", date.today() - timedelta(days=7), key="att_start")
            end_date_att = col2.date_input("Sampai Tanggal", date.today(), key="att_end")
            start_datetime_att = datetime.combine(start_date_att, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
            end_datetime_att = datetime.combine(end_date_att, datetime.max.time()).strftime("%Y-%m-%d %H:%M:%S")

            query = "SELECT a.id, e.name AS 'Nama', a.check_in, a.check_out FROM attendance a JOIN employees e ON a.employee_id = e.id WHERE a.check_in BETWEEN ? AND ? ORDER BY a.check_in DESC"
            df = get_df(query, (start_datetime_att, end_datetime_att))

            if not df.empty:
                df['check_in_dt'] = pd.to_datetime(df['check_in'])
                df['check_out_dt'] = pd.to_datetime(df['check_out'])
                df['Durasi Kerja (Jam)'] = (df['check_out_dt'] - df['check_in_dt']).dt.total_seconds() / 3600
                st.dataframe(df[['id', 'Nama', 'check_in', 'check_out', 'Durasi Kerja (Jam)']].style.format({'Durasi Kerja (Jam)': '{:.2f}'}))
                
                pdf_bytes = generate_pdf_from_dataframe(df, "Riwayat Absensi")
                st.download_button("📄 Download Riwayat Absensi (PDF)", pdf_bytes, "riwayat_absensi.pdf", "application/pdf")
            else: st.info("Tidak ada data absensi pada rentang tanggal yang dipilih.")
        with tabs[1]:
            st.subheader("Edit Data Absensi")
            search_date = st.date_input("Cari Absensi Berdasarkan Tanggal")
            search_date_str = search_date.strftime('%Y-%m-%d')
            attendance_df = get_df("SELECT a.id, e.name, a.check_in FROM attendance a JOIN employees e ON a.employee_id = e.id WHERE date(a.check_in) = ? ORDER BY a.check_in DESC", (search_date_str,))
            if not attendance_df.empty:
                # Menggunakan nama dan check_in untuk display, ID sebagai value
                attendance_options = {f"{row['name']} ({row['check_in']}) - ID: {row['id']}": row['id'] for _, row in attendance_df.iterrows()}
                selected_att_str = st.selectbox("Pilih absensi untuk diedit", list(attendance_options.keys()))
                if selected_att_str:
                    att_id = attendance_options[selected_att_str]
                    att_data = run_query("SELECT * FROM attendance WHERE id=?", (att_id,), fetch='one')
                    if att_data:
                        with st.form("attendance_form"):
                            check_in_val = datetime.strptime(att_data[2], '%Y-%m-%d %H:%M:%S') if att_data[2] else datetime.now()
                            check_out_val = datetime.strptime(att_data[3], '%Y-%m-%d %H:%M:%S') if att_data[3] else None
                            new_check_in = st.text_input("Waktu Check In (YYYY-MM-DD HH:MM:SS)", value=check_in_val.strftime('%Y-%m-%d %H:%M:%S'))
                            new_check_out = st.text_input("Waktu Check Out (YYYY-MM-DD HH:MM:SS)", value=check_out_val.strftime('%Y-%m-%d %H:%M:%S') if check_out_val else "")
                            if st.form_submit_button("Simpan Perubahan"):
                                run_query("UPDATE attendance SET check_in=?, check_out=? WHERE id=?", (new_check_in, new_check_out if new_check_out else None, att_id)); st.success("Data diperbarui!"); st.rerun()
            else: st.info(f"Tidak ada data absensi untuk tanggal {search_date_str}.")

    # --- MENU PENGATURAN APLIKASI ---
    elif menu == "⚙️ Pengaturan Aplikasi":
        st.header("⚙️ Pengaturan Aplikasi")
        st.warning("PERHATIAN: Tindakan menghapus data di halaman ini bersifat permanen dan tidak dapat dibatalkan.")
        
        tabs = st.tabs(["🗑️ Hapus Data Master", "🗑️ Hapus Data Transaksional", "🎨 Atur Antar-Muka"])

        with tabs[0]:
            st.subheader("Hapus Data Master (Bahan, Produk, Karyawan)")
            
            with st.expander("Hapus Bahan Baku"):
                all_ingredients = get_df("SELECT id, name FROM ingredients")
                if not all_ingredients.empty:
                    ing_to_delete = st.selectbox("Pilih bahan untuk dihapus", all_ingredients['name'].tolist(), key="del_ing_select")
                    if st.button(f"Hapus Bahan '{ing_to_delete}'", type="primary"):
                        ing_id = all_ingredients[all_ingredients['name'] == ing_to_delete]['id'].iloc[0]
                        run_query("DELETE FROM ingredients WHERE id=?", (ing_id,)); run_query("DELETE FROM recipes WHERE ingredient_id=?", (ing_id,))
                        st.success(f"Bahan '{ing_to_delete}' dan resep terkait telah dihapus."); st.rerun()
                else: st.info("Tidak ada bahan untuk dihapus.")

            with st.expander("Hapus Produk"):
                products_df = get_df("SELECT id, name FROM products")
                if not products_df.empty:
                    prod_to_delete = st.selectbox("Pilih produk untuk dihapus", products_df['name'].tolist(), key="del_prod_select")
                    if st.button(f"Hapus Produk '{prod_to_delete}'", type="primary"):
                        prod_id = products_df[products_df['name'] == prod_to_delete]['id'].iloc[0]
                        run_query("DELETE FROM products WHERE id=?", (prod_id,)); run_query("DELETE FROM recipes WHERE product_id=?", (prod_id,))
                        st.success(f"Produk '{prod_to_delete}' dan resepnya telah dihapus."); st.rerun()
                else: st.info("Tidak ada produk untuk dihapus.")

            with st.expander("Hapus Karyawan"):
                emp_df = get_df("SELECT id, name FROM employees WHERE name != 'operator'") # Mencegah admin dihapus
                if not emp_df.empty:
                    emp_to_delete = st.selectbox("Pilih karyawan untuk dihapus", emp_df['name'].tolist(), key="del_emp_select")
                    if st.button(f"Hapus Karyawan '{emp_to_delete}'", type="primary"):
                        emp_id = emp_df[emp_df['name'] == emp_to_delete]['id'].iloc[0]
                        run_query("DELETE FROM employees WHERE id=?", (emp_id,)); st.success(f"Karyawan '{emp_to_delete}' dihapus."); st.rerun()
                else: st.info("Tidak ada karyawan lain untuk dihapus.")

        with tabs[1]:
            st.subheader("Hapus Data Transaksional")

            with st.expander("Hapus Resep"):
                products_with_recipes = get_df("SELECT DISTINCT p.id, p.name FROM products p JOIN recipes r ON p.id = r.product_id ORDER BY p.name")
                if not products_with_recipes.empty:
                    # Menggunakan nama produk untuk dropdown
                    prod_name_to_clear_recipe = st.selectbox("Pilih produk untuk hapus resepnya", products_with_recipes['name'].tolist(), key="del_recipe_select")
                    
                    if st.button(f"Hapus Resep untuk '{prod_name_to_clear_recipe}'", type="primary"):
                        prod_id = products_with_recipes[products_with_recipes['name'] == prod_name_to_clear_recipe]['id'].iloc[0]
                        run_query("DELETE FROM recipes WHERE product_id=?", (prod_id,))
                        st.success(f"Resep untuk '{prod_name_to_clear_recipe}' telah dihapus."); st.rerun()
                else: st.info("Tidak ada produk yang memiliki resep untuk dihapus.")

            with st.expander("Hapus SEMUA Riwayat Transaksi"):
                st.error("Ini akan menghapus semua data penjualan dan tidak bisa dikembalikan.")
                if st.checkbox("Saya mengerti dan ingin melanjutkan."):
                    if st.button("HAPUS SEMUA TRANSAKSI", type="primary"):
                        run_query("DELETE FROM transaction_items"); run_query("DELETE FROM transactions")
                        st.success("Semua riwayat transaksi telah dihapus."); st.rerun()

            with st.expander("Hapus SEMUA Data Pengeluaran"):
                if st.button("HAPUS SEMUA PENGELUARAN", type="primary"):
                    run_query("DELETE FROM expenses"); st.success("Semua data pengeluaran dihapus."); st.rerun()
            
            with st.expander("Hapus SEMUA Data Absensi"):
                if st.button("HAPUS SEMUA ABSENSI", type="primary"):
                    run_query("DELETE FROM attendance"); st.success("Semua data absensi dihapus."); st.rerun()

        with tabs[2]:
            st.subheader("Atur Antar-Muka")
            theme_options = ["Gelap", "Terang"]
            current_theme_index = theme_options.index(st.session_state.get('theme', "Gelap"))
            
            theme = st.selectbox("Pilih Tema Aplikasi", theme_options, index=current_theme_index)
            if st.session_state.theme != theme:
                st.session_state.theme = theme
                st.rerun()

# =====================================================================
# --- TITIK MASUK APLIKASI ---
# =====================================================================
if __name__ == "__main__":
    init_db()
    check_login()
