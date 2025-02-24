import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from database import get_delivery_schedule, get_production_plan, get_transfer_schedule, generate_subscription_orders  # Ensure this import is present
from models import Order, OrderItem
from widgets import AutocompleteCombobox
import ttkbootstrap as ttkb
import uuid

class WeeklyBaseView:
    def __init__(self, parent):
        self.parent = parent
        self.current_week = datetime.now().date()
        self.create_widgets()
        
    def create_widgets(self):
        # Navigation frame
        nav_frame = ttk.Frame(self.parent)
        nav_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(nav_frame, text="← Vorherige Woche", 
                  command=self.previous_week).pack(side='left', padx=5)

        ttk.Button(nav_frame, text="Heute",
                    command=self.today_week).pack(side="left", padx=5)
        
        self.week_label = ttk.Label(nav_frame, text="")
        self.week_label.pack(side='left', padx=20)
        
        ttk.Button(nav_frame, text="Nächste Woche →", 
                  command=self.next_week).pack(side='left', padx=5)
        
        # Create day frames for Monday to Sunday
        self.day_frames = {}
        self.day_labels = {}

        week_frame = ttk.Frame(self.parent)
        week_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        monday = self.get_monday_of_week()
    

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for i, day in enumerate(days):
            date = monday + timedelta(days=i)
            date_str = date.strftime('%d.%m')

            day_label = f"{day} ({date_str})"

            day_frame = ttk.LabelFrame(week_frame, text=day_label)
            day_frame.grid(row=0, column=i, padx=2, pady=5, sticky='nsew')
            week_frame.grid_columnconfigure(i, weight=1)
            
            # Create scrollable frame for items
            canvas = tk.Canvas(day_frame, height=600)
            scrollbar = ttk.Scrollbar(day_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e, canvas=canvas: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            self.day_frames[day] = scrollable_frame
        
        self.update_week_label()
        self.highlight_current_day()
        
    def previous_week(self):
        self.current_week -= timedelta(days=7)
        self.update_week_label()
        self.refresh()
    
    def today_week(self):
        # Renamed from current_week to avoid confusion with the property
        self.current_week = datetime.now().date()
        self.update_week_label()
        self.update_day_labels()
        self.refresh()

    def next_week(self):
        self.current_week += timedelta(days=7)
        self.update_week_label()
        self.refresh()

    def update_day_labels(self):
        # Update day frame labels with current dates
        monday = self.get_monday_of_week()
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for i, day in enumerate(days):
            date = monday + timedelta(days=i)
            date_str = date.strftime('%d.%m')
            day_label = f"{day} ({date_str})"
            
            # Update the label text
            if day in self.day_labels:
                self.day_labels[day].configure(text=day_label)
    
    def update_week_label(self):
        # Get Monday of current week
        monday = self.current_week - timedelta(days=self.current_week.weekday())
        sunday = monday + timedelta(days=6)
        self.week_label.config(
            text=f"Week {monday.strftime('%d.%m.%Y')} - {sunday.strftime('%d.%m.%Y')}"
        )
    
    def clear_day_frames(self):
        for frame in self.day_frames.values():
            for widget in frame.winfo_children():
                widget.destroy()
    
    def get_monday_of_week(self):
        return self.current_week - timedelta(days=self.current_week.weekday())

    def highlight_current_day(self):
        today = datetime.now().date()
        day_name = today.strftime('%A')
        if day_name in self.day_frames:
            frame = self.day_frames[day_name]
            frame.config(style='Green.TFrame')

class WeeklyDeliveryView(WeeklyBaseView):
    def __init__(self, parent, app, db):
        super().__init__(parent)
        self.app = app  # Reference to the ProductionApp instance
        self.new_order_widgets = {}  # Will hold new order widgets for each day
        self.db = db

        # Define a custom style for clickable labels using ttkbootstrap
        style = ttkb.Style('darkly')
        style.configure('Clickable.TLabel', 
                        background='#007BFF',  # Bootstrap primary color
                        foreground='white', 
                        borderwidth=1, 
                        relief='solid', 
                        padding=5, 
                        bordercolor='#0056b3')  # Darker shade for border

        # Optional: Change background on hover/active state
        style.map('Clickable.TLabel', background=[('active', '#0056b3')])

        # Add a "+" button to each day frame to add a new order
        for day, frame in self.day_frames.items():
            add_order_button = ttk.Button(frame, text="+", command=lambda day=day: self.open_new_order_window(day))
            add_order_button.pack(side='top', anchor='ne', padx=5, pady=5)

    def open_new_order_window(self, day):
        """Open a new window to create an order for the specified day."""
        new_order_window = tk.Toplevel(self.parent)
        new_order_window.title(f"Create New Order for {day}")

        # Customer Frame
        customer_frame = ttk.LabelFrame(new_order_window, text="Customer Information", padding="10")
        customer_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(customer_frame, text="Customer:").pack(side='left', padx=5)
        customer_combo = AutocompleteCombobox(customer_frame, width=50)
        customer_combo.set_completion_list(sorted(self.app.customers.keys()))
        customer_combo.pack(side='left', padx=5, fill='x', expand=True)
        
        # Items Frame
        items_frame = ttk.LabelFrame(new_order_window, text="Order Items", padding="10")
        items_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Add item controls
        add_frame = ttk.Frame(items_frame)
        add_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(add_frame, text="Item:").pack(side='left', padx=5)
        item_combo = AutocompleteCombobox(add_frame, width=30)
        item_combo.set_completion_list(sorted(self.app.items.keys()))
        item_combo.pack(side='left', padx=5)
        
        ttk.Label(add_frame, text="Amount:").pack(side='left', padx=5)
        amount_var = tk.StringVar()
        amount_entry = ttk.Entry(add_frame, textvariable=amount_var, width=10)
        amount_entry.pack(side='left', padx=5)
        
        order_items = []  # List to store items for current order
        
        def add_item():
            try:
                item_name = item_combo.get()
                amount = float(amount_var.get())
                
                if not item_name or item_name not in self.app.items:
                    raise ValueError("Please select a valid item")
                
                if amount <= 0:
                    raise ValueError("Amount must be greater than 0")
                
                item = self.app.items[item_name]
                order_items.append({
                    'item': item,
                    'amount': amount
                })
                
                items_tree.insert('', 'end', values=(
                    item.name,
                    f"{amount:.1f}",
                    item.total_days,
                    f"€{item.price * amount:.2f}"
                ))
                
                # Clear inputs
                item_combo.set('')
                amount_var.set('')
                
            except ValueError as e:
                messagebox.showerror("Error", str(e))
        
        ttk.Button(add_frame, text="Add Item", command=add_item).pack(side='left', padx=5)
        
        # Items list
        columns = ('Item', 'Amount', 'Growth Days', 'Price')
        items_tree = ttk.Treeview(items_frame, columns=columns, show='headings', height=10)
        for col in columns:
            items_tree.heading(col, text=col)
        items_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        def remove_selected_item():
            selected = items_tree.selection()
            if not selected:
                return
            
            for item_id in selected:
                item_index = items_tree.index(item_id)
                order_items.pop(item_index)
                items_tree.delete(item_id)
        
        ttk.Button(items_frame, text="Remove Selected", 
                  command=remove_selected_item).pack(pady=5)
        
        # Order Details Frame
        details_frame = ttk.LabelFrame(new_order_window, text="Order Details", padding="10")
        details_frame.pack(fill='x', padx=10, pady=5)
        
        # Delivery Date
        date_frame = ttk.Frame(details_frame)
        date_frame.pack(fill='x', pady=5)
        
        ttk.Label(date_frame, text="Delivery Date:").pack(side='left', padx=5)
        delivery_date = self.app.create_date_entry(date_frame)
        
        # Set default date to the selected day
        monday = self.get_monday_of_week()
        days_index = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
        selected_date = monday + timedelta(days=days_index[day])
        self.app.set_date_entry(delivery_date, selected_date)
        
        # Subscription Frame
        sub_frame = ttk.Frame(details_frame)
        sub_frame.pack(fill='x', pady=5)
        
        sub_var = tk.IntVar(value=0)
        sub_types = {
            0: "No subscription",
            1: "Weekly",
            2: "Bi-weekly",
            3: "Every 3 weeks",
            4: "Every 4 weeks"
        }
        for val, text in sub_types.items():
            ttk.Radiobutton(sub_frame, text=text, variable=sub_var, 
                          value=val).pack(side='left', padx=5)
        
        # Date Range Frame
        range_frame = ttk.Frame(details_frame)
        range_frame.pack(fill='x', pady=5)
        
        ttk.Label(range_frame, text="From:").pack(side='left', padx=5)
        from_date = self.app.create_date_entry(range_frame)
        
        ttk.Label(range_frame, text="To:").pack(side='left', padx=5)
        to_date = self.app.create_date_entry(range_frame)
        
        # Set default dates
        self.app.set_date_entry(from_date, selected_date)
        self.app.set_date_entry(to_date, datetime(2025, 12, 31))
        
        # Halbe Channel
        halbe_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(details_frame, text="Halbe Channel", 
                       variable=halbe_var).pack(pady=5)
        
        def save_order():
            try:
                if not customer_combo.get() or customer_combo.get() not in self.app.customers:
                    raise ValueError("Please select a valid customer")
                
                if not order_items:
                    raise ValueError("Please add at least one item to the order")
                
                customer = self.app.customers[customer_combo.get()]
                delivery_date_value = self.app.get_date_from_entry(delivery_date)
                
                # Calculate earliest production date based on longest growth period
                max_days = max(item['item'].total_days for item in order_items)
                production_date = delivery_date_value - timedelta(days=max_days)
                
                with self.db.atomic():
                    # Create order
                    order = Order.create(
                        customer=customer,
                        delivery_date=delivery_date_value,
                        production_date=production_date,
                        from_date=self.app.get_date_from_entry(from_date) if sub_var.get() else None,
                        to_date=self.app.get_date_from_entry(to_date) if sub_var.get() else None,
                        subscription_type=sub_var.get(),
                        halbe_channel=halbe_var.get(),
                        order_id=uuid.uuid4(),
                        is_future=False
                    )
                    
                    # Create order items
                    for item_data in order_items:
                        OrderItem.create(
                            order=order,
                            item=item_data['item'],
                            amount=item_data['amount']
                        )
                    
                    # Generate subscription orders if applicable
                    if sub_var.get() > 0:
                        future_orders = generate_subscription_orders(order)
                        for future_order_data in future_orders:
                            future_order = Order.create(
                                **future_order_data,
                                order_id=uuid.uuid4()
                            )
                            # Copy items to future order
                            for item_data in order_items:
                                OrderItem.create(
                                    order=future_order,
                                    item=item_data['item'],
                                    amount=item_data['amount']
                                )
                
                messagebox.showinfo("Success", "Order saved successfully!")
                new_order_window.destroy()
                self.refresh()
                
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        # Save Button
        ttk.Button(new_order_window, text="Save Order", 
                  command=save_order).pack(pady=10)
    def refresh(self):
        self.clear_day_frames()
        self.new_order_widgets.clear()
        monday = self.get_monday_of_week()
        end_of_week = monday + timedelta(days=6)
        deliveries = get_delivery_schedule(monday, end_of_week)

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for i, day in enumerate(days):
            date = monday + timedelta(days=i)
            date_str = date.strftime('%d.%m')
            day_label = f"{day} ({date_str})"
            
            # Find the day frame and update its label
            for child in self.parent.winfo_children():
                if isinstance(child, ttk.Frame):
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, ttk.LabelFrame) and day in grandchild['text']:
                            grandchild['text'] = day_label
                            break
                            
        # Group deliveries by day name
        deliveries_by_day = {day: [] for day in days}
        for delivery in deliveries:
            day_name = days[delivery.delivery_date.weekday()]
            deliveries_by_day[day_name].append(delivery)
        
        # For each day, show its deliveries and add the "+" button
        for day in days:
            frame = self.day_frames[day]
            
            # Add the "+" button to each day frame - at the top
            button_frame = ttk.Frame(frame)
            button_frame.pack(side='top', fill='x', padx=5, pady=5)
            add_order_button = ttk.Button(button_frame, text="+", width=3, 
                                        command=lambda day=day: self.open_new_order_window(day))
            add_order_button.pack(side='right')

            # Display existing orders for this day
            for delivery in deliveries_by_day[day]:
                # Check if the order has any items
                if not delivery.order_items.exists():
                    continue  # Skip orders with no items

                customer_frame = ttk.Frame(frame)
                customer_frame.pack(fill='x', padx=5, pady=2)
                customer_label = ttk.Label(customer_frame, 
                                        text=delivery.customer.name,
                                        font=('Arial', 16, 'bold'),
                                        style='Clickable.TLabel',
                                        wraplength=frame.winfo_width() if frame.winfo_width() > 0 else 150,
                                        anchor='w')
                customer_label.pack(anchor='w', fill='x')

                # Dynamically set wraplength based on frame width
                def update_wrap(event, label=customer_label):
                    label.configure(wraplength=event.width - 5)  # Slight padding to avoid touching edges

                customer_frame.bind("<Configure>", update_wrap)

                # Clicking the label opens the order editor (edit mode)
                customer_label.bind("<Button-1>", lambda e, order=delivery: self.open_order_editor(delivery.delivery_date, order))
                
                # List order items
                for order_item in delivery.order_items:
                    item_text = f"• {order_item.item.name}: {order_item.amount:.1f}"
                    ttk.Label(customer_frame, text=item_text).pack(anchor='w', padx=10)

    def create_or_update_new_order_widget(self, day):
        frame = self.day_frames[day]
        if day not in self.new_order_widgets:
            new_order_frame = ttk.Frame(frame, relief='ridge', borderwidth=1)
            # An autocomplete entry for selecting a customer
            new_order_entry = AutocompleteCombobox(new_order_frame, width=20)
            new_order_entry.set_completion_list(sorted(self.app.customers.keys()))
            new_order_entry.pack(side='left', padx=5)
            # A button to create a new order
            new_order_button = ttk.Button(new_order_frame, text="New Order", 
                                          command=lambda day=day, entry=new_order_entry: self.handle_new_order(day, entry))
            new_order_button.pack(side='left', padx=5)
            # Store the widget in the dictionary
            self.new_order_widgets[day] = new_order_frame
        else:
            new_order_frame = self.new_order_widgets[day]
        # Position the new order widget at the bottom of the day frame
        new_order_frame.pack(side='bottom', fill='x', pady=2)
        # Position the new order widget at the bottom of the day frame
        new_order_frame.pack(side='bottom', fill='x', pady=2)
    
    def show_new_order_widget(self, day):
        if day in self.new_order_widgets:
            self.new_order_widgets[day].pack(side='bottom', fill='x', pady=2)
    
    def hide_new_order_widget(self, day):
        if day in self.new_order_widgets:
            self.new_order_widgets[day].pack_forget()
    
    def handle_new_order(self, day, entry):
        # Read the customer name (if any) from the new order entry
        customer_name = entry.get()
        monday = self.get_monday_of_week()
        days_index = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
        delivery_date = monday + timedelta(days=days_index[day])
        # Open the order editor in "create" mode (order=None) with an optional prefilled customer name
        self.open_order_editor(delivery_date, order=None, prefill_customer=customer_name)

    def open_order_editor(self, delivery_date, order=None, prefill_customer=None):
        """
        Opens a Toplevel window for creating a new order (if order is None) or editing an existing order.
        The delivery_date is pre-set; if prefill_customer is provided (for new orders), that value pre-fills the customer field.
        """
        edit_window = tk.Toplevel(self.parent)
        if order:
            edit_window.title(f"Edit Order for {order.customer.name} on {order.delivery_date.strftime('%d.%m.%Y')}")
        else:
            edit_window.title(f"Create New Order for {delivery_date.strftime('%d.%m.%Y')}")
        
        # --- Delivery Date Section ---
        date_frame = ttk.Frame(edit_window)
        date_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(date_frame, text="Delivery Date:").pack(side='left', padx=5)
        delivery_date_entry = ttk.Entry(date_frame, width=12)
        delivery_date_entry.pack(side='left', padx=5)
        delivery_date_entry.insert(0, delivery_date.strftime('%d.%m.%Y'))
        
        # --- Customer Selection (only for new orders) ---
        customer_cb = None
        if not order:
            cust_frame = ttk.Frame(edit_window)
            cust_frame.pack(fill='x', padx=10, pady=5)
            ttk.Label(cust_frame, text="Customer:").pack(side='left', padx=5)
            customer_cb = AutocompleteCombobox(cust_frame, width=30)
            customer_cb.set_completion_list(sorted(self.app.customers.keys()))
            customer_cb.pack(side='left', padx=5)
            if prefill_customer:
                customer_cb.set(prefill_customer)
        
        # --- Order Items Section ---
        items_frame = ttk.Frame(edit_window)
        items_frame.pack(fill='both', expand=True, padx=10, pady=10)
        item_rows = []
        
        def add_item_row(existing_order_item=None):
            row_frame = ttk.Frame(items_frame)
            row_frame.pack(fill='x', pady=2)
            ttk.Label(row_frame, text="Item:").pack(side='left', padx=5)
            item_cb = AutocompleteCombobox(row_frame, width=20)
            item_cb.set_completion_list(sorted(self.app.items.keys()))
            item_cb.pack(side='left', padx=5)
            if existing_order_item:
                item_cb.set(existing_order_item.item.name)
            ttk.Label(row_frame, text="Amount:").pack(side='left', padx=5)
            amount_entry = ttk.Entry(row_frame, width=8)
            amount_entry.pack(side='left', padx=5)
            if existing_order_item:
                amount_entry.insert(0, str(existing_order_item.amount))
            def delete_item():
                row_frame.destroy()
                item_rows.remove(item_dict)
            del_button = ttk.Button(row_frame, text="Delete", command=delete_item)
            del_button.pack(side='left', padx=5)
            item_dict = {
                'frame': row_frame,
                'item_cb': item_cb,
                'amount_entry': amount_entry,
                'existing': existing_order_item
            }
            item_rows.append(item_dict)
        
        if order:
            for oi in order.order_items:
                add_item_row(existing_order_item=oi)
        else:
            add_item_row()  # start with one empty item row
        
        add_item_btn = ttk.Button(edit_window, text="Add Item", command=lambda: add_item_row())
        add_item_btn.pack(pady=5)
        
        # --- Save Changes Button ---
        def save_changes():
            new_date_str = delivery_date_entry.get()
            try:
                new_date = datetime.strptime(new_date_str, "%d.%m.%Y").date()
            except ValueError:
                messagebox.showerror("Error", f"Invalid date format: {new_date_str}. Use dd.mm.yyyy.")
                return

            # Initialize order_obj with the existing order parameter
            order_obj = order

            if order_obj:  # This block is for updating an existing order
                order_obj.delivery_date = new_date
                order_obj.save()
                for oi in order_obj.order_items:
                    oi.delete_instance()
            else:  # This block is for creating a new order
                if customer_cb is None:
                    messagebox.showerror("Error", "Customer selection is required.")
                    return
                customer_name = customer_cb.get()
                if customer_name not in self.app.customers:
                    messagebox.showerror("Error", "Invalid customer")
                    return
                order_obj = Order.create(
                    customer=self.app.customers[customer_name],
                    delivery_date=new_date,
                    production_date=new_date - timedelta(days=7),  # Adjust production_date as needed
                    from_date=new_date,
                    to_date=new_date,
                    subscription_type=0,  # No subscription by default
                    halbe_channel=False,
                    order_id=uuid.uuid4(),
                    is_future=False
                )

            # Process order items
            for row in item_rows:
                item_name = row['item_cb'].get()
                try:
                    amount = float(row['amount_entry'].get())
                except ValueError:
                    messagebox.showerror("Error", f"Invalid amount for item {item_name}.")
                    return
                if item_name not in self.app.items:
                    messagebox.showerror("Error", f"Invalid item: {item_name}.")
                    return
                OrderItem.create(
                    order=order_obj,  # Use order_obj instead of order
                    item=self.app.items[item_name],
                    amount=amount
                )
            messagebox.showinfo("Success", "Order saved successfully!")
            edit_window.destroy()
            self.refresh()
            
        save_btn = ttk.Button(edit_window, text="Save Changes", command=save_changes)
        save_btn.pack(pady=10)

        # --- Delete Order Button ---
        if order:
            def delete_order():
                if messagebox.askyesno("Delete Order", "Are you sure you want to delete this order?"):
                    order.delete_instance(recursive=True)  # Deletes the order and its related items
                    messagebox.showinfo("Success", "Order deleted successfully!")
                    edit_window.destroy()
                    self.refresh()

            delete_btn = ttk.Button(edit_window, text="Delete Order", command=delete_order)
            delete_btn.pack(pady=5)

