
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sqlite3

# Constants
TOLERANCE = 0.2
DEFAULT_PASSWORD = "1234"
DATABASE_FOLDER = "database"

# Ensure database folder exists
if not os.path.exists(DATABASE_FOLDER):
    os.makedirs(DATABASE_FOLDER)

# Automatically connect to a database in the folder if exists, otherwise create a default one
default_db_path = os.path.join(DATABASE_FOLDER, "default.db")
if not os.path.exists(default_db_path):
    open(default_db_path, 'w').close()

# Database handler
class ComponentDB:
    def __init__(self):
        self.connections = {}
        self.active_db = None
        self.connect(default_db_path)

    def connect(self, db_path):
        conn = sqlite3.connect(db_path)
        self.connections[db_path] = conn
        self.active_db = db_path
        self._create_table(conn)
        return db_path

    def _create_table(self, conn):
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                pin INTEGER,
                voltage REAL
            )
        """)
        conn.commit()

    def insert_component(self, name, voltages):
        if not self.active_db:
            raise Exception("No active database connected.")
        conn = self.connections[self.active_db]
        c = conn.cursor()
        c.execute("DELETE FROM components WHERE name = ?", (name,))
        for i, voltage in enumerate(voltages, start=1):
            c.execute("INSERT INTO components (name, pin, voltage) VALUES (?, ?, ?)", (name, i, voltage))
        conn.commit()

    def get_component_data(self, name):
        if not self.active_db:
            return []
        conn = self.connections[self.active_db]
        c = conn.cursor()
        c.execute("SELECT pin, voltage FROM components WHERE name = ? ORDER BY pin", (name,))
        return c.fetchall()

    def get_similar_names(self, prefix):
        if not self.active_db:
            return []
        conn = self.connections[self.active_db]
        c = conn.cursor()
        c.execute("SELECT DISTINCT name FROM components WHERE name LIKE ?", (prefix + '%',))
        return [row[0] for row in c.fetchall()]

    def delete_component(self, name):
        if not self.active_db:
            return
        conn = self.connections[self.active_db]
        c = conn.cursor()
        c.execute("DELETE FROM components WHERE name = ?", (name,))
        conn.commit()


class ComponentTesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Component Tester")
        self.db = ComponentDB()
        self.pin_entries = []
        self.build_gui()

    def build_gui(self):
        top_menu = tk.Menu(self.root)
        self.root.config(menu=top_menu)
        file_menu = tk.Menu(top_menu, tearoff=0)
        file_menu.add_command(label="Import Database", command=self.import_database)
        top_menu.add_cascade(label="File", menu=file_menu)

        self.name_var = tk.StringVar()
        self.pin_count_var = tk.IntVar(value=2)

        name_frame = ttk.Frame(self.root, padding=10)
        name_frame.pack(fill='x')
        ttk.Label(name_frame, text="Component Name:").pack(side='left')
        self.name_entry = ttk.Entry(name_frame, textvariable=self.name_var)
        self.name_entry.pack(side='left', padx=5)
        self.name_entry.bind("<KeyRelease>", self.search_component_names)

        self.suggestion_listbox = tk.Listbox(name_frame, height=3)
        self.suggestion_listbox.pack(side='left', padx=5)
        self.suggestion_listbox.bind("<<ListboxSelect>>", self.load_selected_component)

        pin_frame = ttk.Frame(self.root, padding=10)
        pin_frame.pack(fill='x')
        ttk.Label(pin_frame, text="Pin Count:").pack(side='left')
        pin_dropdown = ttk.Combobox(pin_frame, textvariable=self.pin_count_var, values=[2,3,4,6,8], state='readonly')
        pin_dropdown.pack(side='left', padx=5)
        pin_dropdown.bind("<<ComboboxSelected>>", lambda e: self.render_pin_entries())

        self.pin_entry_frame = ttk.Frame(self.root, padding=10)
        self.pin_entry_frame.pack(fill='x')
        self.render_pin_entries()

        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill='x')
        ttk.Button(btn_frame, text="Save as Healthy", command=self.save_healthy).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Test Component", command=self.test_component).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_component).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Export Results", command=self.export_results).pack(side='left', padx=5)

        self.tree = ttk.Treeview(self.root, columns=("Name", "Pin", "Input", "Expected", "Result"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)

    def render_pin_entries(self):
        for widget in self.pin_entry_frame.winfo_children():
            widget.destroy()
        self.pin_entries = []
        for i in range(self.pin_count_var.get()):
            ttk.Label(self.pin_entry_frame, text=f"Pin {i+1}:").grid(row=i, column=0, sticky='e')
            var = tk.StringVar()
            entry = ttk.Entry(self.pin_entry_frame, textvariable=var)
            entry.grid(row=i, column=1, padx=5, pady=2)
            self.pin_entries.append(var)

    def save_healthy(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Enter a component name.")
            return
        try:
            voltages = [round(float(v.get()), 2) for v in self.pin_entries]
            existing = self.db.get_component_data(name)
            if existing:
                password = simpledialog.askstring("Password", "Enter password to overwrite:", show="*")
                if password != DEFAULT_PASSWORD:
                    messagebox.showerror("Denied", "Incorrect password. Save cancelled.")
                    return
            self.db.insert_component(name, voltages)
            messagebox.showinfo("Saved", f"Component '{name}' saved as healthy.")
            self.clear_entries()
        except ValueError:
            messagebox.showerror("Error", "Invalid voltage values.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save component: {str(e)}")

    def test_component(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Enter a component name.")
            return
        try:
            entered_voltages = [round(float(v.get()), 2) for v in self.pin_entries]
            reference_data = self.db.get_component_data(name)
            if not reference_data:
                messagebox.showwarning("Not found", "Component not found in database.")
                return

            expected = {pin: v for pin, v in reference_data}
            matched = 0
            mismatches = []

            for pin, val in enumerate(entered_voltages, start=1):
                ref = expected.get(pin)
                if ref is not None:
                    if abs(val - ref) <= TOLERANCE:
                        matched += 1
                        status = "OK"
                    else:
                        status = f"Fail"
                        mismatches.append((pin, ref, val))
                    self.tree.insert("", "end", values=(name, pin, val, ref, status))

            percentage = matched / len(expected) * 100
            msg = f"Match: {percentage:.0f}%\n"
            if percentage >= 90:
                msg += "✅ Component is healthy"
            else:
                msg += "❌ Component is possibly faulty"
                for pin, correct, actual in mismatches:
                    msg += f"\n- Pin {pin}: expected {correct}V, got {actual}V"

            messagebox.showinfo("Test Result", msg)
        except ValueError:
            messagebox.showerror("Error", "Invalid voltage values.")

    def export_results(self):
        if not self.tree.get_children():
            messagebox.showwarning("No data", "No results to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if not path:
            return
        with open(path, "w") as f:
            for row in self.tree.get_children():
                values = self.tree.item(row)["values"]
                f.write(", ".join(str(v) for v in values) + "\n")
        for item in self.tree.get_children():
            self.tree.delete(item)
        messagebox.showinfo("Exported", f"Results saved to {path}")

    def import_database(self):
        path = filedialog.askopenfilename(defaultextension=".db", filetypes=[("SQLite DB", "*.db")])
        if not path:
            return
        if not os.path.exists(path):
            open(path, 'w').close()
        name = self.db.connect(path)
        messagebox.showinfo("Connected", f"Connected to database: {name}")

    def delete_component(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Enter a component name to delete.")
            return
        if not self.db.get_component_data(name):
            messagebox.showinfo("Info", "Component not found in database.")
            return
        password = simpledialog.askstring("Password", "Enter password to delete:", show="*")
        if password != DEFAULT_PASSWORD:
            messagebox.showerror("Denied", "Incorrect password. Deletion cancelled.")
            return
        self.db.delete_component(name)
        messagebox.showinfo("Deleted", f"Component '{name}' deleted from database.")
        self.clear_entries()

    def search_component_names(self, event=None):
        prefix = self.name_var.get().strip()
        if not prefix or not self.db.active_db:
            self.suggestion_listbox.delete(0, tk.END)
            return
        try:
            names = self.db.get_similar_names(prefix)
            self.suggestion_listbox.delete(0, tk.END)
            for name in names:
                self.suggestion_listbox.insert(tk.END, name)
        except Exception as e:
            print("Search error:", str(e))

    def load_selected_component(self, event=None):
        if not self.suggestion_listbox.curselection():
            return
        index = self.suggestion_listbox.curselection()[0]
        selected = self.suggestion_listbox.get(index)
        self.name_var.set(selected)
        data = self.db.get_component_data(selected)
        self.pin_count_var.set(len(data))
        self.render_pin_entries()
        for pin, voltage in data:
            if pin <= len(self.pin_entries):
                self.pin_entries[pin - 1].set(str(voltage))

    def clear_entries(self):
        self.name_var.set("")
        for v in self.pin_entries:
            v.set("")
        self.suggestion_listbox.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ComponentTesterApp(root)
    root.mainloop()
