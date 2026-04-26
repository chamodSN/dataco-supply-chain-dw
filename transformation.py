"""
DataCo Supply Chain – Data Source Preparation
IT3021 Data Warehousing & Business Intelligence – Assignment 1

Tables produced (matching the ER diagram exactly):
  CSV  : customers.csv, customer_addresses.csv, order_items.csv,
          orders.csv, order_addresses.csv, shipments.csv
  CSV  : products.csv, categories.csv, departments.csv
  TXT  : customers_txt.txt   (pipe-delimited – second source type for SSIS)
  SQL  : supply_chain.sql    (CREATE TABLE + bulk INSERT for SSMS import)
"""

import pandas as pd
import random
import re
import os

# ── CONFIG ───────────────────────────────────────────────────────────────────
INPUT_FILE = "DataCoSupplyChainDataset.csv"
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
random.seed(42)

# ── STEP 0 – LOAD ─────────────────────────────────────────────────────────
print("Loading dataset …")
df = pd.read_csv(INPUT_FILE, encoding="latin-1")
print(f"  Loaded {len(df):,} rows × {len(df.columns)} columns")

# ── STEP 1 – RENAME ALL COLUMNS (permanent) ──────────────────────────────
df.columns = [
    "transaction_type",           # 0
    "actual_shipping_days",       # 1
    "scheduled_shipping_days",    # 2
    "order_profit",               # 3  (Benefit per order)
    "customer_total_sales",       # 4
    "delivery_status",            # 5
    "late_delivery_risk",         # 6
    "category_id",                # 7
    "category_name",              # 8
    "customer_city",              # 9
    "customer_country",           # 10
    "customer_email",             # 11
    "customer_first_name",        # 12
    "customer_id",                # 13
    "customer_last_name",         # 14
    "customer_password",          # 15
    "customer_segment",           # 16
    "customer_state",             # 17
    "customer_street",            # 18
    "customer_zipcode",           # 19
    "department_id",              # 20
    "department_name",            # 21
    "store_latitude",             # 22
    "store_longitude",            # 23
    "market",                     # 24
    "order_city",                 # 25
    "order_country",              # 26
    "order_customer_id",          # 27
    "order_date",                 # 28
    "order_id",                   # 29
    "product_id_rfid",            # 30
    "order_item_discount",        # 31
    "order_item_discount_rate",   # 32
    "order_item_id",              # 33
    "product_price_before_discount",  # 34
    "order_item_profit_ratio",    # 35
    "order_item_quantity",        # 36
    "sales_amount",               # 37
    "order_item_total",           # 38
    "order_profit_per_order",     # 39
    "order_region",               # 40
    "order_state",                # 41
    "order_status",               # 42
    "order_zipcode",              # 43
    "product_card_id",            # 44
    "product_category_id",        # 45
    "product_description",        # 46
    "product_image_url",          # 47
    "product_name",               # 48
    "product_price",              # 49
    "product_status",             # 50
    "shipping_date",              # 51
    "shipping_mode",              # 52
]
print("  All columns renamed.")

# ── TASK 3 – GENERATE CUSTOMER EMAILS ────────────────────────────────────
print("\nTask 3 – Generating customer emails …")

cust_unique = df.drop_duplicates(subset=["customer_id"]).copy()

name_counts = (
    cust_unique["customer_first_name"].str.lower().str.strip()
    + "_"
    + cust_unique["customer_last_name"].str.lower().str.strip()
).value_counts()

counter_store: dict[str, int] = {}


def make_email(fname: str, lname: str, name_key: str) -> str:
    fname = fname.strip().lower().replace(" ", "")
    lname = lname.strip().lower().replace(" ", "")
    base = (
        f"{lname}.{fname}"
        if name_counts.get(name_key, 0) > 1
        else f"{fname}.{lname}"
    )
    if base not in counter_store:
        counter_store[base] = 0
        return f"{base}@gmail.com"
    counter_store[base] += 1
    return f"{base}{counter_store[base]}@gmail.com"


