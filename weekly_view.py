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
        self.canvases = {}
        self.day_frames = {}
        self.day_labels = {}
        self.button_frames = {}
        self.scrollbars = {}
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
        
        # Create main container for days
        week_frame = ttk.Frame(self.parent)
        week_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Make sure week_frame takes all available vertical space
        self.parent.pack_propagate(False)
        
        monday = self.get_monday_of_week()
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Configure column weights to ensure equal sizing
        for i in range(7):
            week_frame.columnconfigure(i, weight=1)
        
        # Configure row weight to ensure vertical expansion
        week_frame.rowconfigure(0, weight=1)
        
        for i, day in enumerate(days):
            date = monday + timedelta(days=i)
            date_str = date.strftime('%d.%m')
            day_label = f"{day} ({date_str})"

            # Create labeled frame for each day
            day_container = ttk.LabelFrame(week_frame, text=day_label)
            day_container.grid(row=0, column=i, padx=2, pady=5, sticky='nsew')
            self.day_labels[day] = day_container
            
            # Create fixed button frame at top (for "+" button in delivery view)
            button_frame = ttk.Frame(day_container)
            button_frame.pack(side='top', fill='x')
            self.button_frames[day] = button_frame
            
            # Create scrollable content area - use full height
            content_frame = ttk.Frame(day_container)
            content_frame.pack(fill='both', expand=True)
            
            # Add vertical scrollbar
            scrollbar = ttk.Scrollbar(content_frame, orient="vertical")
            scrollbar.pack(side='right', fill='y')
            self.scrollbars[day] = scrollbar
            
            # Create canvas for scrolling with fixed minimum height
            canvas = tk.Canvas(content_frame, yscrollcommand=scrollbar.set, highlightthickness=0, height=600)
            canvas.pack(side='left', fill='both', expand=True)
            scrollbar.configure(command=canvas.yview)
            self.canvases[day] = canvas
            
            # Create inner frame for content
            inner_frame = ttk.Frame(canvas)
            canvas_window = canvas.create_window((0, 0), window=inner_frame, anchor='nw', tags='inner_frame')
            self.day_frames[day] = inner_frame
            
            # Configure the canvas to adjust the scrollregion when the inner frame changes size
            def configure_scroll_region(event, canvas=canvas):
                canvas.configure(scrollregion=canvas.bbox("all"))
            
            # Configure the canvas window to expand to the width of the canvas
            def configure_window_size(event, canvas=canvas, window=canvas_window):
                canvas.itemconfig(window, width=event.width)
            
            inner_frame.bind("<Configure>", configure_scroll_region)
            canvas.bind("<Configure>", configure_window_size)
            
            # Bind mousewheel events for scrolling
            def on_mousewheel(event, canvas=canvas):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            
            # Bind specific canvas to mousewheel when mouse enters
            def on_enter(event, canvas=canvas):
                canvas.bind_all("<MouseWheel>", lambda e, c=canvas: on_mousewheel(e, c))
            
            # Unbind mousewheel when mouse leaves
            def on_leave(event):
                canvas.unbind_all("<MouseWheel>")
            
            canvas.bind("<Enter>", on_enter)
            canvas.bind("<Leave>", on_leave)
            
            # Linux scrolling
            canvas.bind("<Button-4>", lambda e, c=canvas: c.yview_scroll(-1, "units"))
            canvas.bind("<Button-5>", lambda e, c=canvas: c.yview_scroll(1, "units"))
        
        self.update_week_label()
        self.highlight_current_day()
        
        # Force layout update to ensure proper dimensions
        self.parent.update_idletasks()
        
    def previous_week(self):
        self.current_week -= timedelta(days=7)
        self.update_week_label()
        self.refresh()
    
    def today_week(self):
        self.current_week = datetime.now().date()
        self.update_week_label()
        self.update_day_labels()
        self.refresh()

    def next_week(self):
        self.current_week += timedelta(days=7)
        self.update_week_label()
        self.refresh()

    def update_day_labels(self):
        monday = self.get_monday_of_week()
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for i, day in enumerate(days):
            date = monday + timedelta(days=i)
            date_str = date.strftime('%d.%m')
            day_label = f"{day} ({date_str})"
            
            if day in self.day_labels:
                self.day_labels[day].configure(text=day_label)
    
    def update_week_label(self):
        monday = self.current_week - timedelta(days=self.current_week.weekday())
        sunday = monday + timedelta(days=6)
        self.week_label.config(
            text=f"Week {monday.strftime('%d.%m.%Y')} - {sunday.strftime('%d.%m.%Y')}"
        )
    
    def clear_day_frames(self):
        for day, frame in self.day_frames.items():
            for widget in frame.winfo_children():
                widget.destroy()
    
    def get_monday_of_week(self):
        return self.current_week - timedelta(days=self.current_week.weekday())

    def highlight_current_day(self):
        today = datetime.now().date()
        day_name = today.strftime('%A')
        if day_name in self.day_labels:
            frame = self.day_labels[day_name]
            # Apply a highlight style if available, otherwise use a background color
            try:
                frame.configure(style='Green.TLabelframe')
            except:
                # Fallback if style not available
                frame.configure(background='green')

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
        monday = self.get_monday_of_week()
        end_of_week = monday + timedelta(days=6)
        deliveries = get_delivery_schedule(monday, end_of_week)

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for i, day in enumerate(days):
            date = monday + timedelta(days=i)
            date_str = date.strftime('%d.%m')
            day_label = f"{day} ({date_str})"
            
            # Update day labels
            if day in self.day_labels:
                self.day_labels[day].configure(text=day_label)
        
        # Clear button frames and add + buttons
        for day in days:
            # Clear existing buttons
            for widget in self.button_frames[day].winfo_children():
                widget.destroy()
                
            # Add new + button
            add_order_button = ttk.Button(
                self.button_frames[day],
                text="+",
                width=3,
                command=lambda d=day: self.open_new_order_window(d)
            )
            add_order_button.pack(side='right', padx=5, pady=5)
                            
        # Group deliveries by day name
        deliveries_by_day = {day: [] for day in days}
        for delivery in deliveries:
            day_name = days[delivery.delivery_date.weekday()]
            deliveries_by_day[day_name].append(delivery)
        
        # Display deliveries for each day
        for day in days:
            frame = self.day_frames[day]
            
            # Display existing orders for this day in the scrollable frame
            for delivery in deliveries_by_day[day]:
                # Skip orders with no items
                if not delivery.order_items.exists():
                    continue

                # Create a frame for each customer with a border and padding
                customer_frame = ttk.Frame(frame, relief='groove', borderwidth=1)
                customer_frame.pack(fill='x', padx=5, pady=5, ipadx=5, ipady=5)
                
                # Customer name header
                customer_label = ttk.Label(
                    customer_frame,
                    text=delivery.customer.name,
                    font=('Arial', 12, 'bold'),
                    style='Clickable.TLabel',
                    wraplength=200,  # Fixed width to ensure text is visible
                    anchor='w'
                )
                customer_label.pack(anchor='w', fill='x', padx=5, pady=5)

                # Make label clickable
                customer_label.bind(
                    "<Button-1>", 
                    lambda e, order=delivery: self.open_order_editor(delivery.delivery_date, order)
                )
                
                # Add a separator
                ttk.Separator(customer_frame, orient='horizontal').pack(fill='x', padx=5, pady=3)
                
                # Create a frame for items
                items_frame = ttk.Frame(customer_frame)
                items_frame.pack(fill='x', padx=5, pady=5)
                
                # List order items in a clean layout
                for index, order_item in enumerate(delivery.order_items):
                    item_frame = ttk.Frame(items_frame)
                    item_frame.pack(fill='x', pady=2)
                    
                    item_text = f"{order_item.item.name}: {order_item.amount:.1f}"
                    ttk.Label(
                        item_frame, 
                        text=item_text,
                        font=('Arial', 11)
                    ).pack(anchor='w', padx=10)

            # Make sure canvases are properly configured for scrolling
            if day in self.canvases:
                self.canvases[day].update_idletasks()
                self.canvases[day].configure(scrollregion=self.canvases[day].bbox("all"))
                                
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
        Now handles subscription editing and updates all related future orders.
        """
        edit_window = tk.Toplevel(self.parent)
        if order:
            edit_window.title(f"Edit Order for {order.customer.name} on {order.delivery_date.strftime('%d.%m.%Y')}")
        else:
            edit_window.title(f"Create New Order for {delivery_date.strftime('%d.%m.%Y')}")
        
        edit_window.geometry("700x600")  # Set a larger size for the window
        
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
        
        # --- Subscription Type Section ---
        subscription_frame = ttk.LabelFrame(edit_window, text="Subscription Settings")
        subscription_frame.pack(fill='x', padx=10, pady=5)
        
        sub_var = tk.IntVar(value=0 if not order else order.subscription_type)
        
        # Create frame for subscription type
        sub_type_frame = ttk.Frame(subscription_frame)
        sub_type_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(sub_type_frame, text="Subscription Type:").pack(side='left', padx=5)
        
        sub_types = {
            0: "No subscription",
            1: "Weekly",
            2: "Bi-weekly",
            3: "Every 3 weeks",
            4: "Every 4 weeks"
        }
        
        # Create dropdown for subscription type instead of radio buttons
        sub_combo = ttk.Combobox(sub_type_frame, textvariable=sub_var, width=15, state="readonly")
        sub_combo['values'] = [f"{v}" for k, v in sub_types.items()]
        sub_combo.current(sub_var.get())  # Set to current value
        sub_combo.pack(side='left', padx=5)
        
        # Create frame for date range
        date_range_frame = ttk.Frame(subscription_frame)
        date_range_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(date_range_frame, text="From:").pack(side='left', padx=5)
        from_date_entry = ttk.Entry(date_range_frame, width=12)
        from_date_entry.pack(side='left', padx=5)
        
        ttk.Label(date_range_frame, text="To:").pack(side='left', padx=5)
        to_date_entry = ttk.Entry(date_range_frame, width=12)
        to_date_entry.pack(side='left', padx=5)
        
        # Set current subscription dates if editing
        if order and order.from_date and order.to_date:
            from_date_entry.insert(0, order.from_date.strftime('%d.%m.%Y'))
            to_date_entry.insert(0, order.to_date.strftime('%d.%m.%Y'))
        else:
            # Default dates for new orders
            today = datetime.now().date()
            from_date_entry.insert(0, today.strftime('%d.%m.%Y'))
            to_date_entry.insert(0, (today + timedelta(days=365)).strftime('%d.%m.%Y'))
        
        # Halbe Channel checkbox
        halbe_var = tk.BooleanVar(value=False if not order else order.halbe_channel)
        ttk.Checkbutton(subscription_frame, text="Halbe Channel", variable=halbe_var).pack(padx=5, pady=5)
        
        # --- Order Items Section ---
        items_frame = ttk.LabelFrame(edit_window, text="Order Items")
        items_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create scrollable frame for items
        canvas = tk.Canvas(items_frame)
        scrollbar = ttk.Scrollbar(items_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure scrolling
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        item_rows = []
        
        def add_item_row(existing_order_item=None):
            row_frame = ttk.Frame(scrollable_frame)
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
        
        # --- Update Type Frame for edit scope---
        update_frame = ttk.LabelFrame(edit_window, text="Update Scope")
        update_frame.pack(fill='x', padx=10, pady=5)
        
        update_type = tk.StringVar(value="current")
        
        ttk.Radiobutton(
            update_frame, 
            text="Update only this order", 
            variable=update_type, 
            value="current"
        ).pack(anchor='w', padx=5, pady=2)
        
        ttk.Radiobutton(
            update_frame, 
            text="Update this and all future orders in this subscription", 
            variable=update_type, 
            value="future"
        ).pack(anchor='w', padx=5, pady=2)
        
        ttk.Radiobutton(
            update_frame, 
            text="Create a new subscription with these settings", 
            variable=update_type, 
            value="new"
        ).pack(anchor='w', padx=5, pady=2)
        
        # --- Save Changes Button ---
        def save_changes():
            try:
                # Parse the delivery date
                new_date_str = delivery_date_entry.get()
                try:
                    new_date = datetime.strptime(new_date_str, "%d.%m.%Y").date()
                except ValueError:
                    messagebox.showerror("Error", f"Invalid date format: {new_date_str}. Use dd.mm.yyyy.")
                    return
                
                # Parse subscription dates
                if sub_var.get() > 0:  # If it's a subscription
                    try:
                        from_date = datetime.strptime(from_date_entry.get(), "%d.%m.%Y").date()
                        to_date = datetime.strptime(to_date_entry.get(), "%d.%m.%Y").date()
                        if from_date > to_date:
                            messagebox.showerror("Error", "From date must be before To date.")
                            return
                    except ValueError:
                        messagebox.showerror("Error", "Invalid date format for subscription range. Use dd.mm.yyyy.")
                        return
                else:
                    from_date = None
                    to_date = None
                
                # Initialize order_obj with the existing order parameter
                order_obj = order
                
                # Gather item data
                order_items_data = []
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
                    order_items_data.append((item_name, amount))
                
                with self.db.atomic():  # Transaction to ensure all operations succeed or fail together
                    if update_type.get() == "current":
                        # Only update the current order
                        if order_obj:  # Editing existing order
                            order_obj.delivery_date = new_date
                            order_obj.subscription_type = sub_var.get()
                            order_obj.from_date = from_date
                            order_obj.to_date = to_date
                            order_obj.halbe_channel = halbe_var.get()
                            order_obj.save()
                            
                            # Delete existing items
                            for oi in order_obj.order_items:
                                oi.delete_instance()
                            
                            # Create new items
                            for item_name, amount in order_items_data:
                                OrderItem.create(
                                    order=order_obj,
                                    item=self.app.items[item_name],
                                    amount=amount
                                )
                        else:  # Creating new order
                            if customer_cb is None:
                                messagebox.showerror("Error", "Customer selection is required.")
                                return
                            customer_name = customer_cb.get()
                            if customer_name not in self.app.customers:
                                messagebox.showerror("Error", "Invalid customer")
                                return
                            
                            # Calculate production date based on items
                            max_days = max(self.app.items[item_name].total_days for item_name, _ in order_items_data)
                            production_date = new_date - timedelta(days=max_days)
                            
                            order_obj = Order.create(
                                customer=self.app.customers[customer_name],
                                delivery_date=new_date,
                                production_date=production_date,
                                from_date=from_date,
                                to_date=to_date,
                                subscription_type=sub_var.get(),
                                halbe_channel=halbe_var.get(),
                                order_id=uuid.uuid4(),
                                is_future=False if new_date <= datetime.now().date() else True
                            )
                            
                            # Create order items
                            for item_name, amount in order_items_data:
                                OrderItem.create(
                                    order=order_obj,
                                    item=self.app.items[item_name],
                                    amount=amount
                                )
                            
                    elif update_type.get() == "future":
                        if not order_obj:
                            messagebox.showerror("Error", "Cannot update future orders for a new order.")
                            return
                        
                        # Find all subscription orders that are part of this subscription and in the future
                        today = datetime.now().date()
                        future_orders = list(Order.select().where(
                            (Order.from_date == order_obj.from_date) &
                            (Order.to_date == order_obj.to_date) &
                            (Order.delivery_date >= today)
                        ))
                        
                        # Update this order and all future orders
                        for future_order in future_orders:
                            # Only update the order if it's this order or it's in the future
                            if future_order.id == order_obj.id or future_order.delivery_date >= today:
                                # Update subscription properties
                                future_order.subscription_type = sub_var.get()
                                future_order.from_date = from_date
                                future_order.to_date = to_date
                                future_order.halbe_channel = halbe_var.get()
                                future_order.save()
                                
                                # Only update items for this specific order
                                if future_order.id == order_obj.id:
                                    # Delete existing items
                                    for oi in future_order.order_items:
                                        oi.delete_instance()
                                    
                                    # Create new items 
                                    for item_name, amount in order_items_data:
                                        OrderItem.create(
                                            order=future_order,
                                            item=self.app.items[item_name],
                                            amount=amount
                                        )
                        
                    elif update_type.get() == "new":
                        # Create a new subscription based on these settings
                        if not order_obj:
                            # Need customer for new order
                            if customer_cb is None:
                                messagebox.showerror("Error", "Customer selection is required.")
                                return
                            customer_name = customer_cb.get()
                            if customer_name not in self.app.customers:
                                messagebox.showerror("Error", "Invalid customer")
                                return
                            customer = self.app.customers[customer_name]
                        else:
                            # Use customer from existing order
                            customer = order_obj.customer
                        
                        # Calculate production date
                        max_days = max(self.app.items[item_name].total_days for item_name, _ in order_items_data)
                        production_date = new_date - timedelta(days=max_days)
                        
                        # Create the first order of the new subscription
                        new_order = Order.create(
                            customer=customer,
                            delivery_date=new_date,
                            production_date=production_date,
                            from_date=from_date,
                            to_date=to_date,
                            subscription_type=sub_var.get(),
                            halbe_channel=halbe_var.get(),
                            order_id=uuid.uuid4(),
                            is_future=False if new_date <= datetime.now().date() else True
                        )
                        
                        # Create order items
                        for item_name, amount in order_items_data:
                            OrderItem.create(
                                order=new_order,
                                item=self.app.items[item_name],
                                amount=amount
                            )
                        
                        # Generate future subscription orders if applicable
                        if sub_var.get() > 0:
                            future_orders = generate_subscription_orders(new_order)
                            for future_order_data in future_orders:
                                future_order = Order.create(
                                    **future_order_data,
                                    order_id=uuid.uuid4()
                                )
                                # Copy items to future order
                                for item_name, amount in order_items_data:
                                    OrderItem.create(
                                        order=future_order,
                                        item=self.app.items[item_name],
                                        amount=amount
                                    )
                
                messagebox.showinfo("Success", "Order saved successfully!")
                edit_window.destroy()
                self.refresh()
                
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
        
        # Create buttons frame
        buttons_frame = ttk.Frame(edit_window)
        buttons_frame.pack(fill='x', padx=10, pady=10)
        
        # Save Button
        save_btn = ttk.Button(buttons_frame, text="Save Changes", command=save_changes)
        save_btn.pack(side='right', padx=5)
        
        # Cancel Button
        cancel_btn = ttk.Button(buttons_frame, text="Cancel", command=edit_window.destroy)
        cancel_btn.pack(side='right', padx=5)
        
        # --- Delete Order Button ---
        if order:
            def delete_order():
                if messagebox.askyesno("Delete Order", "Are you sure you want to delete this order?"):
                    order.delete_instance(recursive=True)  # Deletes the order and its related items
                    messagebox.showinfo("Success", "Order deleted successfully!")
                    edit_window.destroy()
                    self.refresh()

            delete_btn = ttk.Button(buttons_frame, text="Delete Order", command=delete_order)
            delete_btn.pack(side='left', padx=5)
            
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
            
            # Update day labels
            if day in self.day_labels:
                self.day_labels[day].configure(text=day_label)
            
            # Get the frame for this day
            frame = self.day_frames[day]
            
            # Create a structured layout with a grid
            frame.columnconfigure(0, weight=1, minsize=100)  # Item column
            frame.columnconfigure(1, weight=0, minsize=70)   # Amount column
            
            # Add headers
            ttk.Label(frame, text="Item", font=('Arial', 12, 'bold')).grid(row=0, column=0, sticky='w', padx=5, pady=5)
            ttk.Label(frame, text="Amount", font=('Arial', 12, 'bold')).grid(row=0, column=1, sticky='e', padx=5, pady=5)
            
            # Add a separator
            separator = ttk.Separator(frame, orient='horizontal')
            separator.grid(row=1, column=0, columnspan=2, sticky='ew', padx=3, pady=3)
            
            # Filter production items for this day
            day_production = []
            for prod in production_data:
                if prod.order.production_date.weekday() == i:
                    day_production.append(prod)
            
            # Sort items alphabetically for better organization
            day_production.sort(key=lambda x: x.item.name)
            
            # Add each production item in a grid layout
            row_index = 2  # Start after header and separator
            for prod in day_production:
                # Item name
                item_label = ttk.Label(frame, text=prod.item.name, font=('Arial', 11))
                item_label.grid(row=row_index, column=0, sticky='w', padx=5, pady=3)
                
                # Amount with right alignment
                amount_label = ttk.Label(frame, text=f"{prod.total_amount:.1f}", font=('Arial', 11))
                amount_label.grid(row=row_index, column=1, sticky='e', padx=5, pady=3)
                
                # Add a separator between items
                row_index += 1
                if prod != day_production[-1]:  # Don't add separator after the last item
                    item_separator = ttk.Separator(frame, orient='horizontal')
                    item_separator.grid(row=row_index, column=0, columnspan=2, sticky='ew', padx=15, pady=2)
                    row_index += 1
                    
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
            
            # Update day labels
            if day in self.day_labels:
                self.day_labels[day].configure(text=day_label)
            
            # Get the frame for this day
            frame = self.day_frames[day]
            
            # Create a structured layout with a grid
            # Set up two columns with fixed width
            frame.columnconfigure(0, weight=1, minsize=100)  # Item column
            frame.columnconfigure(1, weight=0, minsize=70)   # Amount column
            
            # Add headers
            ttk.Label(frame, text="Item", font=('Arial', 12, 'bold')).grid(row=0, column=0, sticky='w', padx=5, pady=5)
            ttk.Label(frame, text="Amount", font=('Arial', 12, 'bold')).grid(row=0, column=1, sticky='e', padx=5, pady=5)
            
            # Add a separator
            separator = ttk.Separator(frame, orient='horizontal')
            separator.grid(row=1, column=0, columnspan=2, sticky='ew', padx=3, pady=3)
            
            # Filter transfers for this day
            day_transfers = []
            for transfer in transfer_data:
                if transfer['date'].weekday() == i:
                    day_transfers.append(transfer)
            
            # Sort items alphabetically for better organization
            day_transfers.sort(key=lambda x: x['item'])
            
            # Add each transfer item in a grid layout
            row_index = 2  # Start after header and separator
            for transfer in day_transfers:
                # Item name
                item_label = ttk.Label(frame, text=transfer['item'], font=('Arial', 11))
                item_label.grid(row=row_index, column=0, sticky='w', padx=5, pady=3)
                
                # Amount with right alignment
                amount_label = ttk.Label(frame, text=f"{transfer['amount']:.1f}", font=('Arial', 11))
                amount_label.grid(row=row_index, column=1, sticky='e', padx=5, pady=3)
                
                # Add substrate info if available
                if 'substrate' in transfer:
                    row_index += 1
                    substrate_text = f"Substrate: {transfer['substrate']}"
                    substrate_label = ttk.Label(frame, text=substrate_text, font=('Arial', 9))
                    substrate_label.grid(row=row_index, column=0, columnspan=2, sticky='w', padx=15, pady=1)
                
                # Add a separator between items
                row_index += 1
                if transfer != day_transfers[-1]:  # Don't add separator after the last item
                    item_separator = ttk.Separator(frame, orient='horizontal')
                    item_separator.grid(row=row_index, column=0, columnspan=2, sticky='ew', padx=15, pady=2)
                    row_index += 1
                    
def format_date(date):
    """Format date as DD.MM.YYYY"""
    return date.strftime('%d.%m.%Y')