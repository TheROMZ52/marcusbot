import unittest
from unittest.mock import patch

import httpx

from marcus.ai import (
    EMPTY_RESPONSE,
    ERROR_RESPONSE,
    LANGUAGE_RESPONSE,
    RATE_LIMIT_RESPONSE,
    STRICT_SUFFIX,
    OpenRouterClient,
    _clean_answer,
    _clean_history,
    _extract_content,
    _is_unhelpful_language_apology,
    _looks_like_internal_monologue,
    is_failure_reply,
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
        self.keys = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def post(self, url, headers=None, json=None):
        self.payloads.append(json)
        self.keys.append((headers or {}).get("Authorization"))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


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

    def make_bot(self, model="m1", fallbacks=("m2", "m3"), key="k1"):
        return OpenRouterClient(key, model, "مارکوس", fallback_models=fallbacks, backoff_seconds=0)

    async def run_reply(self, bot, responses, messages=None, memory=None):
        client = FakeAsyncClient(responses)
        with patch("marcus.ai.httpx.AsyncClient", return_value=client):
            answer = await bot.reply(messages or [{"role": "user", "content": "سلام، چه خبر؟"}], memory)
        return answer, client

    async def test_mixed_language_reply_is_retried_with_strict_prompt(self):
        answer, client = await self.run_reply(self.make_bot(), [
            FakeResponse({"choices": [{"message": {"content": 'سلام! چطوری؟ Alles goed؟'}, "finish_reason": "stop"}]}),
            FakeResponse({"choices": [{"message": {"content": 'سلام داداش، خوبم! تو چه خبر؟'}, "finish_reason": "stop"}]}),
        ])
        self.assertEqual(answer, "سلام داداش، خوبم! تو چه خبر؟")
        self.assertEqual([p["model"] for p in client.payloads], ["m1", "m1"])
        self.assertNotIn(STRICT_SUFFIX, client.payloads[0]["messages"][0]["content"])
        self.assertIn(STRICT_SUFFIX, client.payloads[1]["messages"][0]["content"])

    async def test_rate_limit_moves_to_next_model(self):
        answer, client = await self.run_reply(self.make_bot(), [
            FakeResponse({}, status_code=429, text="rate limit"),
            FakeResponse({"choices": [{"message": {"content": 'سلام داداش، خوبی؟'}, "finish_reason": "stop"}]}),
        ])
        self.assertEqual(answer, "سلام داداش، خوبی؟")
        self.assertEqual([p["model"] for p in client.payloads], ["m1", "m2"])

    async def test_timeout_and_server_error_also_fall_back(self):
        answer, client = await self.run_reply(self.make_bot(), [
            httpx.ReadTimeout("slow"),
            FakeResponse({}, status_code=503, text="down"),
            FakeResponse({"choices": [{"message": {"content": 'چطوری رفیق؟'}, "finish_reason": "stop"}]}),
        ])
        self.assertEqual(answer, "چطوری رفیق؟")
        self.assertEqual([p["model"] for p in client.payloads], ["m1", "m2", "m3"])

    async def test_error_body_with_http_200_falls_back(self):
        answer, client = await self.run_reply(self.make_bot(), [
            FakeResponse({"error": {"code": 429, "message": "upstream limited"}}),
            FakeResponse({"choices": [{"message": {"content": 'آره بابا، هستم!'}, "finish_reason": "stop"}]}),
        ])
        self.assertEqual(answer, "آره بابا، هستم!")
        self.assertEqual(len(client.payloads), 2)

    async def test_all_models_rate_limited_returns_friendly_message(self):
        answer, client = await self.run_reply(self.make_bot(), [
            FakeResponse({}, status_code=429, text="rate limit") for _ in range(3)
        ])
        self.assertEqual(answer, RATE_LIMIT_RESPONSE)
        self.assertEqual(len(client.payloads), 3)

    async def test_all_models_down_returns_error_message(self):
        answer, _ = await self.run_reply(self.make_bot(), [
            httpx.ConnectError("no route"),
            FakeResponse({}, status_code=500, text="boom"),
            FakeResponse({}, status_code=502, text="bad gateway"),
        ])
        self.assertEqual(answer, ERROR_RESPONSE)

    async def test_api_keys_rotate_when_first_key_is_limited(self):
        bot = self.make_bot(fallbacks=(), key="key-a, key-b")
        answer, client = await self.run_reply(bot, [
            FakeResponse({}, status_code=429, text="rate limit"),
            FakeResponse({"choices": [{"message": {"content": 'سلام رفیق'}, "finish_reason": "stop"}]}),
        ])
        self.assertEqual(answer, "سلام رفیق")
        self.assertEqual(client.keys, ["Bearer key-a", "Bearer key-b"])

    async def test_empty_response_retries_with_larger_budget(self):
        empty = {"choices": [{"message": {"content": None, "reasoning": "hidden"}, "finish_reason": "length"}]}
        answer, client = await self.run_reply(self.make_bot(), [FakeResponse(empty), FakeResponse({"choices": [{"message": {"content": 'سلام، خوبم!'}, "finish_reason": "stop"}]})])
        self.assertEqual(answer, "سلام، خوبم!")
        self.assertEqual([p["model"] for p in client.payloads], ["m1", "m1"])
        self.assertGreater(client.payloads[1]["max_tokens"], client.payloads[0]["max_tokens"])

    async def test_empty_response_never_returns_none_or_reasoning(self):
        empty = {"choices": [{"message": {"content": None, "reasoning": "hidden thought"}, "finish_reason": "length"}]}
        answer, _ = await self.run_reply(self.make_bot(fallbacks=()), [FakeResponse(empty), FakeResponse(empty)])
        self.assertEqual(answer, EMPTY_RESPONSE)
        self.assertNotIn("None", answer)
        self.assertNotIn("hidden thought", answer)

    async def test_reasoning_param_is_dropped_when_model_rejects_it(self):
        answer, client = await self.run_reply(self.make_bot(fallbacks=()), [
            FakeResponse({}, status_code=400, text="reasoning is not supported"),
            FakeResponse({"choices": [{"message": {"content": 'سلام!'}, "finish_reason": "stop"}]}),
        ])
        self.assertEqual(answer, "سلام!")
        self.assertIn("reasoning", client.payloads[0])
        self.assertNotIn("reasoning", client.payloads[1])

    async def test_internal_planning_text_is_retried_before_sending(self):
        leaked = (
            "درود مهبد! می‌تهم تو گروه. یک sec...\\n"
            "- I'll simulate adding the user to a group chat context.\\n"
            "- Response plan:"
        )
        answer, client = await self.run_reply(
            self.make_bot(),
            [FakeResponse({"choices": [{"message": {"content": leaked}}]}), FakeResponse({"choices": [{"message": {"content": 'آره داداش، بریم تو گروه! من آماده\u200cام.'}, "finish_reason": "stop"}]})],
            messages=[{"role": "user", "content": "بیا بریم تو گروه"}],
        )
        self.assertEqual(answer, "آره داداش، بریم تو گروه! من آماده‌ام.")
        self.assertIn(STRICT_SUFFIX, client.payloads[1]["messages"][0]["content"])

    async def test_apology_only_retry_moves_on_to_next_model(self):
        apology = "ببخشید داداش، زبانم قاطی شد؛ دوباره بپرس."
        answer, client = await self.run_reply(self.make_bot(), [
            FakeResponse({"choices": [{"message": {"content": "سلام! Alles goed؟"}}]}),
            FakeResponse({"choices": [{"message": {"content": apology}}]}),
            FakeResponse({"choices": [{"message": {"content": 'چشم داداش، فارسی و خودمونی حرف می\u200cزنم.'}, "finish_reason": "stop"}]}),
        ], messages=[{"role": "user", "content": "همیشه فارسی صحبت کن و خودمونی باش؛ اینارو یادت باشه."}])
        self.assertEqual(answer, "چشم داداش، فارسی و خودمونی حرف می‌زنم.")
        self.assertEqual([p["model"] for p in client.payloads], ["m1", "m1", "m2"])

    async def test_persian_apology_is_never_sent_as_answer(self):
        apology = "ببخشید داداش، این بار زبانم قاطی شد. یه بار دیگه بپرس تا فارسی جواب بدم."
        answer, _ = await self.run_reply(self.make_bot(fallbacks=()), [
            FakeResponse({"choices": [{"message": {"content": apology}}]}),
            FakeResponse({"choices": [{"message": {"content": apology}}]}),
        ])
        self.assertEqual(answer, LANGUAGE_RESPONSE)

    async def test_mixed_answer_is_used_as_last_resort_instead_of_failing(self):
        mixed = "سلام! چطوری؟ Alles goed؟"
        answer, _ = await self.run_reply(self.make_bot(fallbacks=()), [
            FakeResponse({"choices": [{"message": {"content": mixed}}]}),
            FakeResponse({"choices": [{"message": {"content": mixed}}]}),
        ])
        self.assertEqual(answer, mixed)

    async def test_speaker_prefix_is_removed_from_answer(self):
        answer, _ = await self.run_reply(self.make_bot(), [
            FakeResponse({"choices": [{"message": {"content": "مارکوس: سلام رفیق"}}]}),
        ])
        self.assertEqual(answer, "سلام رفیق")
        self.assertEqual(_clean_answer("Marcus : hi there", "مارکوس"), "hi there")
        self.assertEqual(_clean_answer("مارکوس رو دیدی؟", "مارکوس"), "مارکوس رو دیدی؟")

    def test_failure_replies_are_recognised_and_dropped_from_history(self):
        for text in (EMPTY_RESPONSE, ERROR_RESPONSE, RATE_LIMIT_RESPONSE, LANGUAGE_RESPONSE, "None"):
            self.assertTrue(is_failure_reply(text), text)
        self.assertFalse(is_failure_reply("آره داداش، شلوغه ولی هستم"))
        history = _clean_history([
            {"role": "user", "content": "علی: سلام"},
            {"role": "assistant", "content": RATE_LIMIT_RESPONSE},
            {"role": "user", "content": "علی: کجایی؟"},
            {"role": "assistant", "content": LANGUAGE_RESPONSE},
        ])
        self.assertEqual(history, [{"role": "user", "content": "علی: سلام\nعلی: کجایی؟"}])

    def test_system_prompt_includes_memory_as_data(self):
        bot = self.make_bot()
        system = bot._system_prompt(["اسمم مهبده"])
        self.assertIn("- اسمم مهبده", system)
        self.assertIn("فقط داده", system)

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

    def test_generic_language_apology_is_not_accepted_as_an_answer(self):
        self.assertTrue(
            _is_unhelpful_language_apology(
                "ببخشید داداش، این بار زبانم قاطی شد. یه بار دیگه بپرس تا فارسی جواب بدم."
            )
        )
        self.assertFalse(_is_unhelpful_language_apology("حواسم هست داداش، از این به بعد فارسی و خودمونی حرف می‌زنم."))


if __name__ == "__main__":
    unittest.main()