emails_map: dict = {}
for _, row in cust_unique.iterrows():
    cid = row["customer_id"]
    fname = str(row["customer_first_name"])
    lname = str(row["customer_last_name"])
    segment = str(row["customer_segment"]).strip()
    name_key = fname.lower().strip() + "_" + lname.lower().strip()

    if segment in ("Corporate", "Home Office"):
        emails_map[cid] = make_email(fname, lname, name_key)
    elif segment == "Consumer":
        emails_map[cid] = (
            make_email(fname, lname, name_key) if random.random() < 0.40 else ""
        )
    else:
        emails_map[cid] = ""

# Map back – every row for the same customer_id gets the identical email
df["customer_email"] = df["customer_id"].map(emails_map).fillna("")
assigned = sum(1 for v in emails_map.values() if v)
print(f"  Emails assigned to {assigned:,} unique customers.")

# ── TASK 4 – SPLIT CUSTOMER STREET ──────────────────────────────────────
print("\nTask 4 – Splitting customer_street …")


def split_street(address):
    if pd.isna(address) or str(address).strip() == "":
        return "", ""
    address = str(address).strip()
    m = re.match(r"^(\d+[A-Za-z]?)\s+(.+)$", address)
    if m:
        return m.group(2).strip(), m.group(1).strip()
    m = re.match(r"^(.+?)\s+(\d+[A-Za-z]?)$", address)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return address, ""


split_result = df["customer_street"].apply(
    lambda x: pd.Series(split_street(x)))
df["customer_street_name"] = split_result[0]
df["customer_house_number"] = split_result[1]
df.drop(columns=["customer_street"], inplace=True)
print("  customer_street → customer_street_name + customer_house_number")

# ── TASK 5 – DATE FORMAT VARIATION ──────────────────────────────────────
print("\nTask 5 – Reformatting order dates …")

df["order_date"] = pd.to_datetime(df["order_date"], format="%m/%d/%Y %H:%M")
df["_year"] = df["order_date"].dt.year


def format_date(row):
    dt, yr = row["order_date"], row["_year"]
    if yr == 2015:
        return dt.strftime("%m/%d/%Y %H:%M")   # MM/DD/YYYY HH:MM
    elif yr == 2016:
        return dt.strftime("%m/%d/%y %H:%M")    # MM/DD/YY  HH:MM
    else:
        return dt.strftime("%d/%m/%Y %H:%M")    # DD/MM/YYYY HH:MM


df["order_date_formatted"] = df.apply(format_date, axis=1)
df.drop(columns=["_year"], inplace=True)
print("  2015 → MM/DD/YYYY | 2016 → MM/DD/YY | 2017+ → DD/MM/YYYY")

# Parse shipping_date as datetime for later use
df["shipping_date"] = pd.to_datetime(df["shipping_date"], errors="coerce")


# ═══════════════════════════════════════════════════════════════════════════
#  OUTPUT TABLES  (all matching the ER diagram)
# ═══════════════════════════════════════════════════════════════════════════

print("\nWriting output files …")

# ── 1. CUSTOMER (CSV) ─────────────────────────────────────────────────────
#  ER: customer_id, customer_first_name, customer_last_name,
#      customer_email, customer_segment, customer_password
customers = (
    df[[
        "customer_id", "customer_first_name", "customer_last_name",
        "customer_email", "customer_segment", "customer_password",
    ]]
    .drop_duplicates(subset=["customer_id"])
    .sort_values("customer_id")
    .reset_index(drop=True)
)
customers.to_csv(f"{OUTPUT_DIR}/customers.csv", index=False)
print(f"  customers.csv            – {len(customers):,} rows")

# ── 2. CUSTOMER_ADDRESS (TXT) ────────────────────────────────────────────
#  ER: customer_id, customer_street_name, customer_house_number,
#      customer_city, customer_zipcode, customer_state, customer_country
customer_addresses = (
    df[[
        "customer_id", "customer_street_name", "customer_house_number",
        "customer_city", "customer_zipcode",
        "customer_state", "customer_country",
    ]]
    .drop_duplicates(subset=["customer_id"])
    .sort_values("customer_id")
    .reset_index(drop=True)
)
customer_addresses.to_csv(
    f"{OUTPUT_DIR}/customer_addresses.txt", index=False, sep="|")
print(f"  customer_addresses.txt   – pipe-delimited (TXT source)")

