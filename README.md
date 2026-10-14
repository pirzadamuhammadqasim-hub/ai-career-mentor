# Inventory & Sales Management System

A professional web app built with **Python, Streamlit, SQLite, and Pandas** for managing inventory, sales, purchases, customers, suppliers, and reports.

## Features
- Secure login (admin / staff roles)
- Dashboard with KPIs, low-stock alerts, top products, sales trend
- Product & inventory management with reorder levels
- Categories, Suppliers, Customers CRUD
- Sales POS with cart, discounts, tax, invoices, CSV export
- Purchases / restocking with automatic stock updates
- Stock movement tracking
- Reports: sales, inventory valuation, stock movements
- SQLite persistence, input validation, transactional integrity

## Setup
```bash
cd Class1
pip install -r requirements.txt
streamlit run app.py
```

## Default accounts
- `admin` / `admin123`
- `staff` / `staff123`

Database file `inventory.db` is created automatically on first run.