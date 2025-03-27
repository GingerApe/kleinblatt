#!/usr/bin/env python3
import os
import sqlite3
from datetime import datetime

print("Script to delete all single (non-subscription) orders")
print("====================================================")

# Connect to the database
db_path = 'production.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# First, let's see how many single orders we have
cursor.execute("""
    SELECT COUNT(*) 
    FROM "order" 
    WHERE subscription_type = 0
""")
count = cursor.fetchone()[0]
print(f"Found {count} single orders to delete")

# Create a backup of the database before making changes
backup_name = f"production_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
print(f"Creating database backup: {backup_name}")

# Close the connection to make a clean copy
conn.close()

# Create backup using the operating system's copy command
import shutil
shutil.copy2(db_path, backup_name)
print("Backup completed")

# Reconnect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# First delete related order items (foreign key constraint)
print("Deleting order items for single orders...")
cursor.execute("""
    DELETE FROM orderitem
    WHERE order_id IN (
        SELECT id FROM "order" WHERE subscription_type = 0
    )
""")
items_deleted = cursor.rowcount
print(f"Deleted {items_deleted} order items")

# Now delete the single orders
print("Deleting single orders...")
cursor.execute("""
    DELETE FROM "order" 
    WHERE subscription_type = 0
""")
orders_deleted = cursor.rowcount
print(f"Deleted {orders_deleted} orders")

# Commit the changes
conn.commit()
conn.close()

print("\nOperation completed successfully!")
print(f"Database backup saved as: {backup_name}")
print(f"Total items deleted: {items_deleted}")
print(f"Total orders deleted: {orders_deleted}") 