# ── 3. DEPARTMENT (CSV) ──────────────────────────────────────────────────
#  ER: department_id, department_name, store_latitude, store_longitude
departments = (
    df[["department_id", "department_name", "store_latitude", "store_longitude"]]
    .drop_duplicates(subset=["department_id"])
    .sort_values("department_id")
    .reset_index(drop=True)
)
departments.to_csv(f"{OUTPUT_DIR}/departments.csv", index=False)
print(f"  departments.csv          – {len(departments):,} rows")

# ── 4. CATEGORY (CSV) ────────────────────────────────────────────────────
#  ER: category_id, category_name   (+FK department_id shown via PRODUCT→CATEGORY)
#  The ER places department_id linkage through CATEGORY, so we keep dept link here.
categories = (
    df[["category_id", "category_name", "department_id"]]
    .drop_duplicates(subset=["category_id"])
    .sort_values("category_id")
    .reset_index(drop=True)
)
categories.to_csv(f"{OUTPUT_DIR}/categories.csv", index=False)
print(f"  categories.csv           – {len(categories):,} rows")

# ── 5. PRODUCT (CSV) ─────────────────────────────────────────────────────
#  ER: Product_Card_Id (PK), category_id (FK), product_name, product_price,
#      product_status, product_image_url, product_description
products = (
    df[[
        "product_card_id", "category_id",
        "product_name", "product_price", "product_status",
        "product_image_url", "product_description",
    ]]
    .drop_duplicates(subset=["product_card_id"])
    .sort_values("product_card_id")
    .reset_index(drop=True)
)
products.to_csv(f"{OUTPUT_DIR}/products.csv", index=False)
print(f"  products.csv             – {len(products):,} rows")

# ── 6. ORDER (CSV) ───────────────────────────────────────────────────────
#  ER: order_id, order_customer_id, order_date, order_status,
#      transaction_type, order_profit, sales_amount, customer_total_sales
orders = (
    df[[
        "order_id", "order_customer_id", "order_date_formatted",
        "order_status", "transaction_type", "order_profit",
        "sales_amount", "customer_total_sales",
    ]]
    .drop_duplicates(subset=["order_id"])
    .sort_values("order_id")
    .reset_index(drop=True)
    .rename(columns={"order_date_formatted": "order_date"})
)
orders.to_csv(f"{OUTPUT_DIR}/orders.csv", index=False)
print(f"  orders.csv               – {len(orders):,} rows")

# ── 7. ORDER_ADDRESS (CSV) ───────────────────────────────────────────────
#  ER: order_id (PK), order_city, order_country, order_region, order_state, market
order_addresses = (
    df[[
        "order_id", "order_city", "order_country",
        "order_region", "order_state", "order_zipcode", "market",
    ]]
    .drop_duplicates(subset=["order_id"])
    .sort_values("order_id")
    .reset_index(drop=True)
)
order_addresses.to_csv(
    f"{OUTPUT_DIR}/order_addresses.txt", index=False, sep="|")
print(f"  order_addresses.txt      – pipe-delimited (TXT source)")

# ── 8. ORDER_ITEM (CSV) ──────────────────────────────────────────────────
#  ER: order_item_id (PK), order_Id (FK), product_id_rfid (FK),
#      order_item_quantity, order_item_discount, order_item_discount_rate,
#      product_price_before_discount, order_item_profit_ratio,
#      order_item_total, order_profit_per_order
order_items = df[[
    "order_item_id", "order_id", "product_id_rfid",
    "order_item_quantity", "order_item_discount", "order_item_discount_rate",
    "product_price_before_discount", "order_item_profit_ratio",
    "order_item_total", "order_profit_per_order",
]].copy()
# ── ORDER_ITEMS EXCEL (third source type for SSIS) ───────────────────
order_items.to_excel(f"{OUTPUT_DIR}/order_items.xlsx",
                     index=False, sheet_name="OrderItems")
print(f"  order_items.xlsx         – Excel (3rd source type for SSIS)")

