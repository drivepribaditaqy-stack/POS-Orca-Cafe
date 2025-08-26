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
# PERUBAHAN: Mengganti judul halaman dan nama kafe
st.set_page_config(layout="wide", page_title="Warkop Orca")

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
        # PERUBAHAN: Mengosongkan daftar produk awal.
        st.info("Tabel produk kosong. Silakan tambahkan produk baru di menu 'Pengaturan'.")
        products = [] # Dikosongkan
        if products:
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
        # PERUBAHAN: Mengganti judul dan quotes sesuai tema Warkop Orca
        st.title("☕ Warkop Orca")
        quotes = [
            "Ngopi dulu, biar nggak salah paham.",
            "Hidup itu singkat, jangan lupa ngopi.",
            "Secangkir kopi, sejuta cerita.",
            "Warkop bukan cuma tempat ngopi, tapi tempat berbagi.",
            "Dompet tipis, ngopi tetap eksis.",
            "Jangan ada sianida di antara kita, cukup kopi hitam saja.",
            "Masalah? Kopiin aja.",
            "Di sini, semua sama. Yang beda cuma pesenannya."
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
    # PERUBAHAN: Injeksi CSS untuk tema Warkop Orca (nuansa biru laut)
    custom_css = """
    <style>
    /* Color Palette Warkop Orca */
    :root {
        --primary-color: #0077B6;      /* Biru Laut Primer */
        --secondary-color: #00B4D8;    /* Biru Laut Sekunder (lebih cerah) */
        --background-color: #F0F8FF;   /* AliceBlue - Latar belakang putih kebiruan */
        --text-color: #023047;         /* Biru Tua untuk teks */
        --widget-background: #FFFFFF;  /* Putih untuk widget */
        --danger-color: #D32F2F;       /* Merah untuk tombol hapus */
    }

    /* Body & Text */
    body {
        color: var(--text-color);
        background-color: var(--background-color);
    }
    
    /* Sidebar */
    .st-emotion-cache-16txtl3 {
        background-color: var(--widget-background);
    }

    /* Main Content Area */
    .st-emotion-cache-1y4p8pa {
        background-color: var(--background-color);
    }

    /* Tombol Utama */
    .stButton>button {
        background-color: var(--primary-color);
        color: white; /* Teks putih agar kontras dengan tombol biru */
        border: 2px solid var(--primary-color);
        font-weight: bold;
        border-radius: 8px;
    }
    .stButton>button:hover {
        background-color: var(--secondary-color);
        color: var(--text-color);
        border: 2px solid var(--secondary-color);
    }

    /* Tombol Hapus & Aksi Berbahaya */
    .stButton>button[kind="primary"] {
        background-color: var(--danger-color);
        color: white;
        border: none;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #E57373; /* Merah lebih terang saat hover */
    }

    /* Input & Widget Styling */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div {
        background-color: var(--widget-background);
        border-radius: 5px;
    }
    
    /* Header & Title */
    h1, h2, h3 {
        color: var(--primary-color);
    }

    /* Metric Label */
    .st-emotion-cache-1g8m5r4 {
        color: var(--text-color);
    }
    
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

    # --- Navigasi Sidebar ---
    st.sidebar.title("Menu Navigasi")
    # PERUBAHAN: Mengikuti struktur menu dari file asli dan menambahkan menu Pengaturan
    if st.session_state.role == 'Admin':
        menu_options = ["Kasir (POS)", "Laporan", "Manajemen Produk", "Manajemen Stok", "Manajemen Karyawan", "Absensi", "Pengeluaran", "Pengaturan"]
    else: # Operator
        menu_options = ["Kasir (POS)", "Absensi", "Pengeluaran"]
    
    choice = st.sidebar.radio("Pilih Halaman", menu_options)

    # --- Menampilkan halaman yang dipilih ---
    if choice == "Kasir (POS)": pos_page()
    elif choice == "Laporan": reports_page()
    elif choice == "Manajemen Produk": product_management_page()
    elif choice == "Manajemen Stok": inventory_management_page()
    elif choice == "Manajemen Karyawan": employee_management_page()
    elif choice == "Absensi": attendance_page()
    elif choice == "Pengeluaran": expenses_page()
    elif choice == "Pengaturan": settings_page()

# =====================================================================
# --- FUNGSI-FUNGSI BANTU (Database & Lainnya) ---
# =====================================================================
@st.cache_data(ttl=60)
def get_df(query, params=()):
    conn = sqlite3.connect(DB); 
    df = pd.read_sql_query(query, conn, params=params); 
    conn.close(); 
    return df

def run_query(query, params=(), fetch=None):
    conn = sqlite3.connect(DB); 
    c = conn.cursor(); 
    c.execute(query, params)
    result = None
    if fetch == 'one': result = c.fetchone()
    elif fetch == 'all': result = c.fetchall()
    conn.commit(); 
    conn.close(); 
    return result

# =====================================================================
# --- HALAMAN-HALAMAN APLIKASI ---
# =====================================================================

# --- HALAMAN KASIR (POS) ---
def pos_page():
    st.header("🔵 Kasir (Point of Sale)")
    
    if 'cart' not in st.session_state: st.session_state.cart = {}

    products_df = get_df("SELECT id, name, price FROM products ORDER BY name ASC")
    product_dict = {row['name']: {'id': row['id'], 'price': row['price']} for index, row in products_df.iterrows()}
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Pilih Produk")
        
        # Grid layout for products
        product_names = list(product_dict.keys())
        grid_cols = st.columns(4)
        for i, name in enumerate(product_names):
            with grid_cols[i % 4]:
                if st.button(name, key=f"prod_{name}", use_container_width=True):
                    if name in st.session_state.cart:
                        st.session_state.cart[name] += 1
                    else:
                        st.session_state.cart[name] = 1
                    st.rerun()

    with col2:
        st.subheader("🛒 Keranjang Belanja")
        total_price = 0
        if not st.session_state.cart:
            st.info("Keranjang masih kosong.")
        else:
            for product_name, qty in list(st.session_state.cart.items()):
                item_col, qty_col, action_col = st.columns([3, 2, 1])
                price = product_dict[product_name]['price']
                subtotal = qty * price
                total_price += subtotal

                with item_col:
                    st.write(product_name)
                    st.caption(f"Rp {price:,.0f}")
                with qty_col:
                    new_qty = st.number_input("Qty", value=qty, min_value=1, key=f"qty_{product_name}", label_visibility="collapsed")
                    if new_qty != qty:
                        st.session_state.cart[product_name] = new_qty
                        st.rerun()
                with action_col:
                    if st.button("❌", key=f"del_{product_name}", help="Hapus item"):
                        del st.session_state.cart[product_name]
                        st.rerun()
            
            st.markdown("---")
            st.metric("Total Belanja", f"Rp {total_price:,.0f}")

            payment_method = st.selectbox("Metode Pembayaran", ["Cash", "QRIS", "Debit"], key="payment_pos")
            
            if st.button("✅ Proses Pembayaran", disabled=(total_price == 0), use_container_width=True):
                trans_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                run_query(
                    "INSERT INTO transactions (transaction_date, total_amount, payment_method, employee_id) VALUES (?, ?, ?, ?)",
                    (trans_date, total_price, payment_method, st.session_state.user_id)
                )
                last_trans_id = run_query("SELECT last_insert_rowid()", fetch='one')[0]

                for name, qty in st.session_state.cart.items():
                    prod_info = product_dict[name]
                    run_query(
                        "INSERT INTO transaction_items (transaction_id, product_id, quantity, price_per_unit) VALUES (?, ?, ?, ?)",
                        (last_trans_id, prod_info['id'], qty, prod_info['price'])
                    )
                
                st.success(f"Transaksi berhasil! Total: Rp {total_price:,.0f}")
                st.session_state.cart = {}
                st.rerun()

# --- HALAMAN LAPORAN ---
def reports_page():
    st.header("📊 Laporan Penjualan & Keuangan")
    
    today = date.today()
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("Tanggal Mulai", today - timedelta(days=7))
    with col2:
        end_date = st.date_input("Tanggal Akhir", today)
    with col3:
        st.write("")
        st.write("")
        if st.button("Tampilkan Laporan", use_container_width=True):
            st.rerun()

    start_datetime = datetime.combine(start_date, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')
    end_datetime = datetime.combine(end_date, datetime.max.time()).strftime('%Y-%m-%d %H:%M:%S')

    sales_query = """
        SELECT t.transaction_date, ti.quantity, ti.price_per_unit, p.name as product_name
        FROM transactions t
        JOIN transaction_items ti ON t.id = ti.transaction_id
        JOIN products p ON ti.product_id = p.id
        WHERE t.transaction_date BETWEEN ? AND ?
    """
    expenses_query = "SELECT date, category, amount FROM expenses WHERE date BETWEEN ? AND ?"
    
    sales_df = get_df(sales_query, (start_datetime, end_datetime))
    expenses_df = get_df(expenses_query, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))

    st.subheader("Ringkasan Keuangan")
    total_revenue = (sales_df['quantity'] * sales_df['price_per_unit']).sum()
    total_expense = expenses_df['amount'].sum()
    net_profit = total_revenue - total_expense

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Pendapatan", f"Rp {total_revenue:,.0f}")
    m2.metric("Total Pengeluaran", f"Rp {total_expense:,.0f}")
    m3.metric("Laba Bersih", f"Rp {net_profit:,.0f}", delta=f"{net_profit:,.0f}")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📈 Tren Pendapatan", "📦 Produk Terlaris", "💸 Rincian Pengeluaran"])

    with tab1:
        if not sales_df.empty:
            sales_df['transaction_date'] = pd.to_datetime(sales_df['transaction_date'])
            sales_df['revenue'] = sales_df['quantity'] * sales_df['price_per_unit']
            daily_revenue = sales_df.resample('D', on='transaction_date')['revenue'].sum().reset_index()
            fig = go.Figure(go.Scatter(x=daily_revenue['transaction_date'], y=daily_revenue['revenue'], mode='lines+markers'))
            fig.update_layout(title='Tren Pendapatan Harian', xaxis_title='Tanggal', yaxis_title='Pendapatan (Rp)')
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Tidak ada data penjualan.")

    with tab2:
        if not sales_df.empty:
            top_products = sales_df.groupby('product_name')['quantity'].sum().nlargest(10).sort_values(ascending=True)
            fig = go.Figure(go.Bar(y=top_products.index, x=top_products.values, orientation='h'))
            fig.update_layout(title='Top 10 Produk Terlaris', xaxis_title='Jumlah Terjual', yaxis_title='Produk')
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Tidak ada data penjualan.")

    with tab3:
        if not expenses_df.empty:
            expense_by_cat = expenses_df.groupby('category')['amount'].sum()
            fig = go.Figure(go.Pie(labels=expense_by_cat.index, values=expense_by_cat.values, hole=.3))
            fig.update_layout(title='Distribusi Pengeluaran per Kategori')
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Tidak ada data pengeluaran.")

# --- HALAMAN MANAJEMEN PRODUK ---
def product_management_page():
    st.header("📦 Manajemen Produk")
    products_df = get_df("SELECT id, name, price FROM products ORDER BY name ASC")
    tabs = st.tabs(["Daftar Produk", "Tambah/Edit Produk"])
    
    with tabs[0]:
        st.dataframe(products_df, use_container_width=True, hide_index=True)

    with tabs[1]:
        st.subheader("Tambah atau Edit Produk")
        product_names = ["-- Tambah Produk Baru --"] + products_df['name'].tolist()
        selected_product = st.selectbox("Pilih produk untuk diedit", product_names)
        is_new = selected_product == "-- Tambah Produk Baru --"
        
        with st.form("product_form"):
            name = st.text_input("Nama Produk", value="" if is_new else selected_product)
            price = st.number_input("Harga", min_value=0, value=0 if is_new else int(products_df[products_df.name == selected_product].price.iloc[0]))
            
            if st.form_submit_button("Simpan"):
                if not name or price <= 0: st.warning("Nama dan harga harus diisi.")
                else:
                    if is_new: run_query("INSERT INTO products (name, price) VALUES (?, ?)", (name, price))
                    else: run_query("UPDATE products SET name=?, price=? WHERE id=?", (name, price, int(products_df[products_df.name == selected_product].id.iloc[0])))
                    st.success("Data produk disimpan."); st.rerun()

# --- HALAMAN MANAJEMEN STOK ---
def inventory_management_page():
    st.header("📋 Manajemen Stok Bahan")
    st.info("Fitur ini masih dalam pengembangan.")

# --- HALAMAN MANAJEMEN KARYAWAN ---
def employee_management_page():
    st.header("👥 Manajemen Karyawan")
    emp_df = get_df("SELECT id, name, role, wage_amount, wage_period, is_active FROM employees")
    tabs = st.tabs(["Daftar Karyawan", "Tambah/Edit Karyawan"])

    with tabs[0]: st.dataframe(emp_df, use_container_width=True, hide_index=True)
    with tabs[1]:
        st.subheader("Tambah atau Edit Karyawan")
        emp_names = ["-- Tambah Karyawan Baru --"] + emp_df['name'].tolist()
        selected_emp = st.selectbox("Pilih karyawan", emp_names)
        is_new = selected_emp == "-- Tambah Karyawan Baru --"

        with st.form("employee_form"):
            emp_data = emp_df[emp_df.name == selected_emp].iloc[0] if not is_new else None
            name = st.text_input("Nama", value="" if is_new else emp_data['name'])
            role = st.selectbox("Peran", ["Admin", "Operator"], index=0 if is_new else ["Admin", "Operator"].index(emp_data['role']))
            password = st.text_input("Password (kosongkan jika tidak diubah)", type="password")
            wage_amount = st.number_input("Gaji/Upah", min_value=0.0, value=0.0 if is_new else emp_data['wage_amount'], format="%.2f")
            wage_period = st.selectbox("Periode", ["Per Jam", "Per Hari", "Per Bulan"], index=0 if is_new else ["Per Jam", "Per Hari", "Per Bulan"].index(emp_data['wage_period']))
            is_active = st.checkbox("Aktif", value=True if is_new else bool(emp_data['is_active']))

            if st.form_submit_button("Simpan"):
                if not name: st.warning("Nama harus diisi.")
                elif is_new and not password: st.warning("Password harus diisi untuk karyawan baru.")
                else:
                    if is_new:
                        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
                        run_query("INSERT INTO employees (name, role, password, wage_amount, wage_period, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                                  (name.lower(), role, hashed_pw, wage_amount, wage_period, is_active))
                    else:
                        emp_id = int(emp_data['id'])
                        if password:
                            hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
                            run_query("UPDATE employees SET name=?, role=?, password=?, wage_amount=?, wage_period=?, is_active=? WHERE id=?",
                                      (name.lower(), role, hashed_pw, wage_amount, wage_period, is_active, emp_id))
                        else:
                            run_query("UPDATE employees SET name=?, role=?, wage_amount=?, wage_period=?, is_active=? WHERE id=?",
                                      (name.lower(), role, wage_amount, wage_period, is_active, emp_id))
                    st.success("Data karyawan disimpan."); st.rerun()

# --- HALAMAN ABSENSI ---
def attendance_page():
    st.header("🕒 Absensi Karyawan")
    emp_id = st.session_state.user_id
    today_str = date.today().strftime('%Y-%m-%d')
    last_att = run_query("SELECT id, check_in, check_out FROM attendance WHERE employee_id = ? AND date(check_in) = ? ORDER BY id DESC LIMIT 1", (emp_id, today_str), 'one')

    checked_in, checked_out = (True, bool(last_att[2])) if last_att else (False, False)

    col1, col2 = st.columns(2)
    with col1:
        if not checked_in:
            if st.button("⏰ Check-in", use_container_width=True):
                run_query("INSERT INTO attendance (employee_id, check_in) VALUES (?, ?)", (emp_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                st.success("Berhasil check-in."); st.rerun()
        else: st.success(f"Check-in pada: {last_att[1]}")

    with col2:
        if checked_in and not checked_out:
            if st.button("👋 Check-out", use_container_width=True):
                run_query("UPDATE attendance SET check_out = ? WHERE id = ?", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), last_att[0]))
                st.success("Berhasil check-out."); st.rerun()
        elif checked_out: st.info(f"Check-out pada: {last_att[2]}")

    st.subheader("Riwayat Absensi Anda")
    st.dataframe(get_df("SELECT check_in, check_out FROM attendance WHERE employee_id = ? ORDER BY check_in DESC LIMIT 30", (emp_id,)), hide_index=True)

# --- HALAMAN PENGELUARAN ---
def expenses_page():
    st.header("💸 Catat Pengeluaran")
    with st.form("expense_form"):
        exp_date = st.date_input("Tanggal", date.today())
        category = st.selectbox("Kategori", ["Bahan Baku", "Gaji", "Operasional", "Marketing", "Lainnya"])
        description = st.text_input("Deskripsi")
        amount = st.number_input("Jumlah (Rp)", min_value=0.0, format="%.2f")
        payment_method = st.selectbox("Metode Pembayaran", ["Cash", "Transfer", "Debit"])
        
        if st.form_submit_button("Simpan"):
            if not description or amount <= 0: st.warning("Deskripsi dan jumlah harus diisi.")
            else:
                run_query("INSERT INTO expenses (date, category, description, amount, payment_method) VALUES (?, ?, ?, ?, ?)",
                          (exp_date.strftime('%Y-%m-%d'), category, description, amount, payment_method))
                st.success("Pengeluaran dicatat."); st.rerun()
    
    st.subheader("Riwayat Pengeluaran")
    st.dataframe(get_df("SELECT date, category, description, amount, payment_method FROM expenses ORDER BY date DESC LIMIT 50"), hide_index=True)

# --- HALAMAN PENGATURAN ---
def settings_page():
    st.header("⚙️ Pengaturan Aplikasi")
    st.info("Di halaman ini Anda dapat menghapus data transaksi secara massal untuk memulai periode baru.")
    st.warning("PERHATIAN: Aksi di halaman ini tidak dapat diurungkan dan akan menghapus data secara permanen.")

    tabs = st.tabs(["Hapus Data Transaksi", "Hapus Data Pengeluaran", "Hapus Data Absensi"])

    with tabs[0]:
        st.subheader("Hapus Seluruh Riwayat Transaksi")
        if st.button("Hapus Semua Transaksi", type="primary", key="del_trans"):
            run_query("DELETE FROM transactions"); run_query("DELETE FROM transaction_items")
            st.success("Semua data transaksi telah dihapus.")
    
    with tabs[1]:
        st.subheader("Hapus Seluruh Riwayat Pengeluaran")
        if st.button("Hapus Semua Pengeluaran", type="primary", key="del_exp"):
            run_query("DELETE FROM expenses")
            st.success("Semua data pengeluaran telah dihapus.")

    with tabs[2]:
        st.subheader("Hapus Seluruh Riwayat Absensi")
        if st.button("Hapus Semua Absensi", type="primary", key="del_att"):
            run_query("DELETE FROM attendance")
            st.success("Semua data absensi telah dihapus.")


# =====================================================================
# --- TITIK MASUK APLIKASI ---
# =====================================================================
if __name__ == "__main__":
    init_db()
    check_login()
