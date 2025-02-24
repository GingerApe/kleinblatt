# Modify your customer_view.py
from tkinter import messagebox, ttk
from widgets import AutocompleteCombobox
from database import Customer

class CustomerView:
    def __init__(self, parent):
        self.parent = parent
        self.edit_mode = False
        self.current_customer = None
        self.create_widgets()
        self.refresh_customer_list()

    def create_widgets(self):
        # Input frame
        input_frame = ttk.LabelFrame(self.parent, text="Customer Details")
        input_frame.pack(fill='x', padx=10, pady=5)

        # Customer name input with autocomplete
        ttk.Label(input_frame, text="Name:").grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = AutocompleteCombobox(input_frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        # Buttons
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)

        self.save_btn = ttk.Button(btn_frame, text="Save", command=self.save_customer)
        self.save_btn.pack(side='left', padx=5)

        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.cancel_edit)
        self.cancel_btn.pack(side='left', padx=5)
        self.cancel_btn.pack_forget()  # Hidden by default

        # Customer list
        list_frame = ttk.LabelFrame(self.parent, text="Customer List")
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Treeview for customer list
        self.tree = ttk.Treeview(list_frame, columns=('ID', 'Name', 'Created'), show='headings')
        self.tree.heading('ID', text='ID')
        self.tree.heading('Name', text='Name')
        self.tree.heading('Created', text='Created')
        self.tree.pack(fill='both', expand=True, padx=5, pady=5)

        # Add Edit and Delete buttons
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Edit", command=self.edit_customer).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_customer).pack(side='left', padx=5)

    def refresh_customer_list(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Fetch and display customers
        customers = Customer.select()
        for customer in customers:
            self.tree.insert('', 'end', values=(customer.id, customer.name, 
                                              customer.created_at.strftime('%Y-%m-%d %H:%M')))

        # Update autocomplete list
        self.name_entry.set_completion_list([c.name for c in customers])

    def save_customer(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter a customer name")
            return

        try:
            if self.edit_mode and self.current_customer:
                # Update existing customer
                self.current_customer.name = name
                self.current_customer.save()
                messagebox.showinfo("Success", "Customer updated successfully")
            else:
                # Create new customer
                Customer.create(name=name)
                messagebox.showinfo("Success", "Customer added successfully")

            self.cancel_edit()
            self.refresh_customer_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def edit_customer(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a customer to edit")
            return

        # Get customer ID from selected item
        customer_id = self.tree.item(selected_item[0])['values'][0]
        self.current_customer = Customer.get_by_id(customer_id)

        # Set edit mode
        self.edit_mode = True
        self.name_entry.set(self.current_customer.name)
        self.save_btn.configure(text="Update")
        self.cancel_btn.pack(side='left', padx=5)

    def cancel_edit(self):
        self.edit_mode = False
        self.current_customer = None
        self.name_entry.set('')
        self.save_btn.configure(text="Save")
        self.cancel_btn.pack_forget()

    def delete_customer(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a customer to delete")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this customer?"):
            customer_id = self.tree.item(selected_item[0])['values'][0]
            customer = Customer.get_by_id(customer_id)
            customer.delete_instance()
            self.refresh_customer_list()