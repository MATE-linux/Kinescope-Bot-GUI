import asyncio
from datetime import datetime
import queue
import threading

from KinescopeBot import KinescopeBot
from tools.cassete_tools import load_messages_from_cassette
from tools.format_time_tools import format_countdown_message

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