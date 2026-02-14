import os
import shutil
import datetime
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, font

class FileExplorer(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Головне вікно
        self.title("StarExplor")
        self.geometry("450x300")
        
        # Кольори вікна
        self.bg_main = "#2b2b2b"
        self.bg_secondary = "#3c3f41"
        self.fg_text = "#ffffff"
        self.accent = "#4e5154"
        
        self.configure(bg=self.bg_main)
        
        self.current_path = str(Path.home())
        self.history = [self.current_path]
        self.history_index = 0
        
        self.clipboard_items = []
        self.clipboard_operation = None
        self.selected_items = []
        
        self.setup_styles()
        self.create_widgets()
        self.create_context_menu()
        self.load_directory()
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Стилізація таблиці (Treeview)
        style.configure("Treeview", 
                        background=self.bg_secondary, 
                        foreground=self.fg_text, 
                        fieldbackground=self.bg_secondary,
                        borderwidth=0,
                        font=('Arial', 9))
        style.map("Treeview", background=[('selected', '#4b6eaf')])
        
        style.configure("Treeview.Heading", 
                        background=self.bg_main, 
                        foreground=self.fg_text, 
                        relief="flat",
                        font=('Arial', 9, 'bold'))
        
        # Стилізація смуги прокрутки
        style.configure("Vertical.TScrollbar", gripcount=0, background=self.bg_main, troughcolor=self.bg_secondary)

    def create_widgets(self):
        # Панель навігації
        self.nav_frame = tk.Frame(self, bg=self.bg_main, height=40)
        self.nav_frame.pack(fill="x", padx=5, pady=5)
        self.nav_frame.pack_propagate(False)
        
        btn_opts = {"bg": self.accent, "fg": self.fg_text, "relief": "flat", "activebackground": "#5c5e60", "font": ("Arial", 8)}
        
        tk.Button(self.nav_frame, text="Назад", command=self.go_back, **btn_opts).pack(side="left", padx=2)
        tk.Button(self.nav_frame, text="Вперед", command=self.go_forward, **btn_opts).pack(side="left", padx=2)
        tk.Button(self.nav_frame, text="Оновити", command=self.load_directory, **btn_opts).pack(side="left", padx=2)

        self.path_entry = tk.Entry(self.nav_frame, bg=self.bg_secondary, fg=self.fg_text, insertbackground="white", relief="flat", borderwidth=5)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.path_entry.bind("<Return>", lambda e: self.navigate_to_path())
        
        # РобоЧа ОБЛАСТЬ
        self.main_frame = tk.Frame(self, bg=self.bg_main)
        self.main_frame.pack(fill="both", expand=True, padx=5, pady=0)
        
        columns = ('size', 'modified')
        self.tree = ttk.Treeview(self.main_frame, columns=columns, show='tree headings', selectmode='extended')
        
        self.tree.heading('#0', text='Назва')
        self.tree.heading('size', text='Розмір')
        self.tree.heading('modified', text='Змінено')
        
        self.tree.column('#0', width=180)
        self.tree.column('size', width=70)
        self.tree.column('modified', width=120)
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        # Прокрутка
        scroller = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroller.set)
        scroller.pack(side="right", fill="y")
        
        # Прив'язки
        self.tree.bind('<Double-Button-1>', lambda e: self.open_selected())
        self.tree.bind('<Button-3>', self.show_context_menu)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        
        # Статус бар
        self.status_bar = tk.Label(self, text="Готово", anchor="w", bg=self.bg_main, fg="#888888", font=('Arial', 8))
        self.status_bar.pack(fill="x", padx=5)

    def create_context_menu(self):
        self.menu = tk.Menu(self, tearoff=0, bg=self.bg_secondary, fg=self.fg_text, activebackground="#4b6eaf")
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
            messagebox.showerror("Помилка", f"Доступ заборонено: {e}")

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
        
        # Створення Вкна Властивостей
        prop_win = tk.Toplevel(self)
        prop_win.title("Властивості")
        prop_win.geometry("300x200")
        prop_win.configure(bg=self.bg_secondary)
        prop_win.resizable(False, False)
        
        container = tk.Frame(prop_win, bg=self.bg_secondary, padx=15, pady=15)
        container.pack(fill="both", expand=True)
        
        info = [
            ("Назва:", os.path.basename(path)),
            ("Тип:", "Папка" if os.path.isdir(path) else "Файл"),
            ("Розмір:", self.format_size(stats.st_size)),
            ("Змінено:", datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%d.%m.%Y %H:%M")),
            ("Шлях:", path)
        ]
        
        for label, val in info:
            f = tk.Frame(container, bg=self.bg_secondary)
            f.pack(fill="x", pady=2)
            tk.Label(f, text=label, bg=self.bg_secondary, fg="#aaaaaa", font=("Arial", 9, "bold")).pack(side="left")
            tk.Label(f, text=val, bg=self.bg_secondary, fg=self.fg_text, font=("Arial", 9), wraplength=200, justify="left").pack(side="left", padx=5)

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
        name = simpledialog.askstring("Папка", "Назва папки:")
        if name:
            try:
                os.makedirs(os.path.join(self.current_path, name), exist_ok=True)
                self.load_directory()
            except Exception as e: messagebox.showerror("Помилка", str(e))

    def create_file(self):
        name = simpledialog.askstring("Файл", "Назва файлу:")
        if name:
            try:
                Path(os.path.join(self.current_path, name)).touch()
                self.load_directory()
            except Exception as e: messagebox.showerror("Помилка", str(e))

    def copy_items(self):
        self.clipboard_items = self.selected_items.copy()
        self.clipboard_operation = 'copy'
        self.status_bar.configure(text="Скопійовано в буфер")

    def cut_items(self):
        self.clipboard_items = self.selected_items.copy()
        self.clipboard_operation = 'cut'
        self.status_bar.configure(text="Вирізано в буфер")

    def paste_items(self):
        if not self.clipboard_items: return
        try:
            for item in self.clipboard_items:
                dest = os.path.join(self.current_path, os.path.basename(item))
                if self.clipboard_operation == 'copy':
                    if os.path.isdir(item): shutil.copytree(item, dest, dirs_exist_ok=True)
                    else: shutil.copy2(item, dest)
                else:
                    shutil.move(item, dest)
            self.load_directory()
        except Exception as e: messagebox.showerror("Помилка", str(e))

    def delete_items(self):
        if not self.selected_items: return
        if messagebox.askyesno("Видалення", f"Видалити {len(self.selected_items)} ел.?"):
            try:
                for item in self.selected_items:
                    if os.path.isdir(item): shutil.rmtree(item)
                    else: os.remove(item)
                self.load_directory()
            except Exception as e: messagebox.showerror("Помилка", str(e))

    def rename_item(self):
        if not self.selected_items: return
        old = self.selected_items[0]
        new_name = simpledialog.askstring("Назва", "Нова назва:", initialvalue=os.path.basename(old))
        if new_name:
            try:
                os.rename(old, os.path.join(os.path.dirname(old), new_name))
                self.load_directory()
            except Exception as e: messagebox.showerror("Помилка", str(e))

if __name__ == "__main__":
    app = FileExplorer()
    app.mainloop()
