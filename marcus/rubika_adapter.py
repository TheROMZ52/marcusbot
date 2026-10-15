"""Rubika integration boundary.

A verified Rubika API/library has not been selected yet. Keep this adapter
separate from the shared AI and database core; implement it after choosing
the supported API and validating its current authentication and group-message
capabilities. No Rubika network calls are made by this placeholder.
"""

class RubikaAdapter:
    def __init__(self, settings, db, ai):
        self.settings = settings
        self.db = db
        self.ai = ai

    async def start(self):
        raise NotImplementedError(
            "اتصال روبیکا هنوز پیاده‌سازی نشده؛ باید کتابخانه و API معتبر انتخاب شود."
        )
