import csv
import os
import sqlite3
from collections import Counter

# Set up paths relative to where this script is saved
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'shipment_database.db')
CSV_0_PATH = os.path.join(BASE_DIR, 'data', 'shipping_data_0.csv')
CSV_1_PATH = os.path.join(BASE_DIR, 'data', 'shipping_data_1.csv')
CSV_2_PATH = os.path.join(BASE_DIR, 'data', 'shipping_data_2.csv')


def get_or_create_product_id(cursor, product_name):
    """
    Checks if a product exists in the 'product' table.
    If it does, returns its ID; if not, inserts it and returns the new ID.
    """
    cursor.execute("SELECT id FROM product WHERE name = ?", (product_name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    cursor.execute("INSERT INTO product (name) VALUES (?)", (product_name,))
    return cursor.lastrowid


def populate():
    # 1. Establish database connection and cursor
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # Step 1: Ingest shipping_data_0.csv (self-contained)
    # ---------------------------------------------------------
    print("Processing shipping_data_0.csv...")
    with open(CSV_0_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prod_name = row['product']
            origin = row['origin_warehouse']
            destination = row['destination_store']
            quantity = int(row['product_quantity'])

            prod_id = get_or_create_product_id(cursor, prod_name)

            cursor.execute("""
                INSERT INTO shipment (product_id, quantity, origin, destination)
                VALUES (?, ?, ?, ?)
            """, (prod_id, quantity, origin, destination))

    # ---------------------------------------------------------
    # Step 2: Read origin & destination from shipping_data_2.csv
    # ---------------------------------------------------------
    print("Reading shipping_data_2.csv...")
    shipment_locations = {}
    with open(CSV_2_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            shipment_id = row['shipment_identifier']
            shipment_locations[shipment_id] = {
                'origin': row['origin_warehouse'],
                'destination': row['destination_store']
            }

    # ---------------------------------------------------------
    # Step 3: Aggregate item quantities from shipping_data_1.csv
    # ---------------------------------------------------------
    print("Aggregating shipping_data_1.csv...")
    # Count occurrences of (shipment_identifier, product)
    item_counts = Counter()
    with open(CSV_1_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_counts[(row['shipment_identifier'], row['product'])] += 1

    # ---------------------------------------------------------
    # Step 4: Insert aggregated records into shipment table
    # ---------------------------------------------------------
    print("Inserting aggregated records into database...")
    for (shipment_id, prod_name), quantity in item_counts.items():
        if shipment_id in shipment_locations:
            origin = shipment_locations[shipment_id]['origin']
            destination = shipment_locations[shipment_id]['destination']

            prod_id = get_or_create_product_id(cursor, prod_name)

            cursor.execute("""
                INSERT INTO shipment (product_id, quantity, origin, destination)
                VALUES (?, ?, ?, ?)
            """, (prod_id, quantity, origin, destination))

    # 2. Commit transaction and close connection
    conn.commit()
    conn.close()
    print("Database population finished successfully!")


if __name__ == '__main__':
    populate()