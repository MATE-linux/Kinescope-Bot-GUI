import uuid
import aiohttp
from datetime import datetime
import asyncio

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