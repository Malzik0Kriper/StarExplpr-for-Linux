import os
import shutil
import datetime
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, font
import os
import sys
from PIL import Image, ImageTk

# Функція для визначення правильного шляху до іконки всередині EXE/ELF
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# У вашому класі вікна або після створення root:
icon_path = resource_path("icon.png")
if os.path.exists(icon_path):
    img = ImageTk.PhotoImage(Image.open(icon_path))
    root.wm_iconphoto(True, img)

class FileExplorer(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Налаштування вікна
        self.title("Провідник")
        self.geometry("1000x600")
        self.configure(bg='#F0F0F0')
        
        # Поточний шлях
        self.current_path = str(Path.home())
        self.history = [self.current_path]
        self.history_index = 0
        
        # Буфер обміну
        self.clipboard_items = []
        self.clipboard_operation = None
        
        # Вибрані елементи
        self.selected_items = []
        
        # Налаштування стилів
        self.setup_styles()
        self.create_widgets()
        self.load_directory()
        
    def setup_styles(self):
        """Налаштувати стилі ttk"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Кольори Windows 10
        style.configure('TFrame', background='#F0F0F0')
        style.configure('Nav.TFrame', background='white')
        style.configure('Toolbar.TButton', 
                       background='#E1E1E1',
                       relief='flat',
                       padding=5)
        style.map('Toolbar.TButton',
                 background=[('active', '#0078D7'), ('pressed', '#005A9E')])
        
    def create_widgets(self):
        # Верхня панель навігації
        self.nav_frame = tk.Frame(self, height=50, bg='white', relief='flat')
        self.nav_frame.pack(fill="x", padx=0, pady=0)
        self.nav_frame.pack_propagate(False)
        
        # Кнопки навігації
        btn_font = font.Font(size=12, weight='bold')
        
        self.btn_back = tk.Button(
            self.nav_frame, text="←", width=3,
            command=self.go_back, font=btn_font,
            bg='#E1E1E1', relief='flat', cursor='hand2'
        )
        self.btn_back.pack(side="left", padx=5, pady=10)
        
        self.btn_forward = tk.Button(
            self.nav_frame, text="→", width=3,
            command=self.go_forward, font=btn_font,
            bg='#E1E1E1', relief='flat', cursor='hand2'
        )
        self.btn_forward.pack(side="left", padx=2, pady=10)
        
        self.btn_up = tk.Button(
            self.nav_frame, text="↑", width=3,
            command=self.go_up, font=btn_font,
            bg='#E1E1E1', relief='flat', cursor='hand2'
        )
        self.btn_up.pack(side="left", padx=2, pady=10)
        
        # Адресна строка
        self.path_entry = tk.Entry(
            self.nav_frame, font=('Arial', 10),
            relief='solid', bd=1
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.path_entry.bind("<Return>", lambda e: self.navigate_to_path())
        
        # Кнопка оновлення
        self.btn_refresh = tk.Button(
            self.nav_frame, text="⟳", width=3,
            command=self.load_directory, font=btn_font,
            bg='#E1E1E1', relief='flat', cursor='hand2'
        )
        self.btn_refresh.pack(side="left", padx=5, pady=10)
        
        # Панель інструментів
        self.toolbar_frame = tk.Frame(self, height=45, bg='#F5F5F5')
        self.toolbar_frame.pack(fill="x", padx=0, pady=0)
        self.toolbar_frame.pack_propagate(False)
        
        toolbar_buttons = [
            ("Нова папка", self.create_folder),
            ("Новий файл", self.create_file),
            ("Копіювати", self.copy_items),
            ("Вирізати", self.cut_items),
            ("Вставити", self.paste_items),
            ("Видалити", self.delete_items),
            ("Перейменувати", self.rename_item),
        ]
        
        btn_font_small = font.Font(size=9)
        for text, command in toolbar_buttons:
            btn = tk.Button(
                self.toolbar_frame, text=text,
                command=command, font=btn_font_small,
                bg='#E1E1E1', relief='flat',
                cursor='hand2', padx=10, pady=5
            )
            btn.pack(side="left", padx=3, pady=7)
        
        # Основна область з Treeview
        self.main_frame = tk.Frame(self, bg='white')
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Створити Treeview
        columns = ('size', 'modified', 'type')
        self.tree = ttk.Treeview(
            self.main_frame,
            columns=columns,
            show='tree headings',
            selectmode='extended'
        )
        
        # Налаштувати колонки
        self.tree.heading('#0', text='Назва')
        self.tree.heading('size', text='Розмір')
        self.tree.heading('modified', text='Дата змінення')
        self.tree.heading('type', text='Тип')
        
        self.tree.column('#0', width=400)
        self.tree.column('size', width=100)
        self.tree.column('modified', width=150)
        self.tree.column('type', width=100)
        
        # Прокрутка
        scrollbar_y = ttk.Scrollbar(self.main_frame, orient='vertical', command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(self.main_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        scrollbar_y.pack(side='right', fill='y')
        scrollbar_x.pack(side='bottom', fill='x')
        self.tree.pack(fill="both", expand=True)
        
        # Прив'язки подій
        self.tree.bind('<Double-Button-1>', self.on_double_click)
        self.tree.bind('<Button-3>', self.on_right_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        
        # Статус бар
        self.status_bar = tk.Label(
            self, text="Готово",
            anchor="w", bg='#F0F0F0',
            relief='flat', font=('Arial', 9)
        )
        self.status_bar.pack(fill="x", padx=10, pady=5)
    
    def load_directory(self):
        """Завантажити вміст директорії"""
        try:
            # Очистити дерево
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Оновити адресну строку
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, self.current_path)
            
            # Отримати список файлів
            items = []
            try:
                with os.scandir(self.current_path) as entries:
                    for entry in entries:
                        try:
                            items.append(entry)
                        except PermissionError:
                            continue
            except PermissionError:
                messagebox.showerror("Помилка", "Немає доступу до цієї директорії")
                return
            
            # Сортувати: спочатку папки, потім файли
            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
            
            # Відобразити елементи
            folder_count = 0
            file_count = 0
            
            for entry in items:
                try:
                    stat = entry.stat()
                    
                    if entry.is_dir():
                        icon = "📁"
                        size = ""
                        file_type = "Папка"
                        folder_count += 1
                    else:
                        icon = "📄"
                        size = self.format_size(stat.st_size)
                        file_type = "Файл"
                        file_count += 1
                    
                    modified = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
                    
                    # Додати в дерево
                    self.tree.insert(
                        '', 'end',
                        text=f" {icon} {entry.name}",
                        values=(size, modified, file_type),
                        tags=(entry.path,)
                    )
                except Exception as e:
                    print(f"Помилка при додаванні {entry.name}: {e}")
                    continue
            
            # Оновити статус
            self.status_bar.configure(
                text=f"{file_count} файл(ів), {folder_count} папок"
            )
            
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося завантажити директорію:\n{e}")
    
    def format_size(self, size):
        """Форматувати розмір файлу"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} ТБ"
    
    def on_double_click(self, event):
        """Обробник подвійного кліку"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            tags = self.tree.item(item, 'tags')
            if tags:
                path = tags[0]
                self.open_item(path)
    
    def on_right_click(self, event):
        """Обробник правого кліку"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            tags = self.tree.item(item, 'tags')
            if tags:
                path = tags[0]
                messagebox.showinfo("Інфо", f"Файл:\n{os.path.basename(path)}")
    
    def on_select(self, event):
        """Обробник вибору елементів"""
        self.selected_items = []
        for item in self.tree.selection():
            tags = self.tree.item(item, 'tags')
            if tags:
                self.selected_items.append(tags[0])
    
    def open_item(self, path):
        """Відкрити файл або папку"""
        if os.path.isdir(path):
            self.navigate_to(path)
        else:
            try:
                subprocess.Popen(['xdg-open', path])
            except:
                messagebox.showinfo("Інфо", f"Файл: {os.path.basename(path)}")
    
    def navigate_to(self, path):
        """Перейти до директорії"""
        if os.path.isdir(path):
            self.current_path = path
            # Додати до історії
            self.history = self.history[:self.history_index + 1]
            self.history.append(path)
            self.history_index = len(self.history) - 1
            self.load_directory()
    
    def navigate_to_path(self):
        """Перейти до шляху з адресної строки"""
        path = self.path_entry.get()
        if os.path.isdir(path):
            self.navigate_to(path)
        else:
            messagebox.showerror("Помилка", "Невірний шлях")
    
    def go_back(self):
        """Назад в історії"""
        if self.history_index > 0:
            self.history_index -= 1
            self.current_path = self.history[self.history_index]
            self.load_directory()
    
    def go_forward(self):
        """Вперед в історії"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_path = self.history[self.history_index]
            self.load_directory()
    
    def go_up(self):
        """Вгору на один рівень"""
        parent = str(Path(self.current_path).parent)
        if parent != self.current_path:
            self.navigate_to(parent)
    
    def create_folder(self):
        """Створити нову папку"""
        name = simpledialog.askstring("Нова папка", "Введіть назву папки:")
        if name:
            try:
                new_path = os.path.join(self.current_path, name)
                os.makedirs(new_path, exist_ok=True)
                self.load_directory()
                self.status_bar.configure(text=f"Створено папку: {name}")
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося створити папку:\n{e}")
    
    def create_file(self):
        """Створити новий файл"""
        name = simpledialog.askstring("Новий файл", "Введіть назву файлу:")
        if name:
            try:
                new_path = os.path.join(self.current_path, name)
                Path(new_path).touch()
                self.load_directory()
                self.status_bar.configure(text=f"Створено файл: {name}")
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося створити файл:\n{e}")
    
    def copy_items(self):
        """Копіювати вибрані елементи"""
        if not self.selected_items:
            messagebox.showinfo("Інфо", "Нічого не вибрано")
            return
        
        self.clipboard_items = self.selected_items.copy()
        self.clipboard_operation = 'copy'
        self.status_bar.configure(text=f"Скопійовано {len(self.clipboard_items)} елементів")
    
    def cut_items(self):
        """Вирізати вибрані елементи"""
        if not self.selected_items:
            messagebox.showinfo("Інфо", "Нічого не вибрано")
            return
        
        self.clipboard_items = self.selected_items.copy()
        self.clipboard_operation = 'cut'
        self.status_bar.configure(text=f"Вирізано {len(self.clipboard_items)} елементів")
    
    def paste_items(self):
        """Вставити елементи"""
        if not self.clipboard_items:
            messagebox.showinfo("Інфо", "Буфер обміну порожній")
            return
        
        try:
            for item_path in self.clipboard_items:
                if not os.path.exists(item_path):
                    continue
                    
                name = os.path.basename(item_path)
                dest_path = os.path.join(self.current_path, name)
                
                # Перевірити чи існує
                if os.path.exists(dest_path):
                    dest_path = self.get_unique_name(dest_path)
                
                if self.clipboard_operation == 'copy':
                    if os.path.isdir(item_path):
                        shutil.copytree(item_path, dest_path)
                    else:
                        shutil.copy2(item_path, dest_path)
                elif self.clipboard_operation == 'cut':
                    shutil.move(item_path, dest_path)
            
            if self.clipboard_operation == 'cut':
                self.clipboard_items = []
            
            self.load_directory()
            self.status_bar.configure(text="Вставлено успішно")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося вставити:\n{e}")
    
    def delete_items(self):
        """Видалити вибрані елементи"""
        if not self.selected_items:
            messagebox.showinfo("Інфо", "Нічого не вибрано")
            return
        
        if messagebox.askyesno("Видалення", f"Видалити {len(self.selected_items)} елементів?"):
            try:
                for item_path in self.selected_items:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                self.load_directory()
                self.status_bar.configure(text="Видалено успішно")
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося видалити:\n{e}")
    
    def rename_item(self):
        """Перейменувати елемент"""
        if not self.selected_items:
            messagebox.showinfo("Інфо", "Нічого не вибрано")
            return
        
        old_path = self.selected_items[0]
        old_name = os.path.basename(old_path)
        new_name = simpledialog.askstring("Перейменувати", 
                                         f"Нова назва для '{old_name}':",
                                         initialvalue=old_name)
        
        if new_name and new_name != old_name:
            try:
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                os.rename(old_path, new_path)
                self.load_directory()
                self.status_bar.configure(text=f"Перейменовано на: {new_name}")
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося перейменувати:\n{e}")
    
    def get_unique_name(self, path):
        """Отримати унікальне ім'я для файлу/папки"""
        base, ext = os.path.splitext(path)
        counter = 1
        new_path = f"{base} ({counter}){ext}"
        while os.path.exists(new_path):
            counter += 1
            new_path = f"{base} ({counter}){ext}"
        return new_path


if __name__ == "__main__":
    app = FileExplorer()
    app.mainloop()

