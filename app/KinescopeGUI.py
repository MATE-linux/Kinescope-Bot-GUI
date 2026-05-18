import json
import os
import queue
import threading
import customtkinter as ctk
from AZAT_FACTOR import AZAT_FACTOR_DEFAULT
from BotWorker import BotWorker

class KinescopeGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Kinescope Bot GUI v1.0")
        self.geometry("1100x800")
        self.minsize(900, 600)

        # Переменные для хранения настроек
        self.settings = self.load_settings()
        self.current_worker = None
        self.stop_event = None

        # Очереди для обмена данными с воркером
        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()

        # Создание вкладок
        self.tabview = ctk.CTkTabview(self, width=1000, height=700)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_mass = self.tabview.add("Массовая рассылка")
        self.tab_interactive = self.tabview.add("Интерактивный")
        self.tab_countdown = self.tabview.add("Обратный отсчёт")
        self.tab_settings = self.tabview.add("Настройки")

        # Заполнение вкладок
        self.setup_mass_tab()
        self.setup_interactive_tab()
        self.setup_countdown_tab()
        self.setup_settings_tab()

        # Область лога (общая для всех режимов)
        self.log_text = ctk.CTkTextbox(self, wrap="word", height=200)
        self.log_text.pack(fill="x", padx=10, pady=(0,10))

        # Прогресс-бар (общий)
        self.progress_bar = ctk.CTkProgressBar(self, width=800)
        self.progress_bar.pack(pady=(0,10))
        self.progress_bar.set(0)

        # Таймер для обновления интерфейса
        self.after(100, self.process_queues)

        # При закрытии окна останавливаем воркер
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ------------------- ЗАГРУЗКА/СОХРАНЕНИЕ НАСТРОЕК -------------------
    def load_settings(self):
        default = {
            "chat_id": "",
            "base_username": "BOT",
            "cassette_path": "messages.txt",
            "total_messages": 10000,
            "messages_per_bot": 400,
            "max_concurrent_bots": 100,
            "proxy_mode": "none",
            "proxy_url": "",
            "countdown_template": "До конца веба: {hours}ч {minutes_mod}мин (по Азату: {azat_hours}ач {azat_minutes_mod}ам)",
            "azat_factor": AZAT_FACTOR_DEFAULT,
            "countdown_interval": 60,
            "countdown_bot_name": "CountdownBot",
            "target_time": "20:30"
        }
        if os.path.exists("bot_gui_settings.json"):
            try:
                with open("bot_gui_settings.json", "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    default.update(saved)
            except:
                pass
        return default

    def save_settings(self):
        # Сохраняем основные настройки (из виджетов)
        self.settings["chat_id"] = self.chat_id_entry.get()
        self.settings["base_username"] = self.base_username_entry.get()
        self.settings["cassette_path"] = self.cassette_path_entry.get()
        self.settings["total_messages"] = self.total_messages_entry.get()
        self.settings["messages_per_bot"] = self.messages_per_bot_entry.get()
        self.settings["max_concurrent_bots"] = self.max_concurrent_entry.get()
        self.settings["proxy_mode"] = self.proxy_mode_var.get()
        self.settings["proxy_url"] = self.proxy_url_entry.get()
        self.settings["countdown_template"] = self.template_entry.get()
        self.settings["azat_factor"] = float(self.azat_factor_entry.get())
        self.settings["countdown_interval"] = int(self.interval_entry.get())
        self.settings["countdown_bot_name"] = self.bot_name_entry.get()
        self.settings["target_time"] = self.target_time_entry.get()
        with open("bot_gui_settings.json", "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    # ------------------- ВКЛАДКА "МАССОВАЯ РАССЫЛКА" -------------------
    def setup_mass_tab(self):
        frame = ctk.CTkFrame(self.tab_mass)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Chat ID
        ctk.CTkLabel(frame, text="Chat ID:").grid(row=0, column=0, sticky="w", pady=5)
        self.chat_id_entry = ctk.CTkEntry(frame, width=400)
        self.chat_id_entry.grid(row=0, column=1, sticky="w", pady=5)
        self.chat_id_entry.insert(0, self.settings["chat_id"])

        # Базовое имя
        ctk.CTkLabel(frame, text="Базовое имя бота:").grid(row=1, column=0, sticky="w", pady=5)
        self.base_username_entry = ctk.CTkEntry(frame, width=200)
        self.base_username_entry.grid(row=1, column=1, sticky="w", pady=5)
        self.base_username_entry.insert(0, self.settings["base_username"])

        # Путь к кассете
        ctk.CTkLabel(frame, text="Файл кассеты:").grid(row=2, column=0, sticky="w", pady=5)
        self.cassette_path_entry = ctk.CTkEntry(frame, width=300)
        self.cassette_path_entry.grid(row=2, column=1, sticky="w", pady=5)
        self.cassette_path_entry.insert(0, self.settings["cassette_path"])
        browse_btn = ctk.CTkButton(frame, text="Обзор", command=self.browse_cassette, width=80)
        browse_btn.grid(row=2, column=2, padx=5)

        # Количество сообщений
        ctk.CTkLabel(frame, text="Всего сообщений:").grid(row=3, column=0, sticky="w", pady=5)
        self.total_messages_entry = ctk.CTkEntry(frame, width=150)
        self.total_messages_entry.grid(row=3, column=1, sticky="w", pady=5)
        self.total_messages_entry.insert(0, str(self.settings["total_messages"]))

        ctk.CTkLabel(frame, text="Сообщений на бота:").grid(row=4, column=0, sticky="w", pady=5)
        self.messages_per_bot_entry = ctk.CTkEntry(frame, width=150)
        self.messages_per_bot_entry.grid(row=4, column=1, sticky="w", pady=5)
        self.messages_per_bot_entry.insert(0, str(self.settings["messages_per_bot"]))

        ctk.CTkLabel(frame, text="Параллельных ботов:").grid(row=5, column=0, sticky="w", pady=5)
        self.max_concurrent_entry = ctk.CTkEntry(frame, width=150)
        self.max_concurrent_entry.grid(row=5, column=1, sticky="w", pady=5)
        self.max_concurrent_entry.insert(0, str(self.settings["max_concurrent_bots"]))

        # Кнопки
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.grid(row=6, column=0, columnspan=3, pady=20)
        self.mass_start_btn = ctk.CTkButton(btn_frame, text="▶ СТАРТ", command=self.start_mass_send, fg_color="green")
        self.mass_start_btn.pack(side="left", padx=10)
        self.mass_stop_btn = ctk.CTkButton(btn_frame, text="⏹ СТОП", command=self.stop_current_task, fg_color="red", state="disabled")
        self.mass_stop_btn.pack(side="left", padx=10)

    def browse_cassette(self):
        from tkinter import filedialog
        filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            self.cassette_path_entry.delete(0, "end")
            self.cassette_path_entry.insert(0, filename)
            self.settings["cassette_path"] = filename

    # ------------------- ВКЛАДКА "ИНТЕРАКТИВНЫЙ" -------------------
    def setup_interactive_tab(self):
        frame = ctk.CTkFrame(self.tab_interactive)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Верхняя часть: настройки
        settings_frame = ctk.CTkFrame(frame)
        settings_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(settings_frame, text="Chat ID:").grid(row=0, column=0, padx=5, pady=5)
        self.interactive_chat_id_entry = ctk.CTkEntry(settings_frame, width=300)
        self.interactive_chat_id_entry.grid(row=0, column=1, padx=5, pady=5)
        self.interactive_chat_id_entry.insert(0, self.settings["chat_id"])

        ctk.CTkLabel(settings_frame, text="Базовое имя:").grid(row=0, column=2, padx=5, pady=5)
        self.interactive_base_username_entry = ctk.CTkEntry(settings_frame, width=150)
        self.interactive_base_username_entry.grid(row=0, column=3, padx=5, pady=5)
        self.interactive_base_username_entry.insert(0, self.settings["base_username"])

        # Область ввода сообщения
        input_frame = ctk.CTkFrame(frame)
        input_frame.pack(fill="x", pady=10)
        self.message_entry = ctk.CTkEntry(input_frame, width=600, placeholder_text="Введите сообщение...")
        self.message_entry.pack(side="left", padx=5, fill="x", expand=True)
        send_btn = ctk.CTkButton(input_frame, text="Отправить", command=self.send_interactive_message, width=100)
        send_btn.pack(side="right", padx=5)

        # Кнопки управления интерактивным режимом
        control_frame = ctk.CTkFrame(frame)
        control_frame.pack(pady=10)
        self.interactive_start_btn = ctk.CTkButton(control_frame, text="▶ ЗАПУСТИТЬ РЕЖИМ", command=self.start_interactive_mode, fg_color="green")
        self.interactive_start_btn.pack(side="left", padx=5)
        self.interactive_stop_btn = ctk.CTkButton(control_frame, text="⏹ ОСТАНОВИТЬ", command=self.stop_current_task, fg_color="red", state="disabled")
        self.interactive_stop_btn.pack(side="left", padx=5)
        self.interactive_status_label = ctk.CTkLabel(frame, text="Режим не активен", fg_color="gray", corner_radius=5)
        self.interactive_status_label.pack(pady=5)

        # Очередь сообщений для интерактивного режима
        self.interactive_msg_queue = queue.Queue()

    # ------------------- ВКЛАДКА "ОБРАТНЫЙ ОТСЧЁТ" -------------------
    def setup_countdown_tab(self):
        frame = ctk.CTkFrame(self.tab_countdown)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text="Chat ID:").grid(row=0, column=0, sticky="w", pady=5)
        self.countdown_chat_id_entry = ctk.CTkEntry(frame, width=400)
        self.countdown_chat_id_entry.grid(row=0, column=1, sticky="w", pady=5)
        self.countdown_chat_id_entry.insert(0, self.settings["chat_id"])

        ctk.CTkLabel(frame, text="Имя бота:").grid(row=1, column=0, sticky="w", pady=5)
        self.bot_name_entry = ctk.CTkEntry(frame, width=200)
        self.bot_name_entry.grid(row=1, column=1, sticky="w", pady=5)
        self.bot_name_entry.insert(0, self.settings["countdown_bot_name"])

        ctk.CTkLabel(frame, text="Время окончания (ЧЧ:ММ):").grid(row=2, column=0, sticky="w", pady=5)
        self.target_time_entry = ctk.CTkEntry(frame, width=100)
        self.target_time_entry.grid(row=2, column=1, sticky="w", pady=5)
        self.target_time_entry.insert(0, self.settings["target_time"])

        ctk.CTkLabel(frame, text="Интервал (сек):").grid(row=3, column=0, sticky="w", pady=5)
        self.interval_entry = ctk.CTkEntry(frame, width=100)
        self.interval_entry.grid(row=3, column=1, sticky="w", pady=5)
        self.interval_entry.insert(0, str(self.settings["countdown_interval"]))

        ctk.CTkLabel(frame, text="Коэффициент Азаточаса:").grid(row=4, column=0, sticky="w", pady=5)
        self.azat_factor_entry = ctk.CTkEntry(frame, width=100)
        self.azat_factor_entry.grid(row=4, column=1, sticky="w", pady=5)
        self.azat_factor_entry.insert(0, str(self.settings["azat_factor"]))

        ctk.CTkLabel(frame, text="Шаблон сообщения:").grid(row=5, column=0, sticky="nw", pady=5)
        self.template_entry = ctk.CTkEntry(frame, width=600)
        self.template_entry.grid(row=5, column=1, sticky="w", pady=5)
        self.template_entry.insert(0, self.settings["countdown_template"])

        # Кнопки
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=20)
        self.countdown_start_btn = ctk.CTkButton(btn_frame, text="▶ СТАРТ", command=self.start_countdown, fg_color="green")
        self.countdown_start_btn.pack(side="left", padx=10)
        self.countdown_stop_btn = ctk.CTkButton(btn_frame, text="⏹ СТОП", command=self.stop_current_task, fg_color="red", state="disabled")
        self.countdown_stop_btn.pack(side="left", padx=10)

        # Текущее время (для отображения)
        self.countdown_preview_label = ctk.CTkLabel(frame, text="Предпросмотр: ", font=("Consolas", 12))
        self.countdown_preview_label.grid(row=7, column=0, columnspan=2, pady=10)

    # ------------------- ВКЛАДКА "НАСТРОЙКИ" (прокси и общие) -------------------
    def setup_settings_tab(self):
        frame = ctk.CTkFrame(self.tab_settings)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text="Настройки прокси", font=("Arial", 16, "bold")).pack(anchor="w", pady=5)

        self.proxy_mode_var = ctk.StringVar(value=self.settings["proxy_mode"])
        proxy_none = ctk.CTkRadioButton(frame, text="Нет прокси", variable=self.proxy_mode_var, value="none")
        proxy_none.pack(anchor="w")
        proxy_auto = ctk.CTkRadioButton(frame, text="Авто (переменные окружения)", variable=self.proxy_mode_var, value="auto")
        proxy_auto.pack(anchor="w")
        proxy_manual = ctk.CTkRadioButton(frame, text="Ручной", variable=self.proxy_mode_var, value="manual")
        proxy_manual.pack(anchor="w")

        self.proxy_url_entry = ctk.CTkEntry(frame, width=400, placeholder_text="http://user:pass@host:port")
        self.proxy_url_entry.pack(anchor="w", padx=20, pady=5)
        self.proxy_url_entry.insert(0, self.settings["proxy_url"])

        # Кнопка сохранения
        save_btn = ctk.CTkButton(frame, text="Сохранить настройки", command=self.save_settings)
        save_btn.pack(pady=20)

    # ------------------- ОБРАБОТКА ОЧЕРЕДЕЙ (ЛОГ, ПРОГРЕСС) -------------------
    def process_queues(self):
        # Логи
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
        except queue.Empty:
            pass
        # Прогресс (используем для массовой рассылки и для отображения минут в countdown)
        try:
            while True:
                val = self.progress_queue.get_nowait()
                if isinstance(val, int) and hasattr(self, 'total_messages_for_progress'):
                    # Для массовой рассылки
                    if self.total_messages_for_progress > 0:
                        self.progress_bar.set(val / self.total_messages_for_progress)
                elif isinstance(val, int):
                    # Для countdown – показываем минуты (как текст)
                    self.countdown_preview_label.configure(text=f"Осталось минут: {val}")
        except queue.Empty:
            pass
        self.after(100, self.process_queues)

    # ------------------- ЗАПУСК РЕЖИМОВ -------------------
    def start_mass_send(self):
        # Собираем параметры
        try:
            total = int(self.total_messages_entry.get())
            per_bot = int(self.messages_per_bot_entry.get())
            concurrent = int(self.max_concurrent_entry.get())
        except ValueError:
            self.log_queue.put("❌ Ошибка: некорректные числа в полях.")
            return

        chat_id = self.chat_id_entry.get().strip()
        if not chat_id:
            self.log_queue.put("❌ Не введён Chat ID.")
            return

        proxy_config = self.get_proxy_config()

        params = {
            'chat_id': chat_id,
            'base_username': self.base_username_entry.get().strip() or "BOT",
            'cassette_path': self.cassette_path_entry.get().strip() or "messages.txt",
            'total_messages': total,
            'messages_per_bot': per_bot,
            'max_concurrent_bots': concurrent,
            'proxy_config': proxy_config
        }
        self.total_messages_for_progress = total
        self.progress_bar.set(0)

        self.stop_current_task()  # если что-то работает, остановить
        self.stop_event = threading.Event()
        self.current_worker = BotWorker('mass', params, self.log_queue, self.progress_queue, self.stop_event)
        self.current_worker.start()

        self.set_ui_state_for_task(True, "mass")

    def start_interactive_mode(self):
        chat_id = self.interactive_chat_id_entry.get().strip()
        if not chat_id:
            self.log_queue.put("❌ Не введён Chat ID.")
            return
        base_username = self.interactive_base_username_entry.get().strip() or "BOT"
        proxy_config = self.get_proxy_config()

        # Очищаем очередь сообщений
        while not self.interactive_msg_queue.empty():
            try:
                self.interactive_msg_queue.get_nowait()
            except:
                break

        params = {
            'chat_id': chat_id,
            'base_username': base_username,
            'proxy_config': proxy_config,
            'message_queue': self.interactive_msg_queue
        }
        self.stop_current_task()
        self.stop_event = threading.Event()
        self.current_worker = BotWorker('interactive', params, self.log_queue, self.progress_queue, self.stop_event)
        self.current_worker.start()

        self.set_ui_state_for_task(True, "interactive")
        self.interactive_status_label.configure(text="Режим активен, ждёт сообщения", fg_color="green")

    def start_countdown(self):
        chat_id = self.countdown_chat_id_entry.get().strip()
        if not chat_id:
            self.log_queue.put("❌ Не введён Chat ID.")
            return
        try:
            target_time = self.target_time_entry.get().strip()
            if ':' in target_time:
                hour, minute = map(int, target_time.split(':'))
            else:
                hour = int(target_time)
                minute = 0
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except:
            self.log_queue.put("❌ Неверный формат времени. Используйте ЧЧ:ММ")
            return
        try:
            interval = int(self.interval_entry.get())
            azat_factor = float(self.azat_factor_entry.get())
        except:
            self.log_queue.put("❌ Неверный интервал или коэффициент")
            return

        template = self.template_entry.get().strip()
        if not template:
            template = "До конца веба: {hours}ч {minutes_mod}мин (по Азату: {azat_hours}ач {azat_minutes_mod}ам)"

        bot_name = self.bot_name_entry.get().strip() or "CountdownBot"
        proxy_config = self.get_proxy_config()

        params = {
            'chat_id': chat_id,
            'template': template,
            'azat_factor': azat_factor,
            'interval': interval,
            'bot_name': bot_name,
            'target_hour': hour,
            'target_minute': minute,
            'proxy_config': proxy_config
        }
        self.stop_current_task()
        self.stop_event = threading.Event()
        self.current_worker = BotWorker('countdown', params, self.log_queue, self.progress_queue, self.stop_event)
        self.current_worker.start()

        self.set_ui_state_for_task(True, "countdown")

    def send_interactive_message(self):
        msg = self.message_entry.get().strip()
        if not msg:
            return
        if self.current_worker and self.current_worker.is_alive() and self.current_worker.mode == 'interactive':
            self.interactive_msg_queue.put(msg)
            self.message_entry.delete(0, "end")
            self.log_queue.put(f"📨 Сообщение отправлено в очередь: {msg[:50]}...")
        else:
            self.log_queue.put("❌ Интерактивный режим не запущен. Нажмите 'ЗАПУСТИТЬ РЕЖИМ'.")

    def stop_current_task(self):
        if self.stop_event:
            self.stop_event.set()
        if self.current_worker and self.current_worker.is_alive():
            self.current_worker.join(timeout=2)
        self.current_worker = None
        self.stop_event = None
        self.set_ui_state_for_task(False)
        self.log_queue.put("⏹️ Текущая задача остановлена.")

    def set_ui_state_for_task(self, is_running, mode=None):
        # Общее управление кнопками
        state_start = "disabled" if is_running else "normal"
        state_stop = "normal" if is_running else "disabled"

        # Массовая рассылка
        self.mass_start_btn.configure(state=state_start)
        self.mass_stop_btn.configure(state=state_stop)
        # Интерактивный
        self.interactive_start_btn.configure(state=state_start)
        self.interactive_stop_btn.configure(state=state_stop)
        # Обратный отсчёт
        self.countdown_start_btn.configure(state=state_start)
        self.countdown_stop_btn.configure(state=state_stop)

        if not is_running:
            self.interactive_status_label.configure(text="Режим не активен", fg_color="gray")
            self.progress_bar.set(0)

    def get_proxy_config(self):
        mode = self.proxy_mode_var.get()
        if mode == 'none':
            return None
        elif mode == 'auto':
            return {'trust_env': True}
        else:  # manual
            url = self.proxy_url_entry.get().strip()
            if not url:
                return None
            if not (url.startswith('http://') or url.startswith('https://') or url.startswith('socks')):
                url = 'http://' + url
            return {'proxy': url}

    def on_closing(self):
        self.stop_current_task()
        self.save_settings()
        self.destroy()