import threading
import base64
from socket import *
from customtkinter import *
from tkinter import filedialog
from PIL import Image, ImageTk
import io


class MainWindow(CTk):
    def __init__(self):
        super().__init__()
        self.geometry('600x400')  # розмір головного вікна
        self.title("НазароГрама")  # заголовок вікна

        # --- Змінні для роботи ---
        self.is_show_menu = False  # чи показане бокове меню
        self.frame_width = 0  # ширина бокового меню
        self.menu_show_speed = 20  # швидкість анімації відкриття меню
        self.username = None  # ім’я користувача
        self.avatar_path = None  # шлях до аватара користувача
        self.sock = None  # сокет для підключення до сервера
        self.avatars = {}  # словник для зберігання аватарів інших користувачів

        # --- Бокове меню ---
        self.frame = CTkFrame(self, width=200, height=self.winfo_height())  # саме меню
        self.frame.pack_propagate(False)
        self.frame.configure(width=0)  # спочатку воно сховане (ширина = 0)
        self.frame.place(x=0, y=0)

        # Поле вводу імені користувача
        self.label = CTkLabel(self.frame, text='Ваше Ім`я')
        self.label.pack(pady=10)
        self.entry = CTkEntry(self.frame)
        self.entry.pack()

        # Кнопка для зміни ніка
        self.update_name_btn = CTkButton(self.frame, text="Оновити нік", command=self.update_username)
        self.update_name_btn.pack(pady=5)

        # Кнопка вибору аватара
        self.avatar_button = CTkButton(self.frame, text="Обрати аватар", command=self.choose_avatar)
        self.avatar_button.pack(pady=10)

        # Вибір теми (темна/світла)
        self.label_theme = CTkOptionMenu(self.frame, values=['Темна', 'Світла'], command=self.change_theme)
        self.label_theme.pack(side='bottom', pady=20)

        # Кнопка для показу/приховування меню
        self.btn = CTkButton(self, text='▶️', command=self.toggle_show_menu, width=30)
        self.btn.place(x=0, y=0)

        # --- Область чату ---
        self.chat_field = CTkScrollableFrame(self, width=400, height=200)  # список повідомлень
        self.chat_field.place(x=0, y=30)

        # --- Поле вводу повідомлень ---
        self.message_input = CTkEntry(self, placeholder_text='Введіть повідомлення:', height=40)
        self.send_button = CTkButton(self, text='▶️', width=50, height=40, command=self.send_message)

        # Розміщення поля вводу та кнопки відправки
        self.message_input.place(x=0, y=self.winfo_height() - 40)
        self.send_button.place(x=self.winfo_width() - 50, y=self.winfo_height() - 40)

        # --- Підключення до сервера ---
        self.connect_to_server()

        # --- Робимо адаптивність інтерфейсу ---
        self.adaptive_ui()

    # --- Оновлення ніка ---
    def update_username(self):
        new_name = self.entry.get().strip()  # отримати новий нік із поля вводу
        if new_name and new_name != self.username:
            old = self.username or "Користувач"  # якщо нік не встановлений, беремо "Користувач"
            self.username = new_name
            data = f"RENAME@{old}@{new_name}\n"  # формуємо службове повідомлення
            try:
                self.sock.sendall(data.encode())  # відправляємо на сервер
            except:
                pass
            self.add_message(f"Ви змінили нік на {new_name}", system=True)

    # --- Вибір аватара ---
    def choose_avatar(self):
        # відкриваємо діалог для вибору зображення
        path = filedialog.askopenfilename(filetypes=[("Зображення", "*.png;*.jpg;*.jpeg;*.gif")])
        if path:
            self.avatar_path = path
            self.send_avatar()

    def send_avatar(self):
        # якщо нік ще не вказано — беремо з поля
        if not self.username:
            self.username = self.entry.get().strip() or "Користувач"

        if self.avatar_path:
            # читаємо файл зображення і кодуємо у base64
            with open(self.avatar_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            filename = self.avatar_path.split("/")[-1]  # лише ім’я файлу
            data = f"AVATAR@{self.username}@{filename}@{encoded}\n"
            try:
                self.sock.sendall(data.encode())
            except:
                self.add_message("❌ Не вдалося надіслати аватар", system=True)

    def get_avatar_image(self, data, size=(30, 30)):
        # перетворює байти зображення у картинку для tkinter
        try:
            img = Image.open(io.BytesIO(data)).resize(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except:
            return None

    # --- Підключення до сервера ---
    def connect_to_server(self):
        try:
            self.sock = socket(AF_INET, SOCK_STREAM)  # створюємо сокет
            self.sock.connect(('localhost', 12345))  # підключення до сервера
            threading.Thread(target=self.recv_message, daemon=True).start()  # окремий потік для прийому повідомлень
        except Exception as e:
            self.add_message(f"❌ Не вдалося підключитися: {e}", system=True)

    def recv_message(self):
        # прийом повідомлень від сервера у циклі
        buffer = ""
        while True:
            try:
                chunk = self.sock.recv(8192)
                if not chunk:
                    break
                buffer += chunk.decode(errors="ignore")

                # обробка рядків повідомлень
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.handle_line(line.strip())
            except:
                break
        if self.sock:
            self.sock.close()

    # --- Обробка отриманих повідомлень ---
    def handle_line(self, line):
        if not line:
            return
        parts = line.split("@", 3)  # поділяємо повідомлення за символом "@"
        msg_type = parts[0]

        # текстове повідомлення
        if msg_type == "TEXT" and len(parts) >= 3:
            author = parts[1]
            message = parts[2]
            if author == "SYSTEM":
                self.add_message(message, system=True)
            else:
                self.add_message(message, username=author, self_message=(author == self.username))

        # аватар
        elif msg_type == "AVATAR" and len(parts) >= 4:
            author = parts[1]
            filename = parts[2]
            encoded = parts[3]
            try:
                data = base64.b64decode(encoded)
                self.avatars[author] = data
                self.add_message(f"{author} оновив аватар ({filename})", system=True)
            except:
                pass

        # зміна імені
        elif msg_type == "RENAME" and len(parts) >= 3:
            old = parts[1]
            new = parts[2]
            self.add_message(f"{old} змінив нік на {new}", system=True)
            if old in self.avatars:
                self.avatars[new] = self.avatars.pop(old)

        else:
            self.add_message(line, system=True)

    # --- Відправка повідомлення ---
    def send_message(self):
        text = self.message_input.get()
        if not text.strip():
            return

        if not self.username:
            self.username = self.entry.get().strip() or "Користувач"

        data = f"TEXT@{self.username}@{text}\n"
        try:
            self.sock.sendall(data.encode())  # відправляємо повідомлення на сервер
        except:
            pass

        self.add_message(text, username=self.username, self_message=True)  # додаємо одразу в чат
        self.message_input.delete(0, 'end')  # очищаємо поле вводу

    # --- Плавний скрол до кінця ---
    def smooth_scroll_to_end(self, steps=10, delay=20):
        canvas = self.chat_field._parent_canvas  # канвас, де відображаються повідомлення
        start = canvas.yview()[0]  # поточна позиція
        end = 1.0  # ціль — в самий низ
        diff = (end - start) / steps

        def step(i=0):
            if i < steps:
                canvas.yview_moveto(start + diff * (i+1))  # поступово прокручуємо
                self.after(delay, lambda: step(i+1))  # повторюємо через delay мс

        step()

    # --- Додавання повідомлення в чат ---
    def add_message(self, message, username=None, self_message=False, system=False):
        # створюємо контейнер для повідомлення
        frame = CTkFrame(self.chat_field, fg_color="transparent")
        if self_message:
            frame.pack(anchor="e", pady=2, padx=5)  # свої повідомлення праворуч
        elif system:
            frame.pack(anchor="center", pady=2, padx=5)  # системні — по центру
        else:
            frame.pack(anchor="w", pady=2, padx=5)  # чужі — ліворуч

        # --- Системні повідомлення ---
        if system:
            lbl_sys = CTkLabel(frame, text=message, font=("Arial", 11, "italic"), text_color="gray")
            lbl_sys.pack(anchor="center", pady=2)
            self.smooth_scroll_to_end()
            return

        # --- Аватар ---
        if username and username in self.avatars:
            avatar_img = self.get_avatar_image(self.avatars[username])
            if avatar_img:
                lbl_img = CTkLabel(frame, image=avatar_img, text="")
                lbl_img.image = avatar_img
                lbl_img.pack(side="left" if not self_message else "right", padx=5)

        elif username == self.username and self.avatar_path:
            try:
                with open(self.avatar_path, "rb") as f:
                    data = f.read()
                avatar_img = self.get_avatar_image(data)
                if avatar_img:
                    lbl_img = CTkLabel(frame, image=avatar_img, text="")
                    lbl_img.image = avatar_img
                    lbl_img.pack(side="right", padx=5)
            except:
                pass

        # --- Вибір кольорів під тему ---
        current_mode = get_appearance_mode()
        if self_message:
            bg_color = "#3a7bd5" if current_mode == "dark" else "#cce7ff"
            text_color = "white" if current_mode == "dark" else "black"
        else:
            bg_color = "#2b2b2b" if current_mode == "dark" else "#f0f0f0"
            text_color = "white" if current_mode == "dark" else "black"

        # --- Текстове "бульбашкове" повідомлення ---
        text_frame = CTkFrame(
            frame,
            fg_color=bg_color,
            corner_radius=10
        )
        text_frame.pack(side="right" if self_message else "left", padx=5, pady=(0, 5))

        if username:
            lbl_name = CTkLabel(text_frame, text=username, font=("Arial", 12, "bold"), text_color=text_color)
            lbl_name.pack(anchor="w", padx=5, pady=(2, 0))

        lbl_text = CTkLabel(text_frame, text=message, anchor='w', justify='left', wraplength=300, text_color=text_color)
        lbl_text.pack(anchor="w", padx=5, pady=(0, 2))

        # автоскрол завжди вниз
        self.smooth_scroll_to_end()

    # --- Анімація меню ---
    def toggle_show_menu(self):
        if self.is_show_menu:
            self.is_show_menu = False
            self.close_menu()
        else:
            self.is_show_menu = True
            self.show_menu()

    def show_menu(self):
        # плавне відкриття меню
        if self.frame_width <= 200:
            self.frame_width += self.menu_show_speed
            self.frame.configure(width=self.frame_width, height=self.winfo_height())
            if self.frame_width >= 30:
                self.btn.configure(width=self.frame_width, text='◀️')
        if self.is_show_menu:
            self.after(20, self.show_menu)

    def close_menu(self):
        # плавне закриття меню
        if self.frame_width >= 0:
            self.frame_width -= self.menu_show_speed
            self.frame.configure(width=self.frame_width)
            if self.frame_width >= 30:
                self.btn.configure(width=self.frame_width, text='▶️')
        if not self.is_show_menu:
            self.after(20, self.close_menu)

    # --- Зміна теми ---
    def change_theme(self, value):
        if value == 'Темна':
            set_appearance_mode('dark')
        else:
            set_appearance_mode('light')

    # --- Адаптивність (щоб все підлаштовувалось під розмір вікна) ---
    def adaptive_ui(self):
        menu_width = self.frame.winfo_width()
        win_w = self.winfo_width()
        win_h = self.winfo_height()

        # Область чату займає весь простір, крім меню та нижнього поля вводу
        self.chat_field.configure(width=win_w - menu_width - 20, height=win_h - 40 - 50)
        self.chat_field.place(x=menu_width, y=30)

        # Поле вводу розтягується на ширину
        self.message_input.configure(width=win_w - menu_width - self.send_button.winfo_width())
        self.message_input.place(x=menu_width, y=win_h - 40)

        # Кнопка відправки завжди праворуч
        self.send_button.place(x=win_w - self.send_button.winfo_width(), y=win_h - self.send_button.winfo_height())

        self.after(20, self.adaptive_ui)


# --- Запуск програми ---
win = MainWindow()
win.mainloop()