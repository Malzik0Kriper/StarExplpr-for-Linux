import os
import shutil
import subprocess
import threading
from pathlib import Path
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import mimetypes

# Налаштування теми
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class FileExplorer(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Налаштування головного вікна
        self.title("Провідник")
        self.geometry("1200x700")
        self.minsize(800, 500)
        
        # Змінні
        self.current_path = os.path.expanduser("~")
        self.history = [self.current_path]
        self.history_index = 0
        self.clipboard = None
        self.clipboard_operation = None  # 'copy' або 'cut'
        self.selected_items = []
        self.view_mode = "details"  # details або icons
        
        # Створення інтерфейсу
        self.create_widgets()
        self.refresh_view()
        
    def create_widgets(self):
        """Створює всі віджети інтерфейсу"""
        
        # Панель інструментів
        self.toolbar_frame = ctk.CTkFrame(self, height=50, corner_radius=0)
        self.toolbar_frame.pack(fill="x", padx=0, pady=0)
        self.toolbar_frame.pack_propagate(False)
        
        # Кнопки навігації
        nav_frame = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        nav_frame.pack(side="left", padx=10, pady=8)
        
        self.back_btn = ctk.CTkButton(
            nav_frame, text="←", width=40, height=34,
            command=self.go_back, font=("Arial", 18)
        )
        self.back_btn.pack(side="left", padx=2)
        
        self.forward_btn = ctk.CTkButton(
            nav_frame, text="→", width=40, height=34,
            command=self.go_forward, font=("Arial", 18)
        )
        self.forward_btn.pack(side="left", padx=2)
        
        self.up_btn = ctk.CTkButton(
            nav_frame, text="↑", width=40, height=34,
            command=self.go_up, font=("Arial", 18)
        )
        self.up_btn.pack(side="left", padx=2)
        
        self.refresh_btn = ctk.CTkButton(
            nav_frame, text="⟳", width=40, height=34,
            command=self.refresh_view, font=("Arial", 18)
        )
        self.refresh_btn.pack(side="left", padx=2)
        
        # Адресна панель
        address_frame = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        address_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        
        self.address_entry = ctk.CTkEntry(
            address_frame, height=34,
            placeholder_text="Шлях до папки..."
        )
        self.address_entry.pack(fill="x", expand=True)
        self.address_entry.bind("<Return>", lambda e: self.navigate_to_path())
        
        # Кнопки вигляду
        view_frame = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        view_frame.pack(side="right", padx=10, pady=8)
        
        self.details_btn = ctk.CTkButton(
            view_frame, text="☰", width=40, height=34,
            command=lambda: self.change_view("details"),
            font=("Arial", 16)
        )
        self.details_btn.pack(side="left", padx=2)
        
        self.icons_btn = ctk.CTkButton(
            view_frame, text="⊞", width=40, height=34,
            command=lambda: self.change_view("icons"),
            font=("Arial", 16)
        )
        self.icons_btn.pack(side="left", padx=2)
        
        # Головний контейнер
        main_container = ctk.CTkFrame(self, corner_radius=0)
        main_container.pack(fill="both", expand=True)
        
        # Бічна панель з швидким доступом
        self.sidebar = ctk.CTkFrame(main_container, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar.pack_propagate(False)
        
        sidebar_title = ctk.CTkLabel(
            self.sidebar, text="Швидкий доступ",
            font=("Arial", 14, "bold")
        )
        sidebar_title.pack(pady=(10, 5), padx=10, anchor="w")
        
        # Швидкі посилання
        quick_links = [
            ("🏠 Домівка", os.path.expanduser("~")),
            ("📄 Документи", os.path.join(os.path.expanduser("~"), "Documents")),
            ("📥 Завантаження", os.path.join(os.path.expanduser("~"), "Downloads")),
            ("🖼️ Зображення", os.path.join(os.path.expanduser("~"), "Pictures")),
            ("🎵 Музика", os.path.join(os.path.expanduser("~"), "Music")),
            ("🎬 Відео", os.path.join(os.path.expanduser("~"), "Videos")),
            ("💾 Робочий стіл", os.path.join(os.path.expanduser("~"), "Desktop")),
        ]
        
        for name, path in quick_links:
            if os.path.exists(path):
                btn = ctk.CTkButton(
                    self.sidebar, text=name, anchor="w",
                    height=32, fg_color="transparent",
                    hover_color=("gray85", "gray25"),
                    command=lambda p=path: self.navigate_to(p)
                )
                btn.pack(fill="x", padx=5, pady=2)
        
        # Область перегляду файлів
        self.content_frame = ctk.CTkFrame(main_container, corner_radius=0)
        self.content_frame.pack(side="left", fill="both", expand=True)
        
        # Створюємо scrollable frame для вмісту
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.content_frame,
            corner_radius=0
        )
        self.scrollable_frame.pack(fill="both", expand=True)
        
        # Статус бар
        self.status_bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            self.status_bar, text="Готово",
            anchor="w", font=("Arial", 11)
        )
        self.status_label.pack(side="left", padx=10)
        
        # Контекстне меню
        self.create_context_menu()
        
        # Прив'язка клавіш
        self.bind_shortcuts()
        
    def create_context_menu(self):
        """Створює контекстне меню"""
        # Для простоти використовуємо базові діалоги
        # В майбутньому можна додати власне меню
        pass
    
    def bind_shortcuts(self):
        """Прив'язує клавіатурні скорочення"""
        self.bind("<Control-c>", lambda e: self.copy_items())
        self.bind("<Control-x>", lambda e: self.cut_items())
        self.bind("<Control-v>", lambda e: self.paste_items())
        self.bind("<Delete>", lambda e: self.delete_items())
        self.bind("<F2>", lambda e: self.rename_item())
        self.bind("<F5>", lambda e: self.refresh_view())
        self.bind("<Alt-Left>", lambda e: self.go_back())
        self.bind("<Alt-Right>", lambda e: self.go_forward())
        self.bind("<Alt-Up>", lambda e: self.go_up())
        
    def navigate_to(self, path):
        """Переходить до вказаного шляху"""
        if os.path.exists(path) and os.path.isdir(path):
            self.current_path = os.path.abspath(path)
            
            # Оновлюємо історію
            if self.history_index < len(self.history) - 1:
                self.history = self.history[:self.history_index + 1]
            self.history.append(self.current_path)
            self.history_index = len(self.history) - 1
            
            self.refresh_view()
        else:
            messagebox.showerror("Помилка", f"Папка не існує: {path}")
    
    def navigate_to_path(self):
        """Переходить до шляху з адресної панелі"""
        path = self.address_entry.get().strip()
        if path:
            self.navigate_to(path)
    
    def go_back(self):
        """Повертається назад в історії"""
        if self.history_index > 0:
            self.history_index -= 1
            self.current_path = self.history[self.history_index]
            self.refresh_view()
    
    def go_forward(self):
        """Переходить вперед в історії"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_path = self.history[self.history_index]
            self.refresh_view()
    
    def go_up(self):
        """Переходить до батьківської папки"""
        parent = os.path.dirname(self.current_path)
        if parent != self.current_path:
            self.navigate_to(parent)
    
    def refresh_view(self):
        """Оновлює відображення вмісту"""
        # Очищаємо поточний вміст
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.selected_items = []
        
        # Оновлюємо адресну панель
        self.address_entry.delete(0, "end")
        self.address_entry.insert(0, self.current_path)
        
        try:
            # Отримуємо список файлів та папок
            items = []
            for item in os.listdir(self.current_path):
                item_path = os.path.join(self.current_path, item)
                try:
                    stat = os.stat(item_path)
                    is_dir = os.path.isdir(item_path)
                    items.append({
                        'name': item,
                        'path': item_path,
                        'is_dir': is_dir,
                        'size': stat.st_size if not is_dir else 0,
                        'modified': stat.st_mtime
                    })
                except (PermissionError, OSError):
                    continue
            
            # Сортуємо: спочатку папки, потім файли
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            if self.view_mode == "details":
                self.show_details_view(items)
            else:
                self.show_icons_view(items)
            
            # Оновлюємо статус
            file_count = sum(1 for item in items if not item['is_dir'])
            folder_count = sum(1 for item in items if item['is_dir'])
            self.status_label.configure(
                text=f"Елементів: {len(items)} ({folder_count} папок, {file_count} файлів)"
            )
            
        except PermissionError:
            messagebox.showerror("Помилка", "Немає доступу до цієї папки")
        except Exception as e:
            messagebox.showerror("Помилка", f"Помилка читання папки: {str(e)}")
    
    def show_details_view(self, items):
        """Відображає файли у вигляді таблиці"""
        # Заголовок таблиці
        header_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=("gray90", "gray20"))
        header_frame.pack(fill="x", padx=5, pady=5)
        
        headers = [
            ("Ім'я", 0.4),
            ("Дата зміни", 0.25),
            ("Тип", 0.15),
            ("Розмір", 0.2)
        ]
        
        for header, width in headers:
            label = ctk.CTkLabel(
                header_frame, text=header,
                font=("Arial", 11, "bold"),
                anchor="w"
            )
            label.pack(side="left", fill="x", expand=True, 
                      ipadx=10 if width == 0.4 else 5)
        
        # Список файлів
        for item in items:
            self.create_detail_item(item)
    
    def create_detail_item(self, item):
        """Створює елемент у детальному вигляді"""
        item_frame = ctk.CTkFrame(
            self.scrollable_frame,
            fg_color="transparent",
            height=35
        )
        item_frame.pack(fill="x", padx=5, pady=1)
        item_frame.pack_propagate(False)
        
        # Ім'я
        icon = "📁" if item['is_dir'] else self.get_file_icon(item['name'])
        name_label = ctk.CTkLabel(
            item_frame,
            text=f"{icon} {item['name']}",
            anchor="w",
            font=("Arial", 11)
        )
        name_label.pack(side="left", fill="x", expand=True, padx=(10, 5))
        
        # Дата зміни
        date_str = datetime.fromtimestamp(item['modified']).strftime("%d.%m.%Y %H:%M")
        date_label = ctk.CTkLabel(
            item_frame,
            text=date_str,
            anchor="w",
            font=("Arial", 10),
            width=150
        )
        date_label.pack(side="left", padx=5)
        
        # Тип
        if item['is_dir']:
            type_text = "Папка"
        else:
            ext = os.path.splitext(item['name'])[1]
            type_text = f"{ext.upper()[1:]} файл" if ext else "Файл"
        
        type_label = ctk.CTkLabel(
            item_frame,
            text=type_text,
            anchor="w",
            font=("Arial", 10),
            width=100
        )
        type_label.pack(side="left", padx=5)
        
        # Розмір
        size_text = "" if item['is_dir'] else self.format_size(item['size'])
        size_label = ctk.CTkLabel(
            item_frame,
            text=size_text,
            anchor="e",
            font=("Arial", 10),
            width=120
        )
        size_label.pack(side="left", padx=5)
        
        # Прив'язка подій
        for widget in [item_frame, name_label, date_label, type_label, size_label]:
            widget.bind("<Button-1>", lambda e, i=item: self.on_item_click(i))
            widget.bind("<Double-Button-1>", lambda e, i=item: self.on_item_double_click(i))
            widget.bind("<Button-3>", lambda e, i=item: self.on_item_right_click(e, i))
    
    def show_icons_view(self, items):
        """Відображає файли у вигляді значків"""
        container = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Сітка значків
        col = 0
        row = 0
        max_cols = 6
        
        for item in items:
            self.create_icon_item(container, item, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def create_icon_item(self, parent, item, row, col):
        """Створює елемент у вигляді значка"""
        item_frame = ctk.CTkFrame(
            parent,
            fg_color="transparent",
            width=120,
            height=100
        )
        item_frame.grid(row=row, column=col, padx=10, pady=10)
        item_frame.grid_propagate(False)
        
        # Іконка
        icon = "📁" if item['is_dir'] else self.get_file_icon(item['name'])
        icon_label = ctk.CTkLabel(
            item_frame,
            text=icon,
            font=("Arial", 40)
        )
        icon_label.pack(pady=(10, 5))
        
        # Ім'я файлу
        display_name = item['name']
        if len(display_name) > 15:
            display_name = display_name[:12] + "..."
        
        name_label = ctk.CTkLabel(
            item_frame,
            text=display_name,
            font=("Arial", 10),
            wraplength=110
        )
        name_label.pack()
        
        # Прив'язка подій
        for widget in [item_frame, icon_label, name_label]:
            widget.bind("<Button-1>", lambda e, i=item: self.on_item_click(i))
            widget.bind("<Double-Button-1>", lambda e, i=item: self.on_item_double_click(i))
            widget.bind("<Button-3>", lambda e, i=item: self.on_item_right_click(e, i))
    
    def get_file_icon(self, filename):
        """Повертає емоджі іконку для файлу"""
        ext = os.path.splitext(filename)[1].lower()
        
        icons = {
            '.txt': '📄', '.doc': '📄', '.docx': '📄', '.pdf': '📕',
            '.xls': '📊', '.xlsx': '📊', '.csv': '📊',
            '.ppt': '📊', '.pptx': '📊',
            '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️',
            '.bmp': '🖼️', '.svg': '🖼️',
            '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵', '.ogg': '🎵',
            '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬', '.mov': '🎬',
            '.zip': '📦', '.rar': '📦', '.7z': '📦', '.tar': '📦', '.gz': '📦',
            '.py': '🐍', '.js': '📜', '.html': '🌐', '.css': '🎨',
            '.cpp': '⚙️', '.c': '⚙️', '.h': '⚙️', '.java': '☕',
            '.sh': '⚡', '.bat': '⚡', '.exe': '⚙️',
        }
        
        return icons.get(ext, '📄')
    
    def format_size(self, size):
        """Форматує розмір файлу"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} ПБ"
    
    def on_item_click(self, item):
        """Обробляє клік на елементі"""
        self.selected_items = [item]
        self.status_label.configure(text=f"Вибрано: {item['name']}")
    
    def on_item_double_click(self, item):
        """Обробляє подвійний клік на елементі"""
        if item['is_dir']:
            self.navigate_to(item['path'])
        else:
            self.open_file(item['path'])
    
    def on_item_right_click(self, event, item):
        """Обробляє правий клік на елементі"""
        self.selected_items = [item]
        self.show_context_menu(event)
    
    def show_context_menu(self, event):
        """Показує контекстне меню"""
        # Створюємо просте меню з кнопками
        menu_window = ctk.CTkToplevel(self)
        menu_window.geometry(f"200x250+{event.x_root}+{event.y_root}")
        menu_window.overrideredirect(True)
        menu_window.attributes('-topmost', True)
        
        menu_items = [
            ("Відкрити", self.open_selected),
            ("Копіювати", self.copy_items),
            ("Вирізати", self.cut_items),
            ("Вставити", self.paste_items),
            ("Видалити", self.delete_items),
            ("Перейменувати", self.rename_item),
            ("Властивості", self.show_properties),
        ]
        
        for text, command in menu_items:
            btn = ctk.CTkButton(
                menu_window,
                text=text,
                anchor="w",
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                command=lambda c=command, w=menu_window: (c(), w.destroy())
            )
            btn.pack(fill="x", padx=2, pady=1)
        
        # Закриваємо меню при кліку поза ним
        def close_menu(e):
            menu_window.destroy()
        
        self.bind("<Button-1>", close_menu, add="+")
    
    def change_view(self, mode):
        """Змінює режим перегляду"""
        self.view_mode = mode
        self.refresh_view()
    
    def open_selected(self):
        """Відкриває вибраний елемент"""
        if self.selected_items:
            item = self.selected_items[0]
            if item['is_dir']:
                self.navigate_to(item['path'])
            else:
                self.open_file(item['path'])
    
    def open_file(self, filepath):
        """Відкриває файл у відповідній програмі"""
        try:
            subprocess.Popen(['xdg-open', filepath])
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося відкрити файл: {str(e)}")
    
    def copy_items(self):
        """Копіює вибрані елементи"""
        if self.selected_items:
            self.clipboard = [item['path'] for item in self.selected_items]
            self.clipboard_operation = 'copy'
            self.status_label.configure(
                text=f"Скопійовано: {len(self.clipboard)} елементів"
            )
    
    def cut_items(self):
        """Вирізає вибрані елементи"""
        if self.selected_items:
            self.clipboard = [item['path'] for item in self.selected_items]
            self.clipboard_operation = 'cut'
            self.status_label.configure(
                text=f"Вирізано: {len(self.clipboard)} елементів"
            )
    
    def paste_items(self):
        """Вставляє елементи з буфера обміну"""
        if not self.clipboard:
            return
        
        def paste_thread():
            try:
                for source in self.clipboard:
                    if not os.path.exists(source):
                        continue
                    
                    dest_name = os.path.basename(source)
                    dest_path = os.path.join(self.current_path, dest_name)
                    
                    # Якщо файл існує, додаємо суфікс
                    counter = 1
                    while os.path.exists(dest_path):
                        name, ext = os.path.splitext(dest_name)
                        dest_path = os.path.join(
                            self.current_path,
                            f"{name} ({counter}){ext}"
                        )
                        counter += 1
                    
                    if self.clipboard_operation == 'copy':
                        if os.path.isdir(source):
                            shutil.copytree(source, dest_path)
                        else:
                            shutil.copy2(source, dest_path)
                    elif self.clipboard_operation == 'cut':
                        shutil.move(source, dest_path)
                
                if self.clipboard_operation == 'cut':
                    self.clipboard = None
                    self.clipboard_operation = None
                
                self.after(0, self.refresh_view)
                self.after(0, lambda: self.status_label.configure(text="Вставлено успішно"))
                
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Помилка", f"Помилка вставки: {str(e)}"
                ))
        
        threading.Thread(target=paste_thread, daemon=True).start()
    
    def delete_items(self):
        """Видаляє вибрані елементи"""
        if not self.selected_items:
            return
        
        items_text = "\n".join([item['name'] for item in self.selected_items[:5]])
        if len(self.selected_items) > 5:
            items_text += f"\n... та ще {len(self.selected_items) - 5} елементів"
        
        if messagebox.askyesno(
            "Видалення",
            f"Ви впевнені, що хочете видалити:\n\n{items_text}"
        ):
            def delete_thread():
                try:
                    for item in self.selected_items:
                        if os.path.isdir(item['path']):
                            shutil.rmtree(item['path'])
                        else:
                            os.remove(item['path'])
                    
                    self.after(0, self.refresh_view)
                    self.after(0, lambda: self.status_label.configure(
                        text=f"Видалено {len(self.selected_items)} елементів"
                    ))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror(
                        "Помилка", f"Помилка видалення: {str(e)}"
                    ))
            
            threading.Thread(target=delete_thread, daemon=True).start()
    
    def rename_item(self):
        """Перейменовує вибраний елемент"""
        if not self.selected_items:
            return
        
        item = self.selected_items[0]
        
        dialog = ctk.CTkInputDialog(
            text=f"Нове ім'я для: {item['name']}",
            title="Перейменування"
        )
        new_name = dialog.get_input()
        
        if new_name and new_name != item['name']:
            new_path = os.path.join(self.current_path, new_name)
            try:
                os.rename(item['path'], new_path)
                self.refresh_view()
            except Exception as e:
                messagebox.showerror("Помилка", f"Помилка перейменування: {str(e)}")
    
    def show_properties(self):
        """Показує властивості вибраного елемента"""
        if not self.selected_items:
            return
        
        item = self.selected_items[0]
        stat = os.stat(item['path'])
        
        props_window = ctk.CTkToplevel(self)
        props_window.title(f"Властивості: {item['name']}")
        props_window.geometry("400x350")
        
        frame = ctk.CTkFrame(props_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        properties = [
            ("Ім'я:", item['name']),
            ("Тип:", "Папка" if item['is_dir'] else "Файл"),
            ("Розташування:", os.path.dirname(item['path'])),
            ("Розмір:", self.format_size(stat.st_size) if not item['is_dir'] else "-"),
            ("Створено:", datetime.fromtimestamp(stat.st_ctime).strftime("%d.%m.%Y %H:%M")),
            ("Змінено:", datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")),
            ("Доступ:", datetime.fromtimestamp(stat.st_atime).strftime("%d.%m.%Y %H:%M")),
        ]
        
        for label, value in properties:
            prop_frame = ctk.CTkFrame(frame, fg_color="transparent")
            prop_frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(
                prop_frame,
                text=label,
                font=("Arial", 11, "bold"),
                width=120,
                anchor="w"
            ).pack(side="left")
            
            ctk.CTkLabel(
                prop_frame,
                text=value,
                font=("Arial", 11),
                anchor="w"
            ).pack(side="left", fill="x", expand=True)
        
        close_btn = ctk.CTkButton(
            props_window,
            text="Закрити",
            command=props_window.destroy
        )
        close_btn.pack(pady=10)


def main():
    """Головна функція"""
    app = FileExplorer()
    app.mainloop()


if __name__ == "__main__":
    main()