# ── 9. SHIPMENT (CSV) ────────────────────────────────────────────────────
#  ER: Order_Id (FK), shipping_mode, actual_shipping_days,
#      scheduled_shipping_days, delivery_status, late_delivery_risk, shipping_date
shipments = (
    df[[
        "order_id", "shipping_mode",
        "actual_shipping_days", "scheduled_shipping_days",
        "delivery_status", "late_delivery_risk", "shipping_date",
    ]]
    .drop_duplicates(subset=["order_id"])
    .sort_values("order_id")
    .reset_index(drop=True)
)
shipments.to_csv(f"{OUTPUT_DIR}/shipments.csv", index=False)
print(f"  shipments.csv            – {len(shipments):,} rows")

# ═══════════════════════════════════════════════════════════════════════════
#  SQL SCRIPT for SSMS import  (CREATE TABLE + data)
# ═══════════════════════════════════════════════════════════════════════════
print("\nGenerating SQL script for SSMS …")

SQL_HEADER = """\

USE master;
GO
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'DataCoSupplyChain')
    CREATE DATABASE DataCoSupplyChain;
GO
USE DataCoSupplyChain;
GO

-- ──────────────────────────────────────────────────────────
-- 1. DEPARTMENT
-- ──────────────────────────────────────────────────────────
IF OBJECT_ID('dbo.Department', 'U') IS NOT NULL DROP TABLE dbo.Department;
CREATE TABLE dbo.Department (
    department_id      INT           NOT NULL PRIMARY KEY,
    department_name    NVARCHAR(100) NOT NULL,
    store_latitude     FLOAT,
    store_longitude    FLOAT
);

-- ──────────────────────────────────────────────────────────
-- 2. CATEGORY
-- ──────────────────────────────────────────────────────────
IF OBJECT_ID('dbo.Category', 'U') IS NOT NULL DROP TABLE dbo.Category;
CREATE TABLE dbo.Category (
    category_id    INT           NOT NULL PRIMARY KEY,
    category_name  NVARCHAR(100) NOT NULL,
    department_id  INT           NOT NULL,
    CONSTRAINT FK_Category_Department FOREIGN KEY (department_id)
        REFERENCES dbo.Department (department_id)
);

-- ──────────────────────────────────────────────────────────
-- 3. PRODUCT
-- ──────────────────────────────────────────────────────────
IF OBJECT_ID('dbo.Product', 'U') IS NOT NULL DROP TABLE dbo.Product;
CREATE TABLE dbo.Product (
    product_card_id    INT             NOT NULL PRIMARY KEY,
    category_id        INT             NOT NULL,
    product_name       NVARCHAR(200)   NOT NULL,
    product_price      DECIMAL(10,2),
    product_status     TINYINT,
    product_image_url  NVARCHAR(500),
    product_description NVARCHAR(MAX),
    CONSTRAINT FK_Product_Category FOREIGN KEY (category_id)
        REFERENCES dbo.Category (category_id)
);

-- ──────────────────────────────────────────────────────────
-- 4. CUSTOMER
-- ──────────────────────────────────────────────────────────
IF OBJECT_ID('dbo.Customer', 'U') IS NOT NULL DROP TABLE dbo.Customer;
CREATE TABLE dbo.Customer (
    customer_id          INT           NOT NULL PRIMARY KEY,
    customer_first_name  NVARCHAR(100),
    customer_last_name   NVARCHAR(100),
    customer_email       NVARCHAR(200),
    customer_segment     NVARCHAR(50),
    customer_password    NVARCHAR(200)
);

-- ──────────────────────────────────────────────────────────
-- 6. [ORDER]  (ORDER is a reserved word – use brackets)
-- ──────────────────────────────────────────────────────────
IF OBJECT_ID('dbo.[Order]', 'U') IS NOT NULL DROP TABLE dbo.[Order];
CREATE TABLE dbo.[Order] (
    order_id            INT             NOT NULL PRIMARY KEY,
    order_customer_id   INT             NOT NULL,
    order_date          NVARCHAR(20),   -- mixed formats preserved for ETL
    order_status        NVARCHAR(50),
    transaction_type    NVARCHAR(50),
    order_profit        DECIMAL(12,4),
    sales_amount        DECIMAL(12,4),
    customer_total_sales DECIMAL(12,4),
    CONSTRAINT FK_Order_Customer FOREIGN KEY (order_customer_id)
        REFERENCES dbo.Customer (customer_id)
);

-- ──────────────────────────────────────────────────────────
-- 9. SHIPMENT
-- ──────────────────────────────────────────────────────────
IF OBJECT_ID('dbo.Shipment', 'U') IS NOT NULL DROP TABLE dbo.Shipment;
CREATE TABLE dbo.Shipment (
    order_id                INT          NOT NULL PRIMARY KEY,
    shipping_mode           NVARCHAR(50),
    actual_shipping_days    INT,
    scheduled_shipping_days INT,
    delivery_status         NVARCHAR(50),
    late_delivery_risk      TINYINT,
    shipping_date           DATETIME,
    CONSTRAINT FK_Shipment_Order FOREIGN KEY (order_id)
        REFERENCES dbo.[Order] (order_id)
);

-- ──────────────────────────────────────────────────────────
-- BULK INSERT STUBS
-- Update the file paths below to match where you placed
-- the CSV files on your SQL Server machine.
-- ──────────────────────────────────────────────────────────
/*
BULK INSERT dbo.Department
FROM 'E:\\SLIIT\\Y3S2\\DW & BI\\Assignment 1\\output\\departments.csv'
WITH (FIRSTROW=2, FIELDTERMINATOR=',', ROWTERMINATOR='\\n', TABLOCK);

BULK INSERT dbo.Category
FROM 'E:\\SLIIT\\Y3S2\\DW & BI\\Assignment 1\\output\\categories.csv'
WITH (FIRSTROW=2, FIELDTERMINATOR=',', ROWTERMINATOR='\\n', TABLOCK);

BULK INSERT dbo.Product
FROM 'E:\\SLIIT\\Y3S2\\DW & BI\\Assignment 1\\output\\products.csv'
WITH (FIRSTROW=2, FIELDTERMINATOR=',', ROWTERMINATOR='\\n', TABLOCK);

BULK INSERT dbo.Customer
FROM 'E:\\SLIIT\\Y3S2\\DW & BI\\Assignment 1\\output\\customers.csv'
WITH (FIRSTROW=2, FIELDTERMINATOR=',', ROWTERMINATOR='\\n', TABLOCK);

BULK INSERT dbo.[Order]
FROM 'E:\\SLIIT\\Y3S2\\DW & BI\\Assignment 1\\output\\orders.csv'
WITH (FIRSTROW=2, FIELDTERMINATOR=',', ROWTERMINATOR='\\n', TABLOCK);

BULK INSERT dbo.Shipment
FROM 'E:\\SLIIT\\Y3S2\\DW & BI\\Assignment 1\\output\\shipments.csv'
WITH (FIRSTROW=2, FIELDTERMINATOR=',', ROWTERMINATOR='\\n', TABLOCK);
*/

PRINT 'DataCoSupplyChain staging database created successfully.';
GO
"""

