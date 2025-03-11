# Add this code temporarily to your main.py or run it in a Python script
from models import Order, db
import datetime

# Connect to the database
db.connect()

# Get all orders
all_orders = Order.select()

# Filter for Sunday production dates in Python
sunday_orders = [order for order in all_orders if order.production_date.weekday() == 6]  # 6 = Sunday

# Print the results
print(f"Found {len(sunday_orders)} orders with Sunday production dates:")
for order in sunday_orders:
    print(f"Order ID: {order.id}, Production Date: {order.production_date}, Customer: {order.customer.name}")

# Close the database connection
db.close()