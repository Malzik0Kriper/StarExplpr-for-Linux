import os
import shutil
import datetime
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

class TinyStarExplor(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Парамитри ВІКНА
        self.title("StarExplor")
        self.geometry("450x300")
        
        # Кольорои 
        self.bg_dark = "#202020"
        self.bg_field = "#2d2d2d"
        self.fg_white = "#e0e0e0"
        self.accent = "#3d3d3d"
        self.highlight = "#4b6eaf"
        
        self.configure(bg=self.bg_dark)
        
        self.current_path = str(Path.home())
        self.history = [self.current_path]
        self.history_index = 0
        self.selected_items = []
        self.clipboard_items = []
        self.clipboard_operation = None
        
        self.setup_styles()
        self.create_widgets()
        self.create_context_menu()
        self.load_directory()
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Стилізація таблиці
        style.configure("Treeview", 
                        background=self.bg_field, 
                        foreground=self.fg_white, 
                        fieldbackground=self.bg_field,
                        borderwidth=0,
                        font=('Arial', 9))
        style.map("Treeview", background=[('selected', self.highlight)])
        
        style.configure("Treeview.Heading", 
                        background=self.bg_dark, 
                        foreground=self.fg_white, 
                        relief="flat",
                        font=('Arial', 9, 'bold'))
        style.map("Treeview.Heading", background=[('active', self.accent)])

    def create_widgets(self):
        # Панель навігації
        self.nav_frame = tk.Frame(self, bg=self.bg_dark, height=40)
        self.nav_frame.pack(fill="x", padx=5, pady=5)
        self.nav_frame.pack_propagate(False)
        
        btn_opts = {"bg": self.accent, "fg": self.fg_white, "relief": "flat", 
                    "activebackground": self.highlight, "font": ("Arial", 8)}
        
        tk.Button(self.nav_frame, text="Назад", command=self.go_back, **btn_opts).pack(side="left", padx=2)
        tk.Button(self.nav_frame, text="Вперед", command=self.go_forward, **btn_opts).pack(side="left", padx=2)
        tk.Button(self.nav_frame, text="Оновити", command=self.load_directory, **btn_opts).pack(side="left", padx=2)

        self.path_entry = tk.Entry(self.nav_frame, bg=self.bg_field, fg=self.fg_white, 
                                   insertbackground="white", relief="flat")
        self.path_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.path_entry.bind("<Return>", lambda e: self.navigate_to_path())
        
        # Робоча область
        self.main_frame = tk.Frame(self, bg=self.bg_dark)
        self.main_frame.pack(fill="both", expand=True, padx=5)
        
        columns = ('size', 'modified')
        self.tree = ttk.Treeview(self.main_frame, columns=columns, show='tree headings')
        
        self.tree.heading('#0', text='Назва', command=lambda: self.sort_column('#0', False))
        self.tree.heading('size', text='Розмір', command=lambda: self.sort_column('size', False))
        self.tree.heading('modified', text='Змінено', command=lambda: self.sort_column('modified', False))
        
        self.tree.column('#0', width=180)
        self.tree.column('size', width=70)
        self.tree.column('modified', width=120)
        
        self.tree.pack(fill="both", expand=True)
        
        self.tree.bind('<Double-Button-1>', lambda e: self.open_selected())
        self.tree.bind('<Button-3>', self.show_context_menu)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        
        self.status_bar = tk.Label(self, text="", anchor="w", bg=self.bg_dark, fg="#888888", font=('Arial', 8))
        self.status_bar.pack(fill="x", padx=5)

    def create_context_menu(self):
        self.menu = tk.Menu(self, tearoff=0, bg=self.bg_field, fg=self.fg_white, activebackground=self.highlight)
        self.menu.add_command(label="Відкрити", command=self.open_selected)
        self.menu.add_separator()
        self.menu.add_command(label="Нова папка", command=self.create_folder)
        self.menu.add_command(label="Новий файл", command=self.create_file)
        self.menu.add_separator()
        self.menu.add_command(label="Копіювати", command=self.copy_items)
        self.menu.add_command(label="Вирізати", command=self.cut_items)
        self.menu.add_command(label="Вставити", command=self.paste_items)
        self.menu.add_separator()
        self.menu.add_command(label="Перейменувати", command=self.rename_item)
        self.menu.add_command(label="Видалити", command=self.delete_items)
        self.menu.add_separator()
        self.menu.add_command(label="Властивості", command=self.show_properties)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
        self.menu.post(event.x_root, event.y_root)

    def load_directory(self):
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, self.current_path)
            
            items = sorted(os.scandir(self.current_path), key=lambda x: (not x.is_dir(), x.name.lower()))
            for entry in items:
                try:
                    stat = entry.stat()
                    size = self.format_size(stat.st_size) if entry.is_file() else ""
                    modified = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
                    self.tree.insert('', 'end', text=entry.name, values=(size, modified), tags=(entry.path,))
                except: continue
            self.status_bar.configure(text=f"Елементів: {len(items)}")
        except Exception as e:
            messagebox.showerror("Помилка", f"Доступ обмежено: {e}")

    def sort_column(self, col, reverse):
        l = [(self.tree.set(k, col) if col != '#0' else self.tree.item(k, 'text'), k) for k in self.tree.get_children('')]
        l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def format_size(self, size):
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024: return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} ТБ"

    def open_selected(self):
        if self.selected_items:
            path = self.selected_items[0]
            if os.path.isdir(path):
                self.current_path = path
                self.history = self.history[:self.history_index + 1]
                self.history.append(path)
                self.history_index = len(self.history) - 1
                self.load_directory()
            else:
                try:
                    if os.name == 'nt': os.startfile(path)
                    else: subprocess.Popen(['xdg-open', path])
                except: self.show_properties()

    def show_properties(self):
        if not self.selected_items: return
        path = self.selected_items[0]
        stats = os.stat(path)
        
        prop_win = tk.Toplevel(self)
        prop_win.title("Властивості")
        prop_win.geometry("320x220")
        prop_win.configure(bg=self.bg_field)
        prop_win.resizable(False, False)
        
        container = tk.Frame(prop_win, bg=self.bg_field, padx=15, pady=15)
        container.pack(fill="both", expand=True)
        
        info = [
            ("Назва:", os.path.basename(path)),
            ("Тип:", "Папка" if os.path.isdir(path) else "Файл"),
            ("Розмір:", self.format_size(stats.st_size)),
            ("Змінено:", datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%d.%m.%Y %H:%M")),
            ("Шлях:", path)
        ]
        
        for label, val in info:
            f = tk.Frame(container, bg=self.bg_field)
            f.pack(fill="x", pady=2)
            tk.Label(f, text=label, bg=self.bg_field, fg="#aaaaaa", font=("Arial", 9, "bold")).pack(side="left")
            tk.Label(f, text=val, bg=self.bg_field, fg=self.fg_white, font=("Arial", 9), wraplength=220, justify="left").pack(side="left", padx=5)

    def navigate_to_path(self):
        path = self.path_entry.get()
        if os.path.isdir(path):
            self.current_path = path
            self.load_directory()
        else:
            messagebox.showerror("Помилка", "Шлях не знайдено")

    def go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.current_path = self.history[self.history_index]
            self.load_directory()

    def go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_path = self.history[self.history_index]
            self.load_directory()

    def on_select(self, event):
        self.selected_items = [self.tree.item(i, 'tags')[0] for i in self.tree.selection()]

    def create_folder(self):
        name = simpledialog.askstring("Папка", "Назва:")
        if name:
            os.makedirs(os.path.join(self.current_path, name), exist_ok=True)
            self.load_directory()

    def create_file(self):
        name = simpledialog.askstring("Файл", "Назва:")
        if name:
            Path(os.path.join(self.current_path, name)).touch()
            self.load_directory()

    def copy_items(self):
        self.clipboard_items = self.selected_items.copy()
        self.clipboard_operation = 'copy'

    def cut_items(self):
        self.clipboard_items = self.selected_items.copy()
        self.clipboard_operation = 'cut'

    def paste_items(self):
        if not self.clipboard_items: return
        for item in self.clipboard_items:
            dest = os.path.join(self.current_path, os.path.basename(item))
            if self.clipboard_operation == 'copy':
                if os.path.isdir(item): shutil.copytree(item, dest, dirs_exist_ok=True)
                else: shutil.copy2(item, dest)
            else: shutil.move(item, dest)
        self.load_directory()

    def delete_items(self):
        if messagebox.askyesno("Видалення", "Видалити вибране?"):
            for item in self.selected_items:
                if os.path.isdir(item): shutil.rmtree(item)
                else: os.remove(item)
            self.load_directory()

    def rename_item(self):
        if not self.selected_items: return
        old = self.selected_items[0]
        new_name = simpledialog.askstring("Назва", "Нова назва:", initialvalue=os.path.basename(old))
        if new_name:
            os.rename(old, os.path.join(os.path.dirname(old), new_name))
            self.load_directory()

if __name__ == "__main__":
    app = TinyStarExplor()
    app.mainloop()
