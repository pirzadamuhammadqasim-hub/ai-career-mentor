"""Database layer for the Inventory & Sales Management System."""
import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str, salt: str | None = None):
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return salt, f"{salt}:{hashed}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split(":", 1)
    except ValueError:
        return False
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest() == hashed


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'staff',
        full_name TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    );
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT,
        email TEXT,
        phone TEXT,
        address TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        address TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category_id INTEGER,
        supplier_id INTEGER,
        cost REAL NOT NULL DEFAULT 0,
        price REAL NOT NULL DEFAULT 0,
        stock INTEGER NOT NULL DEFAULT 0,
        reorder_level INTEGER NOT NULL DEFAULT 5,
        unit TEXT DEFAULT 'pcs',
        description TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(category_id) REFERENCES categories(id),
        FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
    );
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        sale_date TEXT NOT NULL,
        subtotal REAL NOT NULL,
        discount REAL NOT NULL DEFAULT 0,
        tax_rate REAL NOT NULL DEFAULT 0,
        tax REAL NOT NULL DEFAULT 0,
        grand_total REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'completed',
        user_id INTEGER,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES customers(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        qty INTEGER NOT NULL,
        price REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE,
        FOREIGN KEY(product_id) REFERENCES products(id)
    );
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_no TEXT UNIQUE NOT NULL,
        supplier_id INTEGER,
        purchase_date TEXT NOT NULL,
        subtotal REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'received',
        user_id INTEGER,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS purchase_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        qty INTEGER NOT NULL,
        cost REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY(purchase_id) REFERENCES purchases(id) ON DELETE CASCADE,
        FOREIGN KEY(product_id) REFERENCES products(id)
    );
    CREATE TABLE IF NOT EXISTS stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        movement_type TEXT NOT NULL,
        qty INTEGER NOT NULL,
        reference TEXT,
        movement_date TEXT NOT NULL,
        user_id INTEGER,
        FOREIGN KEY(product_id) REFERENCES products(id)
    );
    """)
    conn.commit()

    # Seed users
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        for u, p, role, name in [("admin", "admin123", "admin", "Administrator"),
                                 ("staff", "staff123", "staff", "Staff User")]:
            salt, pw = hash_password(p)
            cur.execute(
                "INSERT INTO users(username,password,role,full_name,created_at) VALUES(?,?,?,?,?)",
                (u, pw, role, name, now),
            )
    # Seed categories
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        for c in ["Electronics", "Clothing", "Groceries", "Stationery", "Home & Living"]:
            cur.execute("INSERT INTO categories(name) VALUES(?)", (c,))
    conn.commit()
    conn.close()


def rows_to_df(rows):
    import pandas as pd
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dict(r) for r in rows])


def now_str():
    return datetime.now().isoformat(timespec="seconds")


# ---------------- Users ----------------
def authenticate(username, password):
    conn = get_conn()
    cur = conn.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if row and verify_password(password, row["password"]):
        return dict(row)
    return None


def list_users():
    conn = get_conn()
    rows = conn.execute("SELECT id,username,role,full_name,created_at FROM users").fetchall()
    conn.close()
    return rows


# ---------------- Categories ----------------
def list_categories():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return rows


def add_category(name, description=""):
    conn = get_conn()
    conn.execute("INSERT INTO categories(name,description) VALUES(?,?)", (name, description))
    conn.commit()
    conn.close()


def update_category(cid, name, description=""):
    conn = get_conn()
    conn.execute("UPDATE categories SET name=?,description=? WHERE id=?", (name, description, cid))
    conn.commit()
    conn.close()


def delete_category(cid):
    conn = get_conn()
    conn.execute("DELETE FROM categories WHERE id=?", (cid,))
    conn.commit()
    conn.close()


# ---------------- Suppliers ----------------
def list_suppliers():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM suppliers ORDER BY name").fetchall()
    conn.close()
    return rows


def add_supplier(name, contact="", email="", phone="", address=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO suppliers(name,contact,email,phone,address,created_at) VALUES(?,?,?,?,?,?)",
        (name, contact, email, phone, address, now_str()),
    )
    conn.commit()
    conn.close()


def update_supplier(sid, name, contact="", email="", phone="", address=""):
    conn = get_conn()
    conn.execute(
        "UPDATE suppliers SET name=?,contact=?,email=?,phone=?,address=? WHERE id=?",
        (name, contact, email, phone, address, sid),
    )
    conn.commit()
    conn.close()


def delete_supplier(sid):
    conn = get_conn()
    conn.execute("DELETE FROM suppliers WHERE id=?", (sid,))
    conn.commit()
    conn.close()


# ---------------- Customers ----------------
def list_customers():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
    conn.close()
    return rows


def add_customer(name, phone="", email="", address=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO customers(name,phone,email,address,created_at) VALUES(?,?,?,?,?)",
        (name, phone, email, address, now_str()),
    )
    conn.commit()
    conn.close()


def update_customer(cid, name, phone="", email="", address=""):
    conn = get_conn()
    conn.execute(
        "UPDATE customers SET name=?,phone=?,email=?,address=? WHERE id=?",
        (name, phone, email, address, cid),
    )
    conn.commit()
    conn.close()


def delete_customer(cid):
    conn = get_conn()
    conn.execute("DELETE FROM customers WHERE id=?", (cid,))
    conn.commit()
    conn.close()


# ---------------- Products ----------------
def list_products():
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.*, c.name AS category_name, s.name AS supplier_name
        FROM products p
        LEFT JOIN categories c ON p.category_id=c.id
        LEFT JOIN suppliers s ON p.supplier_id=s.id
        ORDER BY p.name
    """).fetchall()
    conn.close()
    return rows


def get_product(pid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    conn.close()
    return row


def add_product(sku, name, category_id, supplier_id, cost, price, stock, reorder_level, unit, description=""):
    conn = get_conn()
    now = now_str()
    conn.execute(
        """INSERT INTO products(sku,name,category_id,supplier_id,cost,price,stock,reorder_level,unit,description,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (sku, name, category_id, supplier_id, cost, price, stock, reorder_level, unit, description, now, now),
    )
    conn.commit()
    # stock movement initial
    cur = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    if stock and stock > 0:
        conn.execute(
            "INSERT INTO stock_movements(product_id,movement_type,qty,reference,movement_date) VALUES(?,?,?,?,?)",
            (cur, "initial", stock, "Initial stock", now),
        )
        conn.commit()
    conn.close()


def update_product(pid, sku, name, category_id, supplier_id, cost, price, reorder_level, unit, description=""):
    conn = get_conn()
    conn.execute(
        """UPDATE products SET sku=?,name=?,category_id=?,supplier_id=?,cost=?,price=?,reorder_level=?,unit=?,description=?,updated_at=?
           WHERE id=?""",
        (sku, name, category_id, supplier_id, cost, price, reorder_level, unit, description, now_str(), pid),
    )
    conn.commit()
    conn.close()


def update_stock(pid, new_stock):
    conn = get_conn()
    conn.execute("UPDATE products SET stock=?,updated_at=? WHERE id=?", (new_stock, now_str(), pid))
    conn.commit()
    conn.close()


def delete_product(pid):
    conn = get_conn()
    conn.execute("DELETE FROM products WHERE id=?", (pid,))
    conn.commit()
    conn.close()


# ---------------- Sales ----------------
def next_invoice_no():
    conn = get_conn()
    today = date.today().strftime("%Y%m%d")
    cnt = conn.execute("SELECT COUNT(*) FROM sales WHERE invoice_no LIKE ?", (f"INV-{today}-%",)).fetchone()[0]
    conn.close()
    return f"INV-{today}-{cnt+1:04d}"


def create_sale(customer_id, items, discount_pct, tax_rate, user_id, notes=""):
    """items: list of dict product_id, qty, price"""
    conn = get_conn()
    try:
        invoice = next_invoice_no()
        subtotal = sum(i["qty"] * i["price"] for i in items)
        discount = round(subtotal * (discount_pct / 100.0), 2)
        after_discount = subtotal - discount
        tax = round(after_discount * (tax_rate / 100.0), 2)
        grand = round(after_discount + tax, 2)
        now = now_str()
        cur = conn.execute(
            """INSERT INTO sales(invoice_no,customer_id,sale_date,subtotal,discount,tax_rate,tax,grand_total,status,user_id,notes,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (invoice, customer_id, now, subtotal, discount, tax_rate, tax, grand, "completed", user_id, notes, now),
        )
        sale_id = cur.lastrowid
        for i in items:
            line_sub = i["qty"] * i["price"]
            conn.execute(
                "INSERT INTO sale_items(sale_id,product_id,qty,price,subtotal) VALUES(?,?,?,?,?)",
                (sale_id, i["product_id"], i["qty"], i["price"], line_sub),
            )
            # decrement stock
            conn.execute(
                "UPDATE products SET stock=stock-?, updated_at=? WHERE id=?",
                (i["qty"], now, i["product_id"]),
            )
            conn.execute(
                "INSERT INTO stock_movements(product_id,movement_type,qty,reference,movement_date,user_id) VALUES(?,?,?,?,?,?)",
                (i["product_id"], "sale", -i["qty"], invoice, now, user_id),
            )
        conn.commit()
        return sale_id, invoice, grand
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_sales(limit=500):
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.*, c.name AS customer_name, u.username AS created_by_name
        FROM sales s
        LEFT JOIN customers c ON s.customer_id=c.id
        LEFT JOIN users u ON s.user_id=u.id
        ORDER BY s.id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows


def get_sale_items(sale_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT si.*, p.name AS product_name, p.sku
        FROM sale_items si JOIN products p ON si.product_id=p.id
        WHERE si.sale_id=? ORDER BY si.id
    """, (sale_id,)).fetchall()
    conn.close()
    return rows


def sale_detail(sale_id):
    conn = get_conn()
    sale = conn.execute("""
        SELECT s.*, c.name AS customer_name, c.phone AS customer_phone, c.email AS customer_email,
               c.address AS customer_address, u.username AS created_by_name
        FROM sales s
        LEFT JOIN customers c ON s.customer_id=c.id
        LEFT JOIN users u ON s.user_id=u.id
        WHERE s.id=?
    """, (sale_id,)).fetchone()
    conn.close()
    return sale


# ---------------- Purchases ----------------
def next_po_no():
    conn = get_conn()
    today = date.today().strftime("%Y%m%d")
    cnt = conn.execute("SELECT COUNT(*) FROM purchases WHERE po_no LIKE ?", (f"PO-{today}-%",)).fetchone()[0]
    conn.close()
    return f"PO-{today}-{cnt+1:04d}"


def create_purchase(supplier_id, items, user_id, notes=""):
    conn = get_conn()
    try:
        po = next_po_no()
        subtotal = sum(i["qty"] * i["cost"] for i in items)
        now = now_str()
        cur = conn.execute(
            """INSERT INTO purchases(po_no,supplier_id,purchase_date,subtotal,status,user_id,notes,created_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (po, supplier_id, now, subtotal, "received", user_id, notes, now),
        )
        pid = cur.lastrowid
        for i in items:
            line_sub = i["qty"] * i["cost"]
            conn.execute(
                "INSERT INTO purchase_items(purchase_id,product_id,qty,cost,subtotal) VALUES(?,?,?,?,?)",
                (pid, i["product_id"], i["qty"], i["cost"], line_sub),
            )
            conn.execute(
                "UPDATE products SET stock=stock+?, cost=?, updated_at=? WHERE id=?",
                (i["qty"], i["cost"], now, i["product_id"]),
            )
            conn.execute(
                "INSERT INTO stock_movements(product_id,movement_type,qty,reference,movement_date,user_id) VALUES(?,?,?,?,?,?)",
                (i["product_id"], "purchase", i["qty"], po, now, user_id),
            )
        conn.commit()
        return pid, po, subtotal
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_purchases(limit=500):
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.*, s.name AS supplier_name, u.username AS created_by_name
        FROM purchases p
        LEFT JOIN suppliers s ON p.supplier_id=s.id
        LEFT JOIN users u ON p.user_id=u.id
        ORDER BY p.id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows


def get_purchase_items(purchase_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT pi.*, pr.name AS product_name, pr.sku
        FROM purchase_items pi JOIN products pr ON pi.product_id=pr.id
        WHERE pi.purchase_id=? ORDER BY pi.id
    """, (purchase_id,)).fetchall()
    conn.close()
    return rows


# ---------------- Dashboard helpers ----------------
def dashboard_stats():
    conn = get_conn()
    total_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_stock_value = conn.execute("SELECT COALESCE(SUM(stock*cost),0) FROM products").fetchone()[0]
    low_stock = conn.execute("SELECT COUNT(*) FROM products WHERE stock<=reorder_level").fetchone()[0]
    out_of_stock = conn.execute("SELECT COUNT(*) FROM products WHERE stock<=0").fetchone()[0]
    total_sales = conn.execute("SELECT COALESCE(SUM(grand_total),0) FROM sales").fetchone()[0]
    today_sales = conn.execute(
        "SELECT COALESCE(SUM(grand_total),0) FROM sales WHERE date(sale_date)=date('now','localtime')"
    ).fetchone()[0]
    total_customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    total_suppliers = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
    conn.close()
    return {
        "total_products": total_products,
        "total_stock_value": total_stock_value,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "total_sales": total_sales,
        "today_sales": today_sales,
        "total_customers": total_customers,
        "total_suppliers": total_suppliers,
    }


def low_stock_products():
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.stock <= p.reorder_level ORDER BY p.stock ASC
    """).fetchall()
    conn.close()
    return rows


def top_products(limit=5):
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.name, SUM(si.qty) AS qty_sold, SUM(si.subtotal) AS revenue
        FROM sale_items si JOIN products p ON si.product_id=p.id
        GROUP BY p.id ORDER BY revenue DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows


def sales_by_day(days=14):
    conn = get_conn()
    rows = conn.execute("""
        SELECT date(sale_date) AS d, COUNT(*) AS orders, COALESCE(SUM(grand_total),0) AS revenue
        FROM sales
        WHERE sale_date >= date('now','localtime', ?)
        GROUP BY date(sale_date) ORDER BY d
    """, (f"-{days} days",)).fetchall()
    conn.close()
    return rows