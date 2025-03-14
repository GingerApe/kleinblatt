import tkinter as tk
from tkinter import ttk, messagebox
from widgets import AutocompleteCombobox
from models import Item
from datetime import datetime

class ItemView:
    def __init__(self, parent):
        self.parent = parent
        self.edit_mode = False
        self.current_item = None
        self.create_widgets()
        self.refresh_item_list()

    def create_widgets(self):
        # Input frame
        input_frame = ttk.LabelFrame(self.parent, text="Item Details")
        input_frame.pack(fill='x', padx=10, pady=5)

        # Grid layout for item details
        # Name with autocomplete
        ttk.Label(input_frame, text="Name:").grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = AutocompleteCombobox(input_frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        # Seed quantity
        ttk.Label(input_frame, text="Seed Quantity (g):").grid(row=1, column=0, padx=5, pady=5)
        self.seed_qty_entry = ttk.Entry(input_frame)
        self.seed_qty_entry.grid(row=1, column=1, padx=5, pady=5)

        # Days inputs
        ttk.Label(input_frame, text="Soaking Days:").grid(row=2, column=0, padx=5, pady=5)
        self.soaking_days_entry = ttk.Entry(input_frame)
        self.soaking_days_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="Germination Days:").grid(row=3, column=0, padx=5, pady=5)
        self.germination_days_entry = ttk.Entry(input_frame)
        self.germination_days_entry.grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="Growth Days:").grid(row=4, column=0, padx=5, pady=5)
        self.growth_days_entry = ttk.Entry(input_frame)
        self.growth_days_entry.grid(row=4, column=1, padx=5, pady=5)

        # Price
        ttk.Label(input_frame, text="Price:").grid(row=5, column=0, padx=5, pady=5)
        self.price_entry = ttk.Entry(input_frame)
        self.price_entry.grid(row=5, column=1, padx=5, pady=5)

        # Substrate
        ttk.Label(input_frame, text="Substrate:").grid(row=6, column=0, padx=5, pady=5)
        self.substrate_entry = ttk.Entry(input_frame)
        self.substrate_entry.grid(row=6, column=1, padx=5, pady=5)

        # Buttons
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=10)

        self.save_btn = ttk.Button(btn_frame, text="Save", command=self.save_item)
        self.save_btn.pack(side='left', padx=5)

        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.cancel_edit)
        self.cancel_btn.pack(side='left', padx=5)
        self.cancel_btn.pack_forget()  # Hidden by default

        # Item list
        list_frame = ttk.LabelFrame(self.parent, text="Item List")
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Treeview for item list
        self.tree = ttk.Treeview(list_frame, columns=(
            'ID', 'Name', 'Seed Qty', 'Soaking', 'Germination', 
            'Growth', 'Price', 'Substrate'), show='headings')
        
        # Configure column headings
        self.tree.heading('ID', text='ID')
        self.tree.heading('Name', text='Name')
        self.tree.heading('Seed Qty', text='Seed Qty (g)')
        self.tree.heading('Soaking', text='Soaking Days')
        self.tree.heading('Germination', text='Germination Days')
        self.tree.heading('Growth', text='Growth Days')
        self.tree.heading('Price', text='Price')
        self.tree.heading('Substrate', text='Substrate')

        # Configure column widths
        self.tree.column('ID', width=50)
        self.tree.column('Name', width=150)
        self.tree.column('Seed Qty', width=100)
        self.tree.column('Soaking', width=100)
        self.tree.column('Germination', width=100)
        self.tree.column('Growth', width=100)
        self.tree.column('Price', width=100)
        self.tree.column('Substrate', width=100)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y')

        # Action buttons
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Edit", command=self.edit_item).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_item).pack(side='left', padx=5)

    def refresh_item_list(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Fetch and display items
        items = Item.select()
        for item in items:
            self.tree.insert('', 'end', values=(
                item.id, 
                item.name,
                f"{item.seed_quantity:.1f}",
                item.soaking_days,
                item.germination_days,
                item.growth_days,
                f"{item.price:.2f}",
                item.substrate or ""
            ))

        # Update autocomplete list
        self.name_entry.set_completion_list([item.name for item in items])

    def save_item(self):
        # Validate inputs
        try:
            name = self.name_entry.get().strip()
            seed_qty = float(self.seed_qty_entry.get())
            soaking_days = int(self.soaking_days_entry.get())
            germination_days = int(self.germination_days_entry.get())
            growth_days = int(self.growth_days_entry.get())
            price = float(self.price_entry.get())
            substrate = self.substrate_entry.get().strip()

            if not name:
                raise ValueError("Please enter an item name")

        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        try:
            if self.edit_mode and self.current_item:
                # Update existing item
                self.current_item.name = name
                self.current_item.seed_quantity = seed_qty
                self.current_item.soaking_days = soaking_days
                self.current_item.germination_days = germination_days
                self.current_item.growth_days = growth_days
                self.current_item.price = price
                self.current_item.substrate = substrate
                self.current_item.save()
                messagebox.showinfo("Success", "Item updated successfully")
            else:
                # Create new item
                Item.create(
                    name=name,
                    seed_quantity=seed_qty,
                    soaking_days=soaking_days,
                    germination_days=germination_days,
                    growth_days=growth_days,
                    price=price,
                    substrate=substrate
                )
                messagebox.showinfo("Success", "Item added successfully")

            self.cancel_edit()
            self.refresh_item_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def edit_item(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select an item to edit")
            return

        # Get item ID from selected item
        item_id = self.tree.item(selected_item[0])['values'][0]
        self.current_item = Item.get_by_id(item_id)

        # Populate form with current values
        self.name_entry.set(self.current_item.name)
        self.seed_qty_entry.delete(0, tk.END)
        self.seed_qty_entry.insert(0, str(self.current_item.seed_quantity))
        self.soaking_days_entry.delete(0, tk.END)
        self.soaking_days_entry.insert(0, str(self.current_item.soaking_days))
        self.germination_days_entry.delete(0, tk.END)
        self.germination_days_entry.insert(0, str(self.current_item.germination_days))
        self.growth_days_entry.delete(0, tk.END)
        self.growth_days_entry.insert(0, str(self.current_item.growth_days))
        self.price_entry.delete(0, tk.END)
        self.price_entry.insert(0, str(self.current_item.price))
        self.substrate_entry.delete(0, tk.END)
        self.substrate_entry.insert(0, self.current_item.substrate or "")

        # Set edit mode
        self.edit_mode = True
        self.save_btn.configure(text="Update")
        self.cancel_btn.pack(side='left', padx=5)

    def cancel_edit(self):
        self.edit_mode = False
        self.current_item = None
        
        # Clear all entries
        self.name_entry.set('')
        self.seed_qty_entry.delete(0, tk.END)
        self.soaking_days_entry.delete(0, tk.END)
        self.germination_days_entry.delete(0, tk.END)
        self.growth_days_entry.delete(0, tk.END)
        self.price_entry.delete(0, tk.END)
        self.substrate_entry.delete(0, tk.END)
        
        self.save_btn.configure(text="Save")
        self.cancel_btn.pack_forget()

    def delete_item(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select an item to delete")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this item?"):
            item_id = self.tree.item(selected_item[0])['values'][0]
            item = Item.get_by_id(item_id)
            item.delete_instance()
            self.refresh_item_list()