class WeeklyProductionView(WeeklyBaseView):
    def refresh(self):
        self.clear_day_frames()
        monday = self.get_monday_of_week()
        end_of_week = monday + timedelta(days=6)
        
        # Get all production tasks for the week
        production_data = get_production_plan(monday, end_of_week)
        
        # Group by day
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for i, day in enumerate(days):
            date = monday + timedelta(days=i)
            date_str = date.strftime('%d.%m')
            day_label = f"{day} ({date_str})"
            
            # Find the day frame and update its label
            for child in self.parent.winfo_children():
                if isinstance(child, ttk.Frame):
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, ttk.LabelFrame) and day in grandchild['text']:
                            grandchild['text'] = day_label
                            break
        for prod in production_data:
            day_idx = prod.order.production_date.weekday()  # Changed from prod.production_date
            day_name = days[day_idx]
            frame = self.day_frames[day_name]
            
            # Create item frame
            item_frame = ttk.Frame(frame)
            item_frame.pack(fill='x', padx=5, pady=2)
            
            # Display item name and amount on one line
            item_text = f"{prod.item.name}: {prod.total_amount:.1f}"
            ttk.Label(item_frame, text=item_text, font=('Arial', 16, 'bold')).pack(anchor='w')

            #amount_text = f"Amount: {prod.total_amount:.1f}"
            #seeds_text = f"Seeds: {prod.total_amount * prod.item.seed_quantity:.1f}g"  # Changed to access through item
            substrate_text = f"Substrate: {prod.item.substrate}"  # Changed to access through item
            
            #ttk.Label(item_frame, text=amount_text).pack(anchor='w', padx=10)
            #ttk.Label(item_frame, text=seeds_text).pack(anchor='w', padx=10)
            ttk.Label(item_frame, text=substrate_text).pack(anchor='w', padx=10)

