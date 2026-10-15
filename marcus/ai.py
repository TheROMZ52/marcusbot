import httpx

SYSTEM_PROMPT = """تو مارکوس هستی؛ رفیق باهوش و خودمونی گروه.
فارسی ایران صحبت کن، کوتاه و طبیعی جواب بده و مثل ربات رسمی حرف نزن.
شوخی کن اما توهین آزاردهنده نکن. اگر چیزی را نمی‌دانی، صادقانه بگو.
اطلاعات ساختگی دربارهٔ کاربرها نساز و اطلاعات حساس یا رمزها را درخواست نکن.
فقط از تاریخچهٔ ارائه‌شده برای حفظ پیوستگی گفتگو استفاده کن.
"""

class OpenRouterClient:
    def __init__(self, api_key: str, model: str, bot_name: str):
        self.api_key = api_key
        self.model = model
        self.bot_name = bot_name

    async def reply(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            "temperature": 0.85,
            "max_tokens": 500,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/TheROMZ52/marcusbot",
            "X-Title": "MarcusBot",
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return "الان جواب درست‌وحسابی نگرفتم؛ یه بار دیگه بپرس."
        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return str(content).strip() or "یه لحظه هنگ کردم، دوباره بگو."
