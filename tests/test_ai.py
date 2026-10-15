import unittest
from unittest.mock import patch

import httpx

from marcus.ai import (
    EMPTY_RESPONSE,
    OpenRouterClient,
    _clean_history,
    _extract_content,
    _is_unhelpful_language_apology,
    _looks_like_internal_monologue,
    _needs_persian_retry,
)


class FakeResponse:
    def __init__(self, data, status_code=200, text=""):
        self.data = data
        self.status_code = status_code
        self.text = text

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=request, response=response
            )


class FakeAsyncClient:
    def __init__(self, responses, **kwargs):
        self.responses = list(responses)
        self.payloads = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def post(self, url, headers=None, json=None):
        self.payloads.append(json)
        return self.responses.pop(0)


class AIResponseTests(unittest.IsolatedAsyncioTestCase):
    def test_none_content_is_not_converted_to_string(self):
        data = {
            "choices": [
                {
                    "message": {"role": "assistant", "content": None, "reasoning": "private reasoning"},
                    "finish_reason": "length",
                }
            ]
        }
        self.assertEqual(_extract_content(data), "")

    def test_text_blocks_are_joined(self):
        data = {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": "سلام"},
                            {"type": "text", "text": " رفیق"},
                        ]
                    }
                }
            ]
        }
        self.assertEqual(_extract_content(data), "سلام رفیق")

    def test_invalid_assistant_history_is_filtered(self):
        messages = [
            {"role": "user", "content": "سلام"},
            {"role": "assistant", "content": "None"},
            {"role": "assistant", "content": "مدل این بار جواب متنی نداد؛ یه بار دیگه بپرس."},
            {"role": "assistant", "content": "خوبم، تو چطوری؟"},
            {"role": "system", "content": "unexpected"},
            {"role": "user", "content": None},
        ]
        self.assertEqual(
            _clean_history(messages),
            [
                {"role": "user", "content": "سلام"},
                {"role": "assistant", "content": "خوبم، تو چطوری؟"},
            ],
        )

    def test_mixed_dutch_output_is_retried_but_requested_language_is_allowed(self):
        answer = "سلام! چطوری؟ Alles goed؟"
        messages = [{"role": "user", "content": "سلام، چه خبر؟"}]
        self.assertTrue(_needs_persian_retry(answer, messages))
        self.assertFalse(
            _needs_persian_retry(
                answer,
                [{"role": "user", "content": "به هلندی جواب بده: سلام"}],
            )
        )

    async def test_mixed_language_reply_is_retried_before_sending(self):
        responses = [
            FakeResponse({
                "choices": [{
                    "message": {"role": "assistant", "content": "سلام! چطوری؟ Alles goed؟"},
                    "finish_reason": "stop",
                }]
            }),
            FakeResponse({
                "choices": [{
                    "message": {"role": "assistant", "content": "سلام داداش، خوبم! تو چه خبر؟"},
                    "finish_reason": "stop",
                }]
            }),
        ]
        client = FakeAsyncClient(responses)
        bot = OpenRouterClient("test-key", "custom-model", "مارکوس")
        with patch("marcus.ai.httpx.AsyncClient", return_value=client):
            answer = await bot.reply([{"role": "user", "content": "سلام، چه خبر؟"}])
        self.assertEqual(answer, "سلام داداش، خوبم! تو چه خبر؟")
        self.assertEqual(len(client.payloads), 2)
        self.assertIn("فقط فارسی محاوره‌ای ایران بنویس", client.payloads[1]["messages"][0]["content"])

    async def test_rate_limit_falls_back_to_openrouter_free(self):
        responses = [
            FakeResponse({}, status_code=429, text="rate limit"),
            FakeResponse({
                "choices": [{
                    "message": {"role": "assistant", "content": "سلام داداش، خوبی؟"},
                    "finish_reason": "stop",
                }]
            }),
        ]
        client = FakeAsyncClient(responses)
        bot = OpenRouterClient("test-key", "nvidia/nemotron-3.5-lightning:free", "مارکوس")
        with patch("marcus.ai.httpx.AsyncClient", return_value=client):
            answer = await bot.reply([{"role": "user", "content": "سلام"}])
        self.assertEqual(answer, "سلام داداش، خوبی؟")
        self.assertEqual(client.payloads[0]["model"], "nvidia/nemotron-3.5-lightning:free")
        self.assertEqual(client.payloads[1]["model"], "openrouter/free")

    async def test_rate_limit_returns_friendly_message_when_free_router_is_limited(self):
        from marcus.ai import RATE_LIMIT_RESPONSE

        client = FakeAsyncClient([
            FakeResponse({}, status_code=429, text="rate limit"),
            FakeResponse({}, status_code=429, text="rate limit"),
            FakeResponse({}, status_code=429, text="rate limit"),
            FakeResponse({}, status_code=429, text="rate limit"),
        ])
        bot = OpenRouterClient("test-key", "nvidia/nemotron-3.5-lightning:free", "مارکوس")
        with patch("marcus.ai.httpx.AsyncClient", return_value=client):
            answer = await bot.reply([{"role": "user", "content": "سلام"}])
        self.assertEqual(answer, RATE_LIMIT_RESPONSE)
        self.assertEqual(len(client.payloads), 4)

    async def test_empty_response_retries_and_returns_visible_text(self):
        responses = [
            FakeResponse({
                "choices": [{
                    "message": {"role": "assistant", "content": None, "reasoning": "hidden thought"},
                    "finish_reason": "length",
                }]
            }),
            FakeResponse({
                "choices": [{
                    "message": {"role": "assistant", "content": "سلام، خوبم!"},
                    "finish_reason": "stop",
                }]
            }),
        ]
        client = FakeAsyncClient(responses)
        bot = OpenRouterClient("test-key", "nvidia/nemotron-3.5-lightning:free", "مارکوس")
        with patch("marcus.ai.httpx.AsyncClient", return_value=client):
            answer = await bot.reply([{"role": "user", "content": "سلام"}])
        self.assertEqual(answer, "سلام، خوبم!")
        self.assertEqual(len(client.payloads), 2)
        self.assertEqual(client.payloads[0]["max_tokens"], 350)
        self.assertEqual(client.payloads[0]["reasoning"]["max_tokens"], 32)
        self.assertEqual(client.payloads[1]["max_tokens"], 400)
        self.assertEqual(client.payloads[1]["reasoning"]["effort"], "minimal")

    async def test_empty_response_never_returns_none_or_reasoning(self):
        empty = {
            "choices": [{
                "message": {"role": "assistant", "content": None, "reasoning": "hidden thought"},
                "finish_reason": "length",
            }]
        }
        client = FakeAsyncClient([FakeResponse(empty), FakeResponse(empty)])
        bot = OpenRouterClient("test-key", "custom-model", "مارکوس")
        with patch("marcus.ai.httpx.AsyncClient", return_value=client):
            answer = await bot.reply([{"role": "user", "content": "سلام"}])
        self.assertEqual(answer, EMPTY_RESPONSE)
        self.assertNotIn("None", answer)
        self.assertNotIn("hidden thought", answer)



    def test_message_interpretation_leak_is_detected(self):
        leaked = (
            "2. Identify Key Elements:\n"
            '- The user is using a format with 𝐌𝐀𝐇𝐁𝐎𝐃: prefix, likely roleplay.\n'
            '- The actual content: "گلابی من که مهبدم از اول بودم"\n'
            '- Roughly: "My beauty, I have been fragrant since the beginning"\n'
            "- Response plan:\n"
            "- Draft:"
        )
        self.assertTrue(_looks_like_internal_monologue(leaked))
        self.assertFalse(_looks_like_internal_monologue("گلابی من که مهبدم از اول بودم؟ آره داداش، خودتی!"))

    def test_internal_planning_text_is_detected(self):
        leaked = (
            "درود مهبد! می‌تهم تو گروه. یک sec...\\n"
            "- I'll simulate adding the user to a group chat context.\\n"
            "- Constraints:\\n"
            "- Response plan:\\n"
            "- Draft:"
        )
        self.assertTrue(_looks_like_internal_monologue(leaked))
        self.assertFalse(_looks_like_internal_monologue("درود داداش، بزن بریم تو گروه!"))

    async def test_internal_planning_text_is_retried_before_sending(self):
        leaked = (
            "درود مهبد! می‌تهم تو گروه. یک sec...\\n"
            "- I'll simulate adding the user to a group chat context.\\n"
            "- Response plan:"
        )
        responses = [
            FakeResponse({"choices": [{"message": {"content": leaked}}]}),
            FakeResponse({"choices": [{"message": {"content": "آره داداش، بریم تو گروه! من آماده‌ام."}}]}),
        ]
        client = FakeAsyncClient(responses)
        bot = OpenRouterClient("test-key", "custom-model", "مارکوس")
        with patch("marcus.ai.httpx.AsyncClient", return_value=client):
            answer = await bot.reply([{"role": "user", "content": "بیا بریم تو گروه"}])
        self.assertEqual(answer, "آره داداش، بریم تو گروه! من آماده‌ام.")
        self.assertEqual(len(client.payloads), 2)
        self.assertIn("فقط پاسخ نهایی را بنویس", client.payloads[1]["messages"][0]["content"])

    def test_generic_language_apology_is_not_accepted_as_an_answer(self):
        self.assertTrue(
            _is_unhelpful_language_apology(
                "ببخشید داداش، این بار زبانم قاطی شد. یه بار دیگه بپرس تا فارسی جواب بدم."
            )
        )
        self.assertFalse(_is_unhelpful_language_apology("حواسم هست داداش، از این به بعد فارسی و خودمونی حرف می‌زنم."))

    async def test_model_retries_when_language_retry_only_apologizes(self):
        responses = [
            FakeResponse({"choices": [{"message": {"content": "سلام! Alles goed؟"}}]}),
            FakeResponse({"choices": [{"message": {"content": "ببخشید داداش، زبانم قاطی شد؛ دوباره بپرس."}}]}),
            FakeResponse({"choices": [{"message": {"content": "چشم داداش، فارسی و خودمونی حرف می‌زنم و ترجیحاتت رو یادم می‌مونه."}}]}),
        ]
        client = FakeAsyncClient(responses)
        bot = OpenRouterClient("test-key", "custom-model", "مارکوس")
        with patch("marcus.ai.httpx.AsyncClient", return_value=client):
            answer = await bot.reply([{"role": "user", "content": "همیشه فارسی صحبت کن و خودمونی باش؛ اینارو یادت باشه."}])
        self.assertEqual(answer, "چشم داداش، فارسی و خودمونی حرف می‌زنم و ترجیحاتت رو یادم می‌مونه.")
        self.assertEqual(len(client.payloads), 3)
        self.assertIn("درخواست اصلی کاربر را انجام بده", client.payloads[2]["messages"][0]["content"])

    async def test_persian_apology_is_retried_instead_of_sent(self):
        responses = [
            FakeResponse({"choices": [{"message": {"content": "ببخشید داداش، این بار زبانم قاطی شد. یه بار دیگه بپرس تا فارسی جواب بدم."}}]}),
            FakeResponse({"choices": [{"message": {"content": "چشم داداش، از این به بعد فارسی و خودمونی جواب می‌دم."}}]}),
        ]
        client = FakeAsyncClient(responses)
        bot = OpenRouterClient("test-key", "custom-model", "مارکوس")
        with patch("marcus.ai.httpx.AsyncClient", return_value=client):
            answer = await bot.reply([{"role": "user", "content": "همیشه فارسی صحبت کن و خودمونی باش؛ اینارو یادت باشه."}])
        self.assertEqual(answer, "چشم داداش، از این به بعد فارسی و خودمونی جواب می‌دم.")
        self.assertEqual(len(client.payloads), 2)

if __name__ == "__main__":
    unittest.main()