class WeeklyTransferView(WeeklyBaseView):
    def refresh(self):
        self.clear_day_frames()
        monday = self.get_monday_of_week()
        end_of_week = monday + timedelta(days=6)
        
        # Get all transfers for the week
        transfer_data = get_transfer_schedule(monday, end_of_week)
        
        # Group by day
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for i, day in enumerate(days):
            date = monday + timedelta(days=i)
            date_str = date.strftime('%d.%m')
            day_label = f"{day} ({date_str})"
            
            # Find the day frame and update its label
            for child in self.parent.winfo_children():
                if isinstance(child, ttk.Frame):
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, ttk.LabelFrame) and day in grandchild['text']:
                            grandchild['text'] = day_label
                            break

        for transfer in transfer_data:
            day_idx = transfer['date'].weekday()
            day_name = days[day_idx]
            frame = self.day_frames[day_name]
            
            # Create item frame
            item_frame = ttk.Frame(frame)
            item_frame.pack(fill='x', padx=5, pady=2)
            
            # Display item name and transfer amount on one line
            item_text = f"{transfer['item']}: {transfer['amount']:.1f}"
            ttk.Label(item_frame, text=item_text, font=('Arial', 16, 'bold')).pack(anchor='w')

def format_date(date):
    """Format date as DD.MM.YYYY"""
    return date.strftime('%d.%m.%Y')