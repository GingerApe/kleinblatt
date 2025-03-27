import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta, date
from models import Item, Order, Customer, OrderItem, db
from database import calculate_production_date, generate_subscription_orders, get_delivery_schedule, get_production_plan, get_transfer_schedule
from peewee import fn, JOIN
import uuid
from weekly_view import WeeklyDeliveryView, WeeklyProductionView, WeeklyTransferView
from customers_view import CustomerView
from item_view import ItemView
from widgets import AutocompleteCombobox
from print_schedules import SchedulePrinter, ask_week_selection
import os

# Function to check for production orders on Sundays
def check_sunday_production():
    """
    Check if there are any orders scheduled for production on Sundays.
    This is a diagnostic function to help understand why Sundays might 
    not show up in the production plan.
    """
    try:
        # Get all orders
        all_orders = Order.select()
        
        # Filter for Sunday production dates
        sunday_orders = [order for order in all_orders if order.production_date.weekday() == 6]  # 6 = Sunday
        
        if sunday_orders:
            messagebox.showinfo(
                "Sunday Production Found", 
                f"Found {len(sunday_orders)} orders with Sunday production dates.\n" +
                f"First example: Order ID {sunday_orders[0].id}, " +
                f"Production Date: {sunday_orders[0].production_date}, " +
                f"Customer: {sunday_orders[0].customer.name}"
            )
        else:
            messagebox.showinfo(
                "No Sunday Production", 
                "No orders with Sunday production dates were found in the database.\n" +
                "This explains why no production entries appear on Sundays."
            )
    except Exception as e:
        messagebox.showerror("Error", f"Error checking Sunday production: {str(e)}")

class ProductionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Production Tracker")
        self.geometry("1400x800")
        
        self.db = db
        self.printer = SchedulePrinter()

        style = ttk.Style()
        style.configure('Green.TFrame', background='green')

        # Create main notebook
        self.notebook = ttk.Notebook(self)
        self.tab1 = ttk.Frame(self.notebook)  # New Order
        self.tab2 = ttk.Frame(self.notebook)  # Delivery Schedule
        self.tab3 = ttk.Frame(self.notebook)  # Production Plan
        self.tab4 = ttk.Frame(self.notebook)  # Transfer Schedule
        self.tab5 = ttk.Frame(self.notebook)  # Customers
        self.tab6 = ttk.Frame(self.notebook)  # Items  # Add this line
        self.tab7 = ttk.Frame(self.notebook)  # Orders

        #self.notebook.add(self.tab1, text="Bestellung")
        self.notebook.add(self.tab2, text="Lieferung")
        self.notebook.add(self.tab3, text="Produktion")
        self.notebook.add(self.tab4, text="Transfer")
        self.notebook.add(self.tab5, text="Kunden")
        self.notebook.add(self.tab6, text="Items")
        self.notebook.add(self.tab7, text="Bestellungen")
        
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        self.load_data()
        self.create_order_tab()
        self.create_delivery_tab()
        self.create_production_tab()
        self.create_transfer_tab()
        self.create_customers_tab()
        self.create_items_tab()
        self.create_orders_tab()

            # Add these lines to refresh data when app starts
        if hasattr(self, 'delivery_view'):
            self.delivery_view.refresh()
        if hasattr(self, 'production_view'):
            self.production_view.refresh()
        if hasattr(self, 'transfer_view'):
            self.transfer_view.refresh()

    # Add this method
    def create_items_tab(self):
        self.item_view = ItemView(self.tab6)
    
    def load_customers(self):
        # Fetch customers sorted by order count with total price calculation
        customers = (Customer
                    .select(Customer, 
                            fn.COUNT(Order.id).alias('order_count'),
                            fn.SUM(OrderItem.amount * Item.price).alias('total_price'))
                    .join(Order, JOIN.LEFT_OUTER)
                    .join(OrderItem, JOIN.LEFT_OUTER)
                    .join(Item, JOIN.LEFT_OUTER)
                    .where(Order.is_future == False)  # Only include historical orders
                    .group_by(Customer)
                    .order_by(fn.COUNT(Order.id).desc()))
        
        for customer in customers:
            # Format the total price as currency or show €0.00 if None
            total_price = f"€{customer.total_price:.2f}" if customer.total_price else "€0,00"
            self.customer_tree.insert('', 'end', values=(customer.name, customer.order_count, total_price.replace('.',',')))
            
    # Modify refresh_tables method to include items
    def refresh_tables(self):
        """Refresh all weekly views"""
        if hasattr(self, 'delivery_view'):
            self.delivery_view.refresh()
        if hasattr(self, 'production_view'):
            self.production_view.refresh()
        if hasattr(self, 'transfer_view'):
            self.transfer_view.refresh()
        if hasattr(self, 'customer_view'):
            self.customer_view.load_customers()
        if hasattr(self, 'item_view'):  # Add this block
            self.item_view.refresh_item_list()
        
        self.after(5000, self.refresh_tables)
        
    def load_data(self):
        self.items = {item.name: item for item in Item.select()}
        self.customers = {customer.name: customer for customer in Customer.select()}
        self.order_items = []  # List to store items for current order
    
    def on_customer_select(self, event):
        selected_item = self.customer_tree.selection()
        if not selected_item:
            return
        
        customer_name = self.customer_tree.item(selected_item, 'values')[0]
        customer = self.customers[customer_name]
        
        # Clear previous orders
        for item in self.order_tree.get_children():
            self.order_tree.delete(item)
        
        # Fetch and display orders for the selected customer
        today = datetime.now().date()
        orders = (Order
                .select()
                .where(
                    (Order.customer == customer) &
                    (Order.delivery_date <= today)
                    )
                .group_by(Order.subscription_type, Order.from_date, Order.to_date))
        
        for order in orders:
            items_summary = ', '.join(f"{oi.item.name} ({oi.amount})" for oi in order.order_items)
            self.order_tree.insert('', 'end', values=(order.from_date, order.to_date, items_summary))
            selected_item = self.customer_tree.selection()
        if not selected_item:
            return
        
        customer_name = self.customer_tree.item(selected_item, 'values')[0]
        customer = self.customers[customer_name]
        
        # Clear previous orders
        for item in self.order_tree.get_children():
            self.order_tree.delete(item)
        
        # Fetch and display orders for the selected customer
        orders = (Order
                .select()
                .where(Order.customer == customer)
                .group_by(Order.subscription_type, Order.from_date, Order.to_date))
        
        for order in orders:
            items_summary = ', '.join(f"{oi.item.name} ({oi.amount})" for oi in order.order_items)
            self.order_tree.insert('', 'end', values=(order.from_date, order.to_date, items_summary))
            
            
    def edit_order(self):
        selected_item = self.order_tree.selection()
        if not selected_item:
            return

        # Use the from_date and to_date from the selected order row as a grouping key.
        from_date_val, to_date_val, _ = self.order_tree.item(selected_item, 'values')
        try:
            # Retrieve all orders sharing the same subscription date range.
            subscription_orders = list(Order.select().where(
                (Order.from_date == from_date_val) & (Order.to_date == to_date_val)
            ))
        except Order.DoesNotExist:
            messagebox.showerror("Error", "The selected order does not exist.")
            return

        edit_window = tk.Toplevel(self)
        edit_window.title("Edit Subscription Orders")
        edit_window.geometry("800x600")  # Set initial size

        # --- Overall Subscription Details ---
        sub_details_frame = ttk.Frame(edit_window)
        sub_details_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(sub_details_frame, text="Subscription Delivery Date Range:").pack(side='left', padx=5)
        ttk.Label(sub_details_frame, text="From:").pack(side='left')
        overall_from_entry = ttk.Entry(sub_details_frame, width=10)
        overall_from_entry.pack(side='left', padx=5)
        overall_from_entry.insert(0, from_date_val)

        ttk.Label(sub_details_frame, text="To:").pack(side='left')
        overall_to_entry = ttk.Entry(sub_details_frame, width=10)
        overall_to_entry.pack(side='left', padx=5)
        overall_to_entry.insert(0, to_date_val)

        # Main container frame
        main_container = ttk.Frame(edit_window)
        main_container.pack(fill='both', expand=True, padx=10, pady=5)

        # --- Create a Canvas with Scrollbar ---
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        
        # Create a frame inside the canvas which will be scrollable
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure the canvas
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # This list will hold dictionaries representing each order row.
        order_rows = []

        def add_order_row(existing_order=None):
            """
            Create a new order row.
            If existing_order is provided, prepopulate with its delivery date and items.
            """
            row_frame = ttk.Frame(scrollable_frame, relief='groove', borderwidth=1, padding=5)
            row_frame.pack(fill='x', pady=5)

            # Delivery Date for this order row.
            ttk.Label(row_frame, text="Delivery Date:").grid(row=0, column=0, padx=5, pady=2)
            delivery_entry = ttk.Entry(row_frame, width=12)
            delivery_entry.grid(row=0, column=1, padx=5, pady=2)
            if existing_order:
                # Format the date as dd.mm.yyyy
                delivery_entry.insert(0, existing_order.delivery_date.strftime("%d.%m.%Y"))
            else:
                delivery_entry.insert(0, overall_from_entry.get())

            # --- Items Container ---
            items_frame = ttk.Frame(row_frame)
            items_frame.grid(row=1, column=0, columnspan=4, padx=5, pady=5)

            item_rows = []  # List to hold item-row data for this order.

            def add_item_row(existing_order_item=None):
                """
                Add a row for one order item.
                If existing_order_item is provided, prepopulate its fields.
                """
                item_row_frame = ttk.Frame(items_frame)
                item_row_frame.pack(fill='x', pady=2)

                ttk.Label(item_row_frame, text="Item:").pack(side='left', padx=5)
                item_cb = AutocompleteCombobox(item_row_frame, width=20)
                item_cb.set_completion_list(sorted(self.items.keys()))
                item_cb.pack(side='left', padx=5)
                if existing_order_item:
                    item_cb.set(existing_order_item.item.name)

                ttk.Label(item_row_frame, text="Amount:").pack(side='left', padx=5)
                amount_entry = ttk.Entry(item_row_frame, width=8)
                amount_entry.pack(side='left', padx=5)
                if existing_order_item:
                    amount_entry.insert(0, str(existing_order_item.amount))

                def delete_item():
                    # Remove this item row.
                    item_row_frame.destroy()
                    item_rows.remove(item_dict)

                del_button = ttk.Button(item_row_frame, text="Delete", command=delete_item)
                del_button.pack(side='left', padx=5)

                item_dict = {
                    'frame': item_row_frame,
                    'item_cb': item_cb,
                    'amount_entry': amount_entry,
                    'existing': existing_order_item  # None for new items.
                }
                item_rows.append(item_dict)

            # Prepopulate with existing order items if available.
            if existing_order:
                for oi in existing_order.order_items:
                    add_item_row(existing_order_item=oi)
            else:
                # New order: start with one empty item row.
                add_item_row()

            add_item_btn = ttk.Button(row_frame, text="Add Item", command=lambda: add_item_row())
            add_item_btn.grid(row=0, column=2, padx=5, pady=2)

            def delete_order():
                if existing_order:
                    scope_options = ["Delete only this order", "Delete this and all future orders"]
                    
                    # Only show subscription options if this is a subscription order
                    has_subscription = existing_order.subscription_type > 0 and existing_order.from_date and existing_order.to_date
                    
                    if has_subscription:
                        choice = messagebox.askyesnocancel(
                            "Delete Order", 
                            "Do you want to delete only this order?\n\n"
                            "Yes - Delete only this order\n"
                            "No - Delete this and all future orders in this subscription\n"
                            "Cancel - Do not delete anything"
                        )
                        
                        if choice is None:  # Cancel
                            return
                        
                        with db.atomic():  # Transaction to ensure all operations succeed or fail together
                            if choice:  # Yes - Delete only this order
                                existing_order.delete_instance(recursive=True)
                                messagebox.showinfo("Success", "Order deleted successfully!")
                            else:  # No - Delete this and all future orders
                                today = datetime.now().date()
                                future_orders = list(Order.select().where(
                                    (Order.from_date == existing_order.from_date) &
                                    (Order.to_date == existing_order.to_date) &
                                    (Order.delivery_date >= today)
                                ))
                                
                                # Delete all future orders (including this one)
                                deleted_count = 0
                                for future_order in future_orders:
                                    future_order.delete_instance(recursive=True)
                                    deleted_count += 1
                                
                                messagebox.showinfo("Success", f"{deleted_count} orders deleted successfully!")
                    else:
                        # Not a subscription order, simple confirmation
                        if messagebox.askyesno("Confirm", "Delete this order?"):
                            existing_order.delete_instance(recursive=True)
                            messagebox.showinfo("Success", "Order deleted successfully!")
                    
                    row_frame.destroy()
                    order_rows.remove(order_row_dict)
                else:
                    # For new rows that haven't been saved yet
                    row_frame.destroy()
                    order_rows.remove(order_row_dict)

            del_order_btn = ttk.Button(row_frame, text="Delete Order", command=delete_order)
            del_order_btn.grid(row=0, column=3, padx=5, pady=2)

            order_row_dict = {
                'frame': row_frame,
                'delivery_entry': delivery_entry,
                'items': item_rows,
                'existing_order': existing_order
            }
            order_rows.append(order_row_dict)

        # Add rows for each existing subscription order.
        for order in subscription_orders:
            add_order_row(existing_order=order)

        # Button frame at the bottom
        buttons_frame = ttk.Frame(edit_window)
        buttons_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        # Button to add a new order row.
        add_order_overall_btn = ttk.Button(buttons_frame, text="Add New Order", command=lambda: add_order_row())
        add_order_overall_btn.pack(side="left", padx=5)

        def save_all_changes():
            try:
                overall_from_str = overall_from_entry.get()
                overall_to_str = overall_to_entry.get()
                
                # Convert to date objects for saving
                try:
                    overall_from = datetime.strptime(overall_from_str, "%d.%m.%Y").date() if "." in overall_from_str else datetime.strptime(overall_from_str, "%Y-%m-%d").date()
                    overall_to = datetime.strptime(overall_to_str, "%d.%m.%Y").date() if "." in overall_to_str else datetime.strptime(overall_to_str, "%Y-%m-%d").date()
                except ValueError:
                    messagebox.showerror("Error", "Invalid date format. Use either dd.mm.yyyy or yyyy-mm-dd.")
                    return
                
                with db.atomic():  # Use transaction to ensure all changes are saved or none
                    # Loop through each order row to update/create orders and their items.
                    for row in order_rows:
                        delivery_date_str = row['delivery_entry'].get()
                        try:
                            delivery_date = datetime.strptime(delivery_date_str, "%d.%m.%Y").date()
                        except ValueError:
                            messagebox.showerror("Error", f"Invalid date format: {delivery_date_str}. Use dd.mm.yyyy.")
                            return

                        existing_order = row['existing_order']
                        
                        # Gather item data first and validate
                        order_items_data = []
                        for item_row in row['items']:
                            item_name = item_row['item_cb'].get()
                            try:
                                # Convert amount string to float explicitly
                                amount_str = item_row['amount_entry'].get().strip()
                                amount = float(amount_str)
                                if amount <= 0:
                                    raise ValueError(f"Amount must be greater than 0 for item {item_name}")
                            except ValueError as e:
                                if "could not convert string to float" in str(e):
                                    messagebox.showerror("Error", f"Invalid amount for item {item_name}. Please enter a number.")
                                else:
                                    messagebox.showerror("Error", str(e))
                                return
                            
                            if item_name not in self.items:
                                messagebox.showerror("Error", f"Invalid item: {item_name}")
                                return
                            
                            order_items_data.append((item_name, amount))
                        
                        if existing_order:
                            # Update existing order
                            existing_order.delivery_date = delivery_date
                            existing_order.from_date = overall_from
                            existing_order.to_date = overall_to
                            existing_order.save()
                            
                            # Delete existing order items for this order
                            for oi in existing_order.order_items:
                                oi.delete_instance()
                            
                            # Create new order items
                            for item_name, amount in order_items_data:
                                OrderItem.create(
                                    order=existing_order,
                                    item=self.items[item_name],
                                    amount=amount
                                )
                        else:
                            # For a new order, we need a customer
                            if subscription_orders:
                                customer = subscription_orders[0].customer
                                subscription_type = subscription_orders[0].subscription_type
                                halbe_channel = subscription_orders[0].halbe_channel
                            else:
                                messagebox.showerror("Error", "Cannot determine customer for new order.")
                                return
                            
                            # Calculate production date based on max days
                            max_days = max(self.items[item_name].total_days for item_name, _ in order_items_data)
                            production_date = delivery_date - timedelta(days=max_days)
                            
                            # Create new order
                            new_order = Order.create(
                                customer=customer,
                                delivery_date=delivery_date,
                                production_date=production_date,
                                from_date=overall_from,
                                to_date=overall_to,
                                subscription_type=subscription_type,
                                halbe_channel=halbe_channel,
                                order_id=uuid.uuid4(),
                                is_future=True
                            )
                            
                            # Create order items
                            for item_name, amount in order_items_data:
                                OrderItem.create(
                                    order=new_order,
                                    item=self.items[item_name],
                                    amount=amount
                                )
                
                messagebox.showinfo("Success", "Orders updated successfully!")
                edit_window.destroy()
                self.on_customer_select(None)  # Refresh orders list
                
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
        # Save button
        save_btn = ttk.Button(buttons_frame, text="Save All Changes", command=save_all_changes)
        save_btn.pack(side="right", padx=5)

        # Add mouse wheel binding to the canvas for better scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows and macOS
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))  # Linux
            
    def create_order_tab(self):
        # Customer Frame
        customer_frame = ttk.LabelFrame(self.tab1, text="Customer Information", padding="10")
        customer_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(customer_frame, text="Customer:").pack(side='left', padx=5)
        self.customer_combo = AutocompleteCombobox(customer_frame, width=50)
        self.customer_combo.set_completion_list(sorted(self.customers.keys()))
        self.customer_combo.pack(side='left', padx=5, fill='x', expand=True)
        
        # Items Frame
        items_frame = ttk.LabelFrame(self.tab1, text="Order Items", padding="10")
        items_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Add item controls
        add_frame = ttk.Frame(items_frame)
        add_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(add_frame, text="Item:").pack(side='left', padx=5)
        self.item_combo = AutocompleteCombobox(add_frame, width=30)
        self.item_combo.set_completion_list(sorted(self.items.keys()))
        self.item_combo.pack(side='left', padx=5)
        
        ttk.Label(add_frame, text="Amount:").pack(side='left', padx=5)
        self.amount_var = tk.StringVar()
        amount_entry = ttk.Entry(add_frame, textvariable=self.amount_var, width=10)
        amount_entry.pack(side='left', padx=5)
        
        ttk.Button(add_frame, text="Add Item", command=self.add_item).pack(side='left', padx=5)
        
        # Items list
        columns = ('Item', 'Amount', 'Growth Days', 'Price')
        self.items_tree = ttk.Treeview(items_frame, columns=columns, show='headings', height=10)
        for col in columns:
            self.items_tree.heading(col, text=col)
        self.items_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        ttk.Button(items_frame, text="Remove Selected", 
                  command=self.remove_selected_item).pack(pady=5)
        
        # Order Details Frame
        details_frame = ttk.LabelFrame(self.tab1, text="Order Details", padding="10")
        details_frame.pack(fill='x', padx=10, pady=5)
        
        # Delivery Date
        date_frame = ttk.Frame(details_frame)
        date_frame.pack(fill='x', pady=5)
        
        ttk.Label(date_frame, text="Delivery Date:").pack(side='left', padx=5)
        self.delivery_date = self.create_date_entry(date_frame)
        
        # Set default date to today
        today = datetime.now()
        self.set_date_entry(self.delivery_date, today)
        
        # Subscription Frame
        sub_frame = ttk.Frame(details_frame)
        sub_frame.pack(fill='x', pady=5)
        
        self.sub_var = tk.IntVar(value=0)
        sub_types = {
            0: "No subscription",
            1: "Weekly",
            2: "Bi-weekly",
            3: "Every 3 weeks",
            4: "Every 4 weeks"
        }
        for val, text in sub_types.items():
            ttk.Radiobutton(sub_frame, text=text, variable=self.sub_var, 
                          value=val).pack(side='left', padx=5)
        
        # Date Range Frame
        range_frame = ttk.Frame(details_frame)
        range_frame.pack(fill='x', pady=5)
        
        ttk.Label(range_frame, text="From:").pack(side='left', padx=5)
        self.from_date = self.create_date_entry(range_frame)
        
        ttk.Label(range_frame, text="To:").pack(side='left', padx=5)
        self.to_date = self.create_date_entry(range_frame)
        
        # Set default dates
        self.set_date_entry(self.from_date, today)
        self.set_date_entry(self.to_date, datetime(2025, 12, 31))
        
        # Halbe Channel
        self.halbe_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(details_frame, text="Halbe Channel", 
                       variable=self.halbe_var).pack(pady=5)
        
        # Save Button
        ttk.Button(self.tab1, text="Save Order", 
                  command=self.save_order).pack(pady=10)

        # Add this new code at the end
        button_frame = ttk.Frame(self.tab1)
        button_frame.pack(pady=10)
        
        # Save Order button
        ttk.Button(button_frame, text="Save Order", 
                command=self.save_order).pack(side='left', padx=5)
        
        # Master Print button
        ttk.Button(button_frame, text="Print All Schedules", 
                command=self.print_all_schedules).pack(side='left', padx=5)
    
    def create_orders_tab(self):
        # Frame for customer list
        customer_frame = ttk.LabelFrame(self.tab7, text="Kunden", padding="10")
        customer_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Treeview for customer list
        self.customer_tree = ttk.Treeview(customer_frame, columns=('Name', 'Anzahl Bestellungen', 'Umsatz'), show='headings')
        self.customer_tree.heading('Name', text='Name')
        self.customer_tree.heading('Anzahl Bestellungen', text='Anzahl Bestellungen')
        self.customer_tree.heading('Umsatz', text='Umsatz')
        self.customer_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Bind selection event
        self.customer_tree.bind('<<TreeviewSelect>>', self.on_customer_select)
        
        # Frame for order list
        order_frame = ttk.LabelFrame(self.tab7, text="Bestellungen", padding="10")
        order_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Treeview for order list
        self.order_tree = ttk.Treeview(order_frame, columns=('Von Datum', 'Bis Datum', 'Items'), show='headings')
        self.order_tree.heading('Von Datum', text='Von Datum')
        self.order_tree.heading('Bis Datum', text='Bis Datum')
        self.order_tree.heading('Items', text='Items')
        self.order_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Button to edit selected order
        ttk.Button(order_frame, text="Edit Order", command=self.edit_order).pack(pady=5)
        
        self.load_customers()

    def set_date_entry(self, date_frame, date):
        """Set date in a date entry frame"""
        day_entry = date_frame.children['!entry']
        month_entry = date_frame.children['!entry2']
        year_entry = date_frame.children['!entry3']
        
        day_entry.delete(0, tk.END)
        day_entry.insert(0, str(date.day))
        month_entry.delete(0, tk.END)
        month_entry.insert(0, str(date.month))
        year_entry.delete(0, tk.END)
        year_entry.insert(0, str(date.year))
    
    def create_date_entry(self, parent):
        """Create a custom date entry widget"""
        frame = ttk.Frame(parent)
        frame.pack(side='left', padx=5)
        
        # Day
        day_entry = ttk.Entry(frame, width=3)
        day_entry.pack(side='left')
        
        ttk.Label(frame, text=".").pack(side='left')
        
        # Month
        month_entry = ttk.Entry(frame, width=3)
        month_entry.pack(side='left')
        
        ttk.Label(frame, text=".").pack(side='left')
        
        # Year
        year_entry = ttk.Entry(frame, width=5)
        year_entry.pack(side='left')
        
        return frame
    
    def get_date_from_entry(self, date_frame):
        # Get all child widgets that are Entry widgets
        entries = [child for child in date_frame.winfo_children() if isinstance(child, (tk.Entry, ttk.Entry))]
        if len(entries) < 3:
            return datetime.now().date()
        try:
            day = int(entries[0].get())
            month = int(entries[1].get())
            year = int(entries[2].get())
            return datetime(year, month, day).date()
        except ValueError:
            return datetime.now().date()
    
    def add_item(self):
        try:
            item_name = self.item_combo.get()
            amount = float(self.amount_var.get())
            
            if not item_name or item_name not in self.items:
                raise ValueError("Please select a valid item")
            
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")
            
            item = self.items[item_name]
            self.order_items.append({
                'item': item,
                'amount': amount
            })
            
            self.items_tree.insert('', 'end', values=(
                item.name,
                f"{amount:.1f}",
                item.total_days,
                f"€{item.price * amount:.2f}"
            ))
            
            # Clear inputs
            self.item_combo.set('')
            self.amount_var.set('')
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
    
    def remove_selected_item(self):
        selected = self.items_tree.selection()
        if not selected:
            return
        
        for item_id in selected:
            item_index = self.items_tree.index(item_id)
            self.order_items.pop(item_index)
            self.items_tree.delete(item_id)
    
    def save_order(self):
        try:
            if not self.customer_combo.get() or self.customer_combo.get() not in self.customers:
                raise ValueError("Please select a valid customer")
            
            if not self.order_items:
                raise ValueError("Please add at least one item to the order")
            
            customer = self.customers[self.customer_combo.get()]
            delivery_date = self.get_date_from_entry(self.delivery_date)
            
            # Calculate earliest production date based on longest growth period
            max_days = max(item['item'].total_days for item in self.order_items)
            production_date = delivery_date - timedelta(days=max_days)
            
            # Confirm with user if production date falls on Sunday
            if production_date.weekday() == 6:  # 6 = Sunday
                use_sunday = messagebox.askyesnocancel(
                    "Sunday Production",
                    f"This order's production date falls on a Sunday ({production_date.strftime('%d.%m.%Y')}).\n\n"
                    "Yes: Keep Sunday as production date\n"
                    "No: Move to Saturday instead\n"
                    "Cancel: Abort saving the order"
                )
                
                if use_sunday is None:  # User clicked Cancel
                    return
                    
                if use_sunday is False:  # User clicked No, move to Saturday
                    production_date = production_date - timedelta(days=1)
            
            with db.atomic():
                # Create order
                order = Order.create(
                    customer=customer,
                    delivery_date=delivery_date,
                    production_date=production_date,
                    from_date=self.get_date_from_entry(self.from_date) if self.sub_var.get() else None,
                    to_date=self.get_date_from_entry(self.to_date) if self.sub_var.get() else None,
                    subscription_type=self.sub_var.get(),
                    halbe_channel=self.halbe_var.get(),
                    order_id=uuid.uuid4(),
                    is_future=False
                )
                
                # Create order items
                for item_data in self.order_items:
                    OrderItem.create(
                        order=order,
                        item=item_data['item'],
                        amount=item_data['amount']
                    )
                
                # Generate subscription orders if applicable
                if self.sub_var.get() > 0:
                    future_orders = generate_subscription_orders(order)
                    for future_order_data in future_orders:
                        future_order = Order.create(
                            **future_order_data,
                            order_id=uuid.uuid4()
                        )
                        # Copy items to future order
                        for item_data in self.order_items:
                            OrderItem.create(
                                order=future_order,
                                item=item_data['item'],
                                amount=item_data['amount']
                            )
            
            messagebox.showinfo("Success", "Order saved successfully!")
            self.clear_form()
            self.refresh_tables()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def clear_form(self):
        self.customer_combo.set('')
        self.order_items.clear()
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        self.item_combo.set('')
        self.amount_var.set('')
        self.sub_var.set(0)
        self.halbe_var.set(False)
        
        # Reset date entries to defaults
        today = datetime.now()
        self.set_date_entry(self.delivery_date, today)
        self.set_date_entry(self.from_date, today)
        self.set_date_entry(self.to_date, datetime(2025, 12, 31))
    
    def create_delivery_tab(self):
        # Create print button frame
        print_frame = ttk.Frame(self.tab2)
        print_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(print_frame, text="Print Delivery Schedule",
                command=lambda: self.print_single_schedule("delivery")).pack(side='right')
        
        # Pass self (the ProductionApp instance) to WeeklyDeliveryView
        self.delivery_view = WeeklyDeliveryView(self.tab2, self, self.db)
    
    def create_production_tab(self):
        # Create print button frame
        print_frame = ttk.Frame(self.tab3)
        print_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(print_frame, text="Print Production Plan",
                command=lambda: self.print_single_schedule("production")).pack(side='right')
        
        # Add diagnostic button for Sunday production check
        ttk.Button(print_frame, text="Check Sunday Production",
                command=check_sunday_production).pack(side='left', padx=5)
        
        self.production_view = WeeklyProductionView(self.tab3)

    def create_transfer_tab(self):
        # Create print button frame
        print_frame = ttk.Frame(self.tab4)
        print_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(print_frame, text="Print Transfer Schedule",
                command=lambda: self.print_single_schedule("transfer")).pack(side='right')
        
        self.transfer_view = WeeklyTransferView(self.tab4)
    
    def create_customers_tab(self):
        self.customer_view = CustomerView(self.tab5)
    
    def refresh_tables(self):
        """Refresh all weekly views"""
        if hasattr(self, 'delivery_view'):
            self.delivery_view.refresh()
        if hasattr(self, 'production_view'):
            self.production_view.refresh()
        if hasattr(self, 'transfer_view'):
            self.transfer_view.refresh()
        if hasattr(self, 'customer_view'):
            self.customer_view.load_customers()
        
        self.after(5000, self.refresh_tables)

    def print_all_schedules(self):
        """Print all schedules and open the PDF"""
        try:
            week_selection = ask_week_selection()
            if week_selection:
                week_date = date.today()
                if week_selection == "next":
                    week_date += timedelta(days=7)
                
                filepath = self.printer.print_all_schedules(week_date)
                self.open_pdf(filepath)
                messagebox.showinfo("Success", "All schedules have been printed successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to print schedules: {str(e)}")

    def print_single_schedule(self, schedule_type):
        """Print a single schedule and open the PDF"""
        try:
            # Get the currently displayed week from the respective view
            current_week = None
            if schedule_type == "delivery" and hasattr(self, 'delivery_view'):
                current_week = self.delivery_view.current_week
            elif schedule_type == "production" and hasattr(self, 'production_view'):
                current_week = self.production_view.current_week
            elif schedule_type == "transfer" and hasattr(self, 'transfer_view'):
                current_week = self.transfer_view.current_week
            
            if current_week:
                filepath = self.printer.print_week_schedule(schedule_type, current_week)
                self.open_pdf(filepath)
                messagebox.showinfo("Success", f"{schedule_type.title()} schedule has been printed successfully!")
            else:
                messagebox.showerror("Error", "Could not determine the current week")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to print {schedule_type} schedule: {str(e)}")

    def open_pdf(self, filepath):
        """Open the generated PDF file with the default system viewer"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(filepath)
            elif os.name == 'posix':  # macOS and Linux
                if os.system('which open') == 0:  # macOS
                    os.system(f'open "{filepath}"')
                else:  # Linux
                    os.system(f'xdg-open "{filepath}"')
        except Exception as e:
            messagebox.showwarning("Warning", f"PDF was created but couldn't be opened automatically: {filepath}")

VERSION = "0.9"
def check_for_updates():
    try:
        # Replace with your actual repo URL
        response = requests.get("https://api.github.com/repos/yourusername/yourrepo/releases/latest")
        latest_version = response.json()["tag_name"]
        
        if latest_version > VERSION:
            print(f"New version {latest_version} available!")
            print("Please download the latest version from: ")
            print("https://github.com/yourusername/yourrepo/releases/latest")
            return True
    except:
        pass
    return False
if __name__ == "__main__":
    check_for_updates()
    app = ProductionApp()
    app.mainloop()