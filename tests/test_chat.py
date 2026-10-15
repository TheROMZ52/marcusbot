import asyncio
import tempfile
import unittest
from pathlib import Path

from marcus.ai import EMPTY_RESPONSE, RATE_LIMIT_RESPONSE
from marcus.chat import ChatLocks, generate_reply
from marcus.db import Database


class FakeAI:
    def __init__(self, answers, delay=0.0):
        self.answers = list(answers)
        self.delay = delay
        self.seen = []

    async def reply(self, history, memories=None):
        self.seen.append([dict(item) for item in history])
        if self.delay:
            await asyncio.sleep(self.delay)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


class GenerateReplyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(str(Path(self.tmp.name) / "t.sqlite3"))

    async def turn(self, ai, text, chat="c1"):
        return await generate_reply(
            self.db, ai, platform="telegram", chat_id=chat, user_id="u1",
            text=text, memories=[], history_limit=12,
        )

    async def test_good_answer_is_stored(self):
        ai = FakeAI(["سلام رفیق"])
        answer = await self.turn(ai, "علی: سلام")
        self.assertEqual(answer, "سلام رفیق")
        self.assertEqual(
            self.db.history("telegram", "c1", 10),
            [{"role": "user", "content": "علی: سلام"}, {"role": "assistant", "content": "سلام رفیق"}],
        )

    async def test_failure_answer_is_shown_but_not_stored_and_user_message_removed(self):
        ai = FakeAI([RATE_LIMIT_RESPONSE])
        answer = await self.turn(ai, "علی: سلام")
        self.assertEqual(answer, RATE_LIMIT_RESPONSE)
        self.assertEqual(self.db.history("telegram", "c1", 10), [])

    async def test_exception_and_none_do_not_pollute_history(self):
        ai = FakeAI([RuntimeError("boom"), None, "None"])
        for _ in range(3):
            await self.turn(ai, "علی: هی")
        self.assertEqual(self.db.history("telegram", "c1", 10), [])
        self.assertEqual(await self.turn(FakeAI([None]), "علی: هی"), EMPTY_RESPONSE)

    async def test_next_question_does_not_glue_to_failed_one(self):
        await self.turn(FakeAI([RATE_LIMIT_RESPONSE]), "علی: سؤال اول")
        ai = FakeAI(["جواب دوم"])
        await self.turn(ai, "علی: سؤال دوم")
        self.assertEqual(ai.seen[0], [{"role": "user", "content": "علی: سؤال دوم"}])

    async def test_chat_lock_keeps_messages_of_one_chat_in_order(self):
        locks = ChatLocks()
        ai = FakeAI(["جواب ۱", "جواب ۲"], delay=0.05)

        async def run(text):
            async with locks.get("c1"):
                return await self.turn(ai, text)

        first, second = await asyncio.gather(run("علی: ۱"), run("علی: ۲"))
        self.assertEqual((first, second), ("جواب ۱", "جواب ۲"))
        self.assertEqual(ai.seen[1][-1], {"role": "user", "content": "علی: ۲"})
        self.assertEqual(ai.seen[1][-2], {"role": "assistant", "content": "جواب ۱"})

    async def test_different_chats_do_not_block_each_other(self):
        locks = ChatLocks()
        self.assertIsNot(locks.get("a"), locks.get("b"))
        self.assertIs(locks.get("a"), locks.get("a"))


if __name__ == "__main__":
    unittest.main()