with open(f"{OUTPUT_DIR}/supply_chain.sql", "w", encoding="utf-8") as f:
    f.write(SQL_HEADER)
print(f"  supply_chain.sql         – CREATE TABLE + BULK INSERT stubs")

# ── SUMMARY ──────────────────────────────────────────────────────────────
print("\n✅  Done!  All files written to ./output/")
print("""
┌─────────────────────────────────┬──────────────┬──────────────────────────────────┐
│  File                           │  Format      │  SSIS Source Type                │
├─────────────────────────────────┼──────────────┼──────────────────────────────────┤
│  customers.csv                  │  CSV         │  Flat File Source                │
│  customers_txt.txt              │  TXT (pipe)  │  Flat File Source (2nd type)     │
│  customer_addresses.csv         │  CSV         │  Flat File Source                │
│  departments.csv                │  CSV         │  Flat File Source                │
│  categories.csv                 │  CSV         │  Flat File Source                │
│  products.csv                   │  CSV         │  Flat File Source                │
│  orders.csv                     │  CSV         │  Flat File Source                │
│  order_addresses.csv            │  CSV         │  Flat File Source                │
│  order_items.csv                │  CSV         │  Flat File Source                │
│  shipments.csv                  │  CSV         │  Flat File Source                │
│  supply_chain.sql               │  SQL Script  │  Run in SSMS → then use OLE DB  │
└─────────────────────────────────┴──────────────┴──────────────────────────────────┘
""")
