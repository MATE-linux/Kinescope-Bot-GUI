#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
KINESCOPE BOT GUI v1.0 – Графический интерфейс на CustomTkinter
================================================================
Основан на BotV5_3_1.py. Поддерживает все три режима работы:
1. Массовая рассылка (кассета)
2. Интерактивный режим с умным переиспользованием ботов
3. Обратный отсчёт с азаточасами
"""

import asyncio
import threading
import queue
import json
import os
import sys
import uuid
import time
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
import aiohttp

# ========================= ИМПОРТ ИЗ ОСНОВНОГО БОТА (при необходимости) =========================
# Вместо прямого импорта (чтобы избежать ошибок), дублируем необходимые классы и функции.
# Если оригинальный файл лежит рядом, можно раскомментировать импорт:
# from BotV5_3_1 import KinescopeBot, load_messages_from_cassette, format_countdown_message, AZAT_FACTOR_DEFAULT
# Но для надёжности продублируем ключевые компоненты:

# ---------- Константы ----------
AZAT_FACTOR_DEFAULT = 4/3  # 1.33333...

# ---------- Класс KinescopeBot (копия из оригинала) ----------
class KinescopeBot:
    """Класс для взаимодействия с чатом Kinescope"""
    def __init__(self, chat_id, bot_number, base_username="BOT"):
        self.chat_id = chat_id
        self.bot_number = bot_number
        self.base_username = base_username
        if bot_number == 1:
            self.username = base_username
        else:
            self.username = f"{base_username}{bot_number}"
        self.base_url = "https://chat.kinescope.io/v1/chat"
        self.session = None
        self.session_id = None
        self.auth_user_id = None

    async def authorize(self):
        url = f"{self.base_url}/{self.chat_id}/auth"
        user_id = str(uuid.uuid4())
        payload = {"username": self.username, "id": user_id}
        headers = {
            "Content-Type": "text/plain;charset=UTF-8",
            "Origin": "https://kinescope.io",
            "Referer": "https://kinescope.io/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0",
            "Accept": "*/*"
        }
        try:
            async with aiohttp.ClientSession(headers=headers) as temp_session:
                async with temp_session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.session_id = data["data"]["session_id"]
                        self.auth_user_id = data["data"]["user"]["id"]
                        self.username = data["data"]["user"]["username"]
                        return True
                    return False
        except Exception:
            return False

    async def create_session(self, proxy_config=None):
        headers = {
            "Content-Type": "application/json",
            "Origin": "https://kinescope.io",
            "Referer": "https://kinescope.io/",
            "User-Agent": f"Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0-BOT{self.bot_number}",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Connection": "keep-alive",
            "Authorization": f"Bearer {self.session_id}"
        }
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=10)

        if proxy_config is None:
            self.session = aiohttp.ClientSession(connector=connector, headers=headers)
        elif 'proxy' in proxy_config:
            self.session = aiohttp.ClientSession(connector=connector, headers=headers, proxy=proxy_config['proxy'])
        elif 'trust_env' in proxy_config:
            self.session = aiohttp.ClientSession(connector=connector, headers=headers, trust_env=True)
        else:
            self.session = aiohttp.ClientSession(connector=connector, headers=headers)

    async def close_session(self):
        if self.session:
            await self.session.close()

    def _create_message_data(self, message):
        return {
            "created_at": datetime.now().astimezone().replace(microsecond=0).isoformat(),
            "id": str(uuid.uuid4()),
            "is_pinned": False,
            "message": message,
            "status": "pending",
            "user": {
                "id": self.auth_user_id,
                "is_blocked": False,
                "username": self.username,
                "username_index": 0
            }
        }

    async def send_message(self, message):
        if not self.session:
            return False, "No active session"
        url = f"{self.base_url}/{self.chat_id}/messages"
        data = self._create_message_data(message)
        try:
            async with self.session.post(url, json=data, timeout=10) as resp:
                if resp.status == 200:
                    return True, None
                else:
                    text = await resp.text()
                    return False, f"HTTP {resp.status}: {text[:100]}"
        except asyncio.TimeoutError:
            return False, "Timeout"
        except Exception as e:
            return False, str(e)

# ---------- Функции для работы с кассетой ----------
def load_messages_from_cassette(file_path):
    if not os.path.exists(file_path):
        return [
            "Это тестовое сообщение #1",
            "Это тестовое сообщение #2\nсо второй строкой",
            "#РАЗБАНЬМЕНЯ"
        ]
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    raw_messages = content.split('\n===\n')
    messages = [msg.strip() for msg in raw_messages if msg.strip()]
    if not messages:
        return [
            "Это тестовое сообщение #1",
            "Это тестовое сообщение #2\nсо второй строкой",
            "#РАЗБАНЬМЕНЯ"
        ]
    return messages

# ---------- Функции для форматирования времени (режим 3) ----------
def format_time_sign(total_minutes):
    if total_minutes < 0:
        return -1, -total_minutes
    elif total_minutes > 0:
        return 1, total_minutes
    else:
        return 0, 0

def format_countdown_message(template, remaining_minutes, azat_factor):
    sign, abs_min = format_time_sign(remaining_minutes)
    hours = abs_min // 60
    minutes = abs_min % 60
    if sign == -1:
        hours_str = "-0" if hours == 0 else str(-hours)
    else:
        hours_str = str(hours)

    azat_min_total = int(remaining_minutes / azat_factor)
    sign_a, abs_azat_min = format_time_sign(azat_min_total)
    azat_hours = abs_azat_min // 60
    azat_minutes = abs_azat_min % 60
    if sign_a == -1:
        azat_hours_str = "-0" if azat_hours == 0 else str(-azat_hours)
    else:
        azat_hours_str = str(azat_hours)

    replacements = {
        "{minutes}": str(remaining_minutes),
        "{hours}": hours_str,
        "{minutes_mod}": str(minutes),
        "{azat_minutes}": str(azat_min_total),
        "{azat_hours}": azat_hours_str,
        "{azat_minutes_mod}": str(azat_minutes),
    }
    result = template
    for k, v in replacements.items():
        result = result.replace(k, v)
    return result

# ========================= КЛАСС ДЛЯ РАБОТЫ В ФОНОВОМ ПОТОКЕ =========================
class BotWorker(threading.Thread):
    """Запускает асинхронные задачи бота в отдельном потоке со своим event loop"""
    def __init__(self, mode, params, log_queue, progress_queue, stop_event):
        super().__init__(daemon=True)
        self.mode = mode          # 'mass', 'interactive', 'countdown'
        self.params = params      # словарь с параметрами
        self.log_queue = log_queue
        self.progress_queue = progress_queue
        self.stop_event = stop_event

    def run(self):
        asyncio.run(self._async_run())

    async def _async_run(self):
        try:
            if self.mode == 'mass':
                await self._mass_send()
            elif self.mode == 'interactive':
                await self._interactive_mode()
            elif self.mode == 'countdown':
                await self._countdown_mode()
        except Exception as e:
            self.log_queue.put(f"[ОШИБКА] {e}")

    # ------------------- РЕЖИМ 1: МАССОВАЯ РАССЫЛКА -------------------
    async def _mass_send(self):
        params = self.params
        chat_id = params['chat_id']
        base_username = params['base_username']
        cassette_path = params['cassette_path']
        total_messages = params['total_messages']
        messages_per_bot = params['messages_per_bot']
        max_concurrent_bots = params['max_concurrent_bots']
        proxy_config = params.get('proxy_config', None)

        self.log_queue.put("📀 Режим массовой рассылки запущен.")
        messages_source = load_messages_from_cassette(cassette_path)
        self.log_queue.put(f"📼 Загружено {len(messages_source)} сообщений из кассеты.")

        full_list = [messages_source[i % len(messages_source)] for i in range(total_messages)]
        num_bots = (total_messages + messages_per_bot - 1) // messages_per_bot
        self.log_queue.put(f"📊 План: {total_messages} сообщений, {num_bots} ботов, до {messages_per_bot} сообщ/бота")
        self.log_queue.put(f"🚦 Глобальный concurrency: {max_concurrent_bots} одновременных запросов")

        chunks = [full_list[i:i+messages_per_bot] for i in range(0, len(full_list), messages_per_bot)]

        semaphore = asyncio.Semaphore(max_concurrent_bots)
        progress_counter = 0
        lock = asyncio.Lock()

        async def run_bot_chunk(bot_number, chunk):
            nonlocal progress_counter
            bot = KinescopeBot(chat_id, bot_number, base_username)
            auth_ok = await bot.authorize()
            if not auth_ok:
                return 0, len(chunk)
            await bot.create_session(proxy_config=proxy_config)
            success = 0
            for msg in chunk:
                if self.stop_event.is_set():
                    break
                async with semaphore:
                    ok, _ = await bot.send_message(msg)
                    if ok:
                        success += 1
                        async with lock:
                            progress_counter += 1
                            self.progress_queue.put(progress_counter)  # обновляем прогресс
                await asyncio.sleep(0.05)
            await bot.close_session()
            return success, len(chunk)

        tasks = [run_bot_chunk(idx+1, chunk) for idx, chunk in enumerate(chunks) if chunk]
        results = await asyncio.gather(*tasks)

        total_success = sum(r[0] for r in results)
        total_attempted = sum(r[1] for r in results)
        self.log_queue.put(f"🎉 ОТПРАВКА ЗАВЕРШЕНА! Отправлено {total_success}/{total_attempted}")
        # Отправляем финальное сообщение (опционально, но для совместимости)
        await self._send_final_message(chat_id, f"[BOT GUI] Массовая рассылка завершена. Отправлено {total_success} из {total_attempted}.", proxy_config)

    # ------------------- РЕЖИМ 2: ИНТЕРАКТИВНЫЙ -------------------
    async def _interactive_mode(self):
        params = self.params
        chat_id = params['chat_id']
        base_username = params['base_username']
        proxy_config = params.get('proxy_config', None)
        message_queue = params.get('message_queue')  # очередь для получения сообщений от GUI
        # В интерактивном режиме воркер работает непрерывно, пока не выставлен stop_event
        # Он ожидает сообщения из очереди, отправляет их, при ошибке пересоздаёт бота.

        self.log_queue.put("💬 Интерактивный режим запущен. Ожидание сообщений...")
        current_bot = None
        bot_number = 0

        async def create_new_bot():
            nonlocal current_bot, bot_number
            if current_bot:
                await current_bot.close_session()
            bot_number += 1
            bot = KinescopeBot(chat_id, bot_number, base_username)
            self.log_queue.put(f"🔐 Создаю бота #{bot_number} (имя: {bot.username})...")
            ok = await bot.authorize()
            if not ok:
                self.log_queue.put("❌ Не удалось авторизоваться.")
                await bot.close_session()
                return None
            await bot.create_session(proxy_config=proxy_config)
            self.log_queue.put(f"✅ Бот #{bot_number} готов (username: {bot.username})")
            return bot

        current_bot = await create_new_bot()
        if not current_bot:
            self.log_queue.put("❌ Не удалось создать бота. Завершение интерактивного режима.")
            return

        while not self.stop_event.is_set():
            # Ждём сообщение из очереди (с таймаутом, чтобы проверять stop_event)
            try:
                msg = await asyncio.get_event_loop().run_in_executor(None, lambda: message_queue.get(timeout=0.5))
            except queue.Empty:
                continue
            if msg is None:  # сигнал завершения
                break
            # Отправка с ретраями
            success = False
            for attempt in range(1, 4):
                if self.stop_event.is_set():
                    break
                ok, error = await current_bot.send_message(msg)
                if ok:
                    success = True
                    self.log_queue.put(f"✅ Отправлено (бот {current_bot.username}): {msg[:50]}...")
                    break
                else:
                    self.log_queue.put(f"⚠️ Ошибка (попытка {attempt}/3): {error}")
                    if attempt < 3:
                        self.log_queue.put("🔄 Создаю нового бота...")
                        new_bot = await create_new_bot()
                        if new_bot:
                            await current_bot.close_session()
                            current_bot = new_bot
                        else:
                            await asyncio.sleep(2)
                    else:
                        self.log_queue.put("❌ Не удалось отправить после 3 попыток.")
            if not success and not self.stop_event.is_set():
                self.log_queue.put("⚠️ Пропускаем сообщение.")

        # Завершение
        await self._send_final_message(chat_id, f"[BOT GUI] Интерактивный режим завершён. Бот {current_bot.username} прощается.", proxy_config)
        if current_bot:
            await current_bot.close_session()
        self.log_queue.put("👋 Интерактивный режим остановлен.")

    # ------------------- РЕЖИМ 3: ОБРАТНЫЙ ОТСЧЁТ -------------------
    async def _countdown_mode(self):
        params = self.params
        chat_id = params['chat_id']
        template = params['template']
        azat_factor = params['azat_factor']
        interval = params['interval']
        bot_name = params['bot_name']
        target_hour = params['target_hour']
        target_minute = params['target_minute']
        proxy_config = params.get('proxy_config', None)

        self.log_queue.put("⏳ Режим обратного отсчёта запущен.")

        def minutes_remaining():
            now = datetime.now()
            target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            delta = target - now
            return int(delta.total_seconds() // 60)

        # Менеджер бота с ротацией
        class CountdownBotManager:
            def __init__(self, chat_id, base_name, proxy_config, log_callback):
                self.chat_id = chat_id
                self.base_name = base_name
                self.proxy_config = proxy_config
                self.log_callback = log_callback
                self.current_bot = None
                self.bot_number = 0

            async def create_bot(self):
                self.bot_number += 1
                bot = KinescopeBot(self.chat_id, self.bot_number, self.base_name)
                self.log_callback(f"🔐 Создаю бота #{self.bot_number} (имя: {bot.username})...")
                ok = await bot.authorize()
                if not ok:
                    self.log_callback("❌ Не удалось авторизоваться.")
                    await bot.close_session()
                    return None
                await bot.create_session(proxy_config=self.proxy_config)
                self.log_callback(f"✅ Бот #{self.bot_number} готов (username: {bot.username})")
                return bot

            async def rotate_bot(self):
                if self.current_bot:
                    await self.current_bot.close_session()
                self.current_bot = await self.create_bot()
                return self.current_bot is not None

            async def send_with_retry(self, message, max_attempts=3):
                for attempt in range(1, max_attempts+1):
                    if self.current_bot is None:
                        if not await self.rotate_bot():
                            await asyncio.sleep(2)
                            continue
                    ok, err = await self.current_bot.send_message(message)
                    if ok:
                        return True
                    self.log_callback(f"⚠️ Ошибка отправки (попытка {attempt}/{max_attempts}): {err}")
                    if attempt < max_attempts:
                        self.log_callback("🔄 Создаю нового бота...")
                        await self.rotate_bot()
                        await asyncio.sleep(1)
                return False

            async def close(self):
                if self.current_bot:
                    await self.current_bot.close_session()

        manager = CountdownBotManager(chat_id, bot_name, proxy_config, self.log_queue.put)
        if not await manager.rotate_bot():
            self.log_queue.put("❌ Не удалось создать бота. Завершение режима.")
            return

        self.log_queue.put(f"✅ Бот {manager.current_bot.username} запущен. Начинаем отсчёт.")

        last_remaining = None
        while not self.stop_event.is_set():
            remaining = minutes_remaining()
            # Обновляем прогресс (для отображения в GUI)
            self.progress_queue.put(remaining)   # можно использовать для отображения текущего времени
            message = format_countdown_message(template, remaining, azat_factor)
            # Логируем каждое отправленное сообщение (чтобы не засорять, можно раз в N секунд)
            self.log_queue.put(f"📤 {message}")
            success = await manager.send_with_retry(message)
            if not success:
                self.log_queue.put("❌ Не удалось отправить сообщение после всех попыток. Пропускаем.")
            # Ожидание с проверкой stop_event
            for _ in range(interval):
                if self.stop_event.is_set():
                    break
                await asyncio.sleep(1)

        # Завершение
        await self._send_final_message(chat_id, f"[BOT GUI] Обратный отсчёт завершён. Бот {manager.current_bot.username} прощается.", proxy_config)
        await manager.close()
        self.log_queue.put("👋 Режим обратного отсчёта остановлен.")

    # ------------------- ВСПОМОГАТЕЛЬНАЯ ОТПРАВКА ФИНАЛЬНОГО СООБЩЕНИЯ -------------------
    async def _send_final_message(self, chat_id, message_text, proxy_config):
        bot = KinescopeBot(chat_id, 1, "FinalBot")
        ok = await bot.authorize()
        if not ok:
            self.log_queue.put("⚠️ Не удалось авторизоваться для отправки финального сообщения.")
            return
        await bot.create_session(proxy_config=proxy_config)
        await bot.send_message(message_text)
        await bot.close_session()


# ========================= ГЛАВНОЕ ОКНО GUI =========================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

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

# ========================= ЗАПУСК =========================
if __name__ == "__main__":
    app = KinescopeGUI()
    app.mainloop()
