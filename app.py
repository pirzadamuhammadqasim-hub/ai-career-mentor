"""Inventory & Sales Management System - Streamlit app."""
import os
import sys
from datetime import date, timedelta

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

st.set_page_config(
    page_title="Inventory & Sales Management",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- bootstrap db ----------
db.init_db()


# ---------- session state ----------
def ss(key, default=None):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


ss("user", None)
ss("page", "Dashboard")
ss("sales_cart", [])
ss("purchase_cart", [])


# ---------- helpers ----------
def money(x):
    return f"{x:,.2f}"


def require_login():
    if st.session_state.user is None:
        show_login()
        st.stop()


def show_login():
    st.title("📦 Inventory & Sales Management")
    st.subheader("Please sign in")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                user = db.authenticate(username.strip(), password)
                if user:
                    st.session_state.user = user
                    st.session_state.page = "Dashboard"
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        st.caption("Default accounts: admin / admin123  |  staff / staff123")


def logout():
    st.session_state.user = None
    st.session_state.sales_cart = []
    st.session_state.purchase_cart = []
    st.rerun()


# ---------- sidebar ----------
def sidebar():
    user = st.session_state.user
    st.sidebar.title("📦 INV & SALES")
    st.sidebar.markdown(f"**{user['full_name'] or user['username']}**  \nRole: `{user['role']}`")
    pages = ["Dashboard", "Products", "Categories", "Suppliers", "Customers"]
    pages += ["Sales (POS)", "Purchases", "Reports", "Stock Movements"]
    if user["role"] == "admin":
        pages += ["Users"]
    page = st.sidebar.radio("Navigation", pages, index=pages.index(st.session_state.page) if st.session_state.page in pages else 0)
    st.session_state.page = page
    st.sidebar.divider()
    if st.sidebar.button("Logout", use_container_width=True):
        logout()


# ---------- Dashboard ----------
def page_dashboard():
    st.title("Dashboard")
    stats = db.dashboard_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Products", stats["total_products"])
    c2.metric("Stock Value (cost)", f"{money(stats['total_stock_value'])}")
    c3.metric("Today's Sales", f"{money(stats['today_sales'])}")
    c4.metric("Total Sales", f"{money(stats['total_sales'])}")
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Low Stock", stats["low_stock"])
    c6.metric("Out of Stock", stats["out_of_stock"])
    c7.metric("Customers", stats["total_customers"])
    c8.metric("Suppliers", stats["total_suppliers"])

    st.divider()
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.subheader("Sales (last 14 days)")
        rows = db.sales_by_day(14)
        if rows:
            df = pd.DataFrame([dict(r) for r in rows])
            df = df.set_index("d")
            st.bar_chart(df["revenue"])
        else:
            st.info("No sales yet.")
    with col_b:
        st.subheader("Low stock alerts")
        rows = db.low_stock_products()
        if rows:
            df = pd.DataFrame([dict(r) for r in rows])[["name", "stock", "reorder_level"]]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.success("All stock levels healthy.")

    st.subheader("Top products by revenue")
    rows = db.top_products(5)
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No sales data yet.")


# ---------- Categories ----------
def page_categories():
    st.title("Categories")
    tab1, tab2 = st.tabs(["List", "Add / Edit"])
    categories = db.list_categories()
    with tab1:
        if categories:
            df = pd.DataFrame([dict(r) for r in categories])
            st.dataframe(df[["id", "name", "description"]], use_container_width=True, hide_index=True)
        else:
            st.info("No categories.")
    with tab2:
        names = [r["name"] for r in categories]
        mode = st.radio("Mode", ["Add", "Edit", "Delete"], horizontal=True)
        if mode == "Add":
            with st.form("add_cat"):
                name = st.text_input("Name")
                desc = st.text_input("Description")
                if st.form_submit_button("Add"):
                    if name.strip():
                        try:
                            db.add_category(name.strip(), desc.strip())
                            st.success("Added")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                    else:
                        st.error("Name required")
        elif mode == "Edit":
            if not categories:
                st.info("No categories.")
            else:
                sel = st.selectbox("Select", [r["id"] for r in categories], format_func=lambda x: next(r["name"] for r in categories if r["id"] == x))
                cat = next(r for r in categories if r["id"] == sel)
                with st.form("edit_cat"):
                    name = st.text_input("Name", value=cat["name"])
                    desc = st.text_input("Description", value=cat["description"] or "")
                    if st.form_submit_button("Update"):
                        db.update_category(sel, name.strip(), desc.strip())
                        st.success("Updated")
                        st.rerun()
        else:
            if not categories:
                st.info("No categories.")
            else:
                sel = st.selectbox("Select to delete", [r["id"] for r in categories], format_func=lambda x: next(r["name"] for r in categories if r["id"] == x))
                if st.button("Delete", type="primary"):
                    try:
                        db.delete_category(sel)
                        st.success("Deleted")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))


# ---------- Suppliers ----------
def page_suppliers():
    st.title("Suppliers")
    suppliers = db.list_suppliers()
    tab1, tab2 = st.tabs(["List", "Manage"])
    with tab1:
        if suppliers:
            df = pd.DataFrame([dict(r) for r in suppliers])
            st.dataframe(df[["id", "name", "contact", "email", "phone", "address"]], use_container_width=True, hide_index=True)
        else:
            st.info("No suppliers.")
    with tab2:
        mode = st.radio("Mode", ["Add", "Edit", "Delete"], horizontal=True)
        if mode == "Add":
            with st.form("add_sup"):
                name = st.text_input("Name*")
                contact = st.text_input("Contact person")
                email = st.text_input("Email")
                phone = st.text_input("Phone")
                address = st.text_area("Address")
                if st.form_submit_button("Add"):
                    if name.strip():
                        db.add_supplier(name.strip(), contact, email, phone, address)
                        st.success("Added")
                        st.rerun()
                    else:
                        st.error("Name required")
        elif mode == "Edit":
            if not suppliers:
                st.info("No suppliers.")
            else:
                sel = st.selectbox("Select", [r["id"] for r in suppliers], format_func=lambda x: next(r["name"] for r in suppliers if r["id"] == x))
                s = next(r for r in suppliers if r["id"] == sel)
                with st.form("edit_sup"):
                    name = st.text_input("Name", value=s["name"])
                    contact = st.text_input("Contact", value=s["contact"] or "")
                    email = st.text_input("Email", value=s["email"] or "")
                    phone = st.text_input("Phone", value=s["phone"] or "")
                    address = st.text_area("Address", value=s["address"] or "")
                    if st.form_submit_button("Update"):
                        db.update_supplier(sel, name.strip(), contact, email, phone, address)
                        st.success("Updated")
                        st.rerun()
        else:
            if not suppliers:
                st.info("No suppliers.")
            else:
                sel = st.selectbox("Select to delete", [r["id"] for r in suppliers], format_func=lambda x: next(r["name"] for r in suppliers if r["id"] == x))
                if st.button("Delete", type="primary"):
                    try:
                        db.delete_supplier(sel)
                        st.success("Deleted")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))


# ---------- Customers ----------
def page_customers():
    st.title("Customers")
    customers = db.list_customers()
    tab1, tab2 = st.tabs(["List", "Manage"])
    with tab1:
        if customers:
            df = pd.DataFrame([dict(r) for r in customers])
            st.dataframe(df[["id", "name", "phone", "email", "address"]], use_container_width=True, hide_index=True)
        else:
            st.info("No customers.")
    with tab2:
        mode = st.radio("Mode", ["Add", "Edit", "Delete"], horizontal=True)
        if mode == "Add":
            with st.form("add_cust"):
                name = st.text_input("Name*")
                phone = st.text_input("Phone")
                email = st.text_input("Email")
                address = st.text_area("Address")
                if st.form_submit_button("Add"):
                    if name.strip():
                        db.add_customer(name.strip(), phone, email, address)
                        st.success("Added")
                        st.rerun()
                    else:
                        st.error("Name required")
        elif mode == "Edit":
            if not customers:
                st.info("No customers.")
            else:
                sel = st.selectbox("Select", [r["id"] for r in customers], format_func=lambda x: next(r["name"] for r in customers if r["id"] == x))
                c = next(r for r in customers if r["id"] == sel)
                with st.form("edit_cust"):
                    name = st.text_input("Name", value=c["name"])
                    phone = st.text_input("Phone", value=c["phone"] or "")
                    email = st.text_input("Email", value=c["email"] or "")
                    address = st.text_area("Address", value=c["address"] or "")
                    if st.form_submit_button("Update"):
                        db.update_customer(sel, name.strip(), phone, email, address)
                        st.success("Updated")
                        st.rerun()
        else:
            if not customers:
                st.info("No customers.")
            else:
                sel = st.selectbox("Select to delete", [r["id"] for r in customers], format_func=lambda x: next(r["name"] for r in customers if r["id"] == x))
                if st.button("Delete", type="primary"):
                    try:
                        db.delete_customer(sel)
                        st.success("Deleted")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))


# ---------- Products ----------
def page_products():
    st.title("Products / Inventory")
    products = db.list_products()
    categories = db.list_categories()
    suppliers = db.list_suppliers()
    cat_map = {r["id"]: r["name"] for r in categories}
    sup_map = {r["id"]: r["name"] for r in suppliers}

    tabs = st.tabs(["All Products", "Add Product", "Edit Product", "Delete"])
    with tabs[0]:
        if not products:
            st.info("No products yet.")
        else:
            q = st.text_input("Search", "")
            df = pd.DataFrame([dict(r) for r in products])
            if q.strip():
                mask = df["name"].str.contains(q, case=False, na=False) | df["sku"].str.contains(q, case=False, na=False)
                df = df[mask]
            show_cols = ["id", "sku", "name", "category_name", "supplier_name", "cost", "price", "stock", "reorder_level", "unit"]
            st.dataframe(df[show_cols], use_container_width=True, hide_index=True)
            # low stock filter
            low = [r for r in products if r["stock"] <= r["reorder_level"]]
            if low:
                st.warning(f"{len(low)} product(s) at or below reorder level.")
    with tabs[1]:
        with st.form("add_prod"):
            sku = st.text_input("SKU*")
            name = st.text_input("Name*")
            c1, c2 = st.columns(2)
            cat_id = c1.selectbox("Category", [None] + [r["id"] for r in categories], format_func=lambda x: "None" if x is None else cat_map[x])
            sup_id = c2.selectbox("Supplier", [None] + [r["id"] for r in suppliers], format_func=lambda x: "None" if x is None else sup_map[x])
            c3, c4 = st.columns(2)
            cost = c3.number_input("Cost", min_value=0.0, value=0.0, step=0.01, format="%.2f")
            price = c4.number_input("Price", min_value=0.0, value=0.0, step=0.01, format="%.2f")
            c5, c6, c7 = st.columns(3)
            stock = c5.number_input("Initial stock", min_value=0, value=0, step=1)
            reorder = c6.number_input("Reorder level", min_value=0, value=5, step=1)
            unit = c7.text_input("Unit", value="pcs")
            desc = st.text_area("Description")
            if st.form_submit_button("Add Product"):
                if sku.strip() and name.strip():
                    try:
                        db.add_product(sku.strip(), name.strip(), cat_id, sup_id, cost, price, int(stock), int(reorder), unit.strip() or "pcs", desc.strip())
                        st.success("Product added")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
                else:
                    st.error("SKU and Name required")
    with tabs[2]:
        if not products:
            st.info("No products.")
        else:
            sel = st.selectbox("Select product", [r["id"] for r in products], format_func=lambda x: f"{next(r['sku'] for r in products if r['id']==x)} - {next(r['name'] for r in products if r['id']==x)}")
            p = next(r for r in products if r["id"] == sel)
            with st.form("edit_prod"):
                sku = st.text_input("SKU", value=p["sku"])
                name = st.text_input("Name", value=p["name"])
                c1, c2 = st.columns(2)
                cat_id = c1.selectbox("Category", [None] + [r["id"] for r in categories], index=([None] + [r["id"] for r in categories]).index(p["category_id"]) if p["category_id"] in [r["id"] for r in categories] else 0, format_func=lambda x: "None" if x is None else cat_map.get(x, x))
                sup_id = c2.selectbox("Supplier", [None] + [r["id"] for r in suppliers], index=([None] + [r["id"] for r in suppliers]).index(p["supplier_id"]) if p["supplier_id"] in [r["id"] for r in suppliers] else 0, format_func=lambda x: "None" if x is None else sup_map.get(x, x))
                c3, c4 = st.columns(2)
                cost = c3.number_input("Cost", min_value=0.0, value=float(p["cost"]), step=0.01, format="%.2f")
                price = c4.number_input("Price", min_value=0.0, value=float(p["price"]), step=0.01, format="%.2f")
                c5, c6, c7 = st.columns(3)
                reorder = c5.number_input("Reorder level", min_value=0, value=int(p["reorder_level"]), step=1)
                unit = c6.text_input("Unit", value=p["unit"] or "pcs")
                new_stock = c7.number_input("Stock (adjust)", min_value=0, value=int(p["stock"]), step=1)
                desc = st.text_area("Description", value=p["description"] or "")
                if st.form_submit_button("Update"):
                    db.update_product(sel, sku.strip(), name.strip(), cat_id, sup_id, cost, price, int(reorder), unit.strip() or "pcs", desc.strip())
                    if new_stock != p["stock"]:
                        db.update_stock(sel, int(new_stock))
                    st.success("Updated")
                    st.rerun()
    with tabs[3]:
        if not products:
            st.info("No products.")
        else:
            sel = st.selectbox("Select to delete", [r["id"] for r in products], format_func=lambda x: f"{next(r['sku'] for r in products if r['id']==x)} - {next(r['name'] for r in products if r['id']==x)}", key="delprod")
            if st.button("Delete", type="primary"):
                try:
                    db.delete_product(sel)
                    st.success("Deleted")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))


# ---------- Sales POS ----------
def page_sales():
    st.title("Sales (POS)")
    products = db.list_products()
    customers = db.list_customers()
    prod_map = {r["id"]: r for r in products}
    cust_map = {r["id"]: r for r in customers}

    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("Add item")
        if not products:
            st.info("No products. Add products first.")
        else:
            c1, c2, c3 = st.columns([3, 1, 1])
            pid = c1.selectbox("Product", [r["id"] for r in products], format_func=lambda x: f"{prod_map[x]['sku']} - {prod_map[x]['name']} (stock: {prod_map[x]['stock']})")
            qty = c2.number_input("Qty", min_value=1, value=1, step=1, key=f"sale_qty_{pid}")
            price = c3.number_input("Price", min_value=0.0, value=float(prod_map[pid]["price"]), step=0.01, format="%.2f", key=f"sale_price_{pid}")
            if st.button("Add to cart"):
                if qty > prod_map[pid]["stock"]:
                    st.error("Not enough stock")
                else:
                    st.session_state.sales_cart.append({"product_id": pid, "name": prod_map[pid]["name"], "qty": int(qty), "price": float(price)})
                    st.rerun()

        st.subheader("Cart")
        cart = st.session_state.sales_cart
        if cart:
            df = pd.DataFrame(cart)
            df["subtotal"] = df["qty"] * df["price"]
            st.dataframe(df[["name", "qty", "price", "subtotal"]], use_container_width=True, hide_index=True)
            # remove
            if st.button("Clear cart"):
                st.session_state.sales_cart = []
                st.rerun()
            # remove last? add index removal
            idx_to_remove = st.number_input("Remove item index (1-based)", min_value=0, max_value=len(cart), value=0, step=1)
            if idx_to_remove > 0 and st.button("Remove selected"):
                del st.session_state.sales_cart[idx_to_remove - 1]
                st.rerun()
        else:
            st.info("Cart is empty.")

    with col_right:
        st.subheader("Checkout")
        cust_options = [None] + [r["id"] for r in customers]
        customer_id = st.selectbox("Customer", cust_options, format_func=lambda x: "Walk-in" if x is None else cust_map[x]["name"])
        discount_pct = st.number_input("Discount %", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
        tax_rate = st.number_input("Tax %", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
        notes = st.text_area("Notes", height=60)
        cart = st.session_state.sales_cart
        if cart:
            subtotal = sum(i["qty"] * i["price"] for i in cart)
            discount = round(subtotal * discount_pct / 100.0, 2)
            tax = round((subtotal - discount) * tax_rate / 100.0, 2)
            grand = round(subtotal - discount + tax, 2)
            st.metric("Subtotal", money(subtotal))
            st.metric("Discount", money(discount))
            st.metric("Tax", money(tax))
            st.metric("Grand Total", money(grand))
            if st.button("Complete Sale", type="primary", use_container_width=True):
                # validate stock
                ok = True
                for i in cart:
                    p = prod_map[i["product_id"]]
                    if i["qty"] > p["stock"]:
                        ok = False
                        st.error(f"Insufficient stock for {p['name']}")
                        break
                if ok:
                    try:
                        sale_id, invoice, grand = db.create_sale(
                            customer_id, cart, discount_pct, tax_rate,
                            st.session_state.user["id"], notes.strip()
                        )
                        st.session_state.sales_cart = []
                        st.success(f"Sale completed: {invoice} — Total {money(grand)}")
                        # show invoice
                        sale = db.sale_detail(sale_id)
                        items = db.get_sale_items(sale_id)
                        st.session_state["last_sale_id"] = sale_id
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        else:
            st.info("Add items to cart.")

    # Invoice view
    last_id = st.session_state.get("last_sale_id")
    if last_id:
        st.divider()
        st.subheader("Last Invoice")
        sale = db.sale_detail(last_id)
        items = db.get_sale_items(last_id)
        if sale:
            st.write(f"Invoice: **{sale['invoice_no']}**  |  Date: {sale['sale_date']}")
            st.write(f"Customer: {sale['customer_name'] or 'Walk-in'}")
            df = pd.DataFrame([dict(r) for r in items])
            st.dataframe(df[["product_name", "sku", "qty", "price", "subtotal"]], use_container_width=True, hide_index=True)
            st.write(f"Subtotal: {money(sale['subtotal'])} | Discount: {money(sale['discount'])} | Tax: {money(sale['tax'])} | **Grand Total: {money(sale['grand_total'])}**")
            # download csv
            csv = df.to_csv(index=False)
            st.download_button("Download invoice (CSV)", csv, file_name=f"{sale['invoice_no']}.csv", mime="text/csv")
        if st.button("Dismiss invoice"):
            st.session_state.pop("last_sale_id", None)
            st.rerun()


# ---------- Purchases ----------
def page_purchases():
    st.title("Purchases (Restock)")
    products = db.list_products()
    suppliers = db.list_suppliers()
    prod_map = {r["id"]: r for r in products}

    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("Add item")
        if not products:
            st.info("No products.")
        else:
            c1, c2, c3 = st.columns([3, 1, 1])
            pid = c1.selectbox("Product", [r["id"] for r in products], format_func=lambda x: f"{prod_map[x]['sku']} - {prod_map[x]['name']}")
            qty = c2.number_input("Qty", min_value=1, value=1, step=1, key=f"pqty_{pid}")
            cost = c3.number_input("Unit cost", min_value=0.0, value=float(prod_map[pid]["cost"]), step=0.01, format="%.2f", key=f"pcost_{pid}")
            if st.button("Add to cart", key="padd"):
                st.session_state.purchase_cart.append({"product_id": pid, "name": prod_map[pid]["name"], "qty": int(qty), "cost": float(cost)})
                st.rerun()
        st.subheader("Cart")
        cart = st.session_state.purchase_cart
        if cart:
            df = pd.DataFrame(cart)
            df["subtotal"] = df["qty"] * df["cost"]
            st.dataframe(df[["name", "qty", "cost", "subtotal"]], use_container_width=True, hide_index=True)
            if st.button("Clear cart", key="pclear"):
                st.session_state.purchase_cart = []
                st.rerun()
            idx = st.number_input("Remove item index (1-based)", min_value=0, max_value=len(cart), value=0, step=1, key="premoveidx")
            if idx > 0 and st.button("Remove selected", key="premove"):
                del st.session_state.purchase_cart[idx - 1]
                st.rerun()
        else:
            st.info("Cart is empty.")

    with col_right:
        st.subheader("Receive")
        sup_options = [None] + [r["id"] for r in suppliers]
        sup_map = {r["id"]: r for r in suppliers}
        supplier_id = st.selectbox("Supplier", sup_options, format_func=lambda x: "None" if x is None else sup_map[x]["name"])
        notes = st.text_area("Notes", height=60, key="pnotes")
        cart = st.session_state.purchase_cart
        if cart:
            total = sum(i["qty"] * i["cost"] for i in cart)
            st.metric("Total", money(total))
            if st.button("Receive Purchase", type="primary", use_container_width=True):
                try:
                    pur_id, po, total = db.create_purchase(
                        supplier_id, cart, st.session_state.user["id"], notes.strip()
                    )
                    st.session_state.purchase_cart = []
                    st.success(f"Purchase received: {po} — Total {money(total)}")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        else:
            st.info("Add items to cart.")

    st.divider()
    st.subheader("Recent purchases")
    rows = db.list_purchases(50)
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        st.dataframe(df[["id", "po_no", "supplier_name", "purchase_date", "subtotal", "status"]], use_container_width=True, hide_index=True)
        sel = st.selectbox("View items", [r["id"] for r in rows], format_func=lambda x: next(r["po_no"] for r in rows if r["id"] == x), key="pview")
        items = db.get_purchase_items(sel)
        if items:
            idf = pd.DataFrame([dict(r) for r in items])
            st.dataframe(idf[["product_name", "sku", "qty", "cost", "subtotal"]], use_container_width=True, hide_index=True)


# ---------- Reports ----------
def page_reports():
    st.title("Reports")
    tab1, tab2, tab3 = st.tabs(["Sales Report", "Inventory Report", "Stock Movements"])
    with tab1:
        c1, c2 = st.columns(2)
        start = c1.date_input("Start date", value=date.today() - timedelta(days=30))
        end = c2.date_input("End date", value=date.today())
        rows = db.list_sales(10000)
        if rows:
            df = pd.DataFrame([dict(r) for r in rows])
            df["sale_date"] = pd.to_datetime(df["sale_date"])
            mask = (df["sale_date"].dt.date >= start) & (df["sale_date"].dt.date <= end)
            fdf = df[mask]
            st.metric("Orders", len(fdf))
            st.metric("Revenue", money(fdf["grand_total"].sum() if len(fdf) else 0))
            st.dataframe(fdf[["invoice_no", "customer_name", "sale_date", "subtotal", "discount", "tax", "grand_total", "status"]], use_container_width=True, hide_index=True)
            csv = fdf.to_csv(index=False)
            st.download_button("Export CSV", csv, file_name="sales_report.csv", mime="text/csv")
        else:
            st.info("No sales.")
    with tab2:
        products = db.list_products()
        if products:
            df = pd.DataFrame([dict(r) for r in products])
            df["stock_value_cost"] = df["stock"] * df["cost"]
            df["stock_value_price"] = df["stock"] * df["price"]
            st.dataframe(df[["sku", "name", "category_name", "stock", "cost", "price", "stock_value_cost", "stock_value_price", "reorder_level"]], use_container_width=True, hide_index=True)
            st.metric("Total stock value (cost)", money(df["stock_value_cost"].sum()))
            st.metric("Total stock value (retail)", money(df["stock_value_price"].sum()))
            csv = df.to_csv(index=False)
            st.download_button("Export CSV", csv, file_name="inventory_report.csv", mime="text/csv")
        else:
            st.info("No products.")
    with tab3:
        conn = db.get_conn()
        rows = conn.execute("""
            SELECT sm.*, p.name AS product_name, p.sku, u.username
            FROM stock_movements sm
            JOIN products p ON sm.product_id=p.id
            LEFT JOIN users u ON sm.user_id=u.id
            ORDER BY sm.id DESC LIMIT 500
        """).fetchall()
        conn.close()
        if rows:
            df = pd.DataFrame([dict(r) for r in rows])
            st.dataframe(df[["movement_date", "product_name", "sku", "movement_type", "qty", "reference", "username"]], use_container_width=True, hide_index=True)
        else:
            st.info("No movements.")


# ---------- Stock Movements page (dedicated) ----------
def page_stock_movements():
    st.title("Stock Movements")
    conn = db.get_conn()
    rows = conn.execute("""
        SELECT sm.*, p.name AS product_name, p.sku, u.username
        FROM stock_movements sm JOIN products p ON sm.product_id=p.id
        LEFT JOIN users u ON sm.user_id=u.id
        ORDER BY sm.id DESC LIMIT 1000
    """).fetchall()
    conn.close()
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        st.dataframe(df[["id", "movement_date", "product_name", "sku", "movement_type", "qty", "reference", "username"]], use_container_width=True, hide_index=True)
    else:
        st.info("No movements yet.")


# ---------- Users ----------
def page_users():
    st.title("Users")
    users = db.list_users()
    df = pd.DataFrame([dict(r) for r in users])
    st.dataframe(df[["id", "username", "role", "full_name", "created_at"]], use_container_width=True, hide_index=True)
    with st.expander("Add user"):
        with st.form("add_user"):
            username = st.text_input("Username")
            full_name = st.text_input("Full name")
            role = st.selectbox("Role", ["staff", "admin"])
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Create"):
                if username.strip() and password:
                    import hashlib, secrets
                    salt, pw = db.hash_password(password)
                    conn = db.get_conn()
                    try:
                        conn.execute("INSERT INTO users(username,password,role,full_name,created_at) VALUES(?,?,?,?,?)",
                                     (username.strip(), pw, role, full_name.strip(), db.now_str()))
                        conn.commit()
                        st.success("User created")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
                    finally:
                        conn.close()
                else:
                    st.error("Username and password required")


# ---------- main ----------
def main():
    if st.session_state.user is None:
        show_login()
        return
    sidebar()
    page = st.session_state.page
    {
        "Dashboard": page_dashboard,
        "Products": page_products,
        "Categories": page_categories,
        "Suppliers": page_suppliers,
        "Customers": page_customers,
        "Sales (POS)": page_sales,
        "Purchases": page_purchases,
        "Reports": page_reports,
        "Stock Movements": page_stock_movements,
        "Users": page_users,
    }[page]()


if __name__ == "__main__":
    main()