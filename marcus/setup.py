import getpass
import os
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(".env")
FIELDS = {
    "OPENROUTER_API_KEY": ("کلید API اوپن‌روتر (اجباری)", True),
    "TELEGRAM_BOT_TOKEN": ("توکن ربات تلگرام؛ برای رد کردن خالی بگذار", False),
    "RUBIKA_BOT_TOKEN": ("توکن ربات روبیکا؛ برای رد کردن خالی بگذار", False),
}


def run_first_setup() -> None:
    load_dotenv(ENV_PATH)
    current = {key: os.getenv(key, "").strip() for key in FIELDS}
    missing = [key for key, value in current.items() if not value]

    if not missing:
        return

    print("\nمارکوس — راه‌اندازی اولیه")
    print("مقادیر واردشده در فایل محلی .env ذخیره می‌شوند و نمایش داده نخواهند شد.")
    print("برای فعال کردن هر پلتفرم، توکنش را وارد کن؛ پلتفرم‌های دیگر را می‌توانی رد کنی.\n")

    updates = {}
    for key in missing:
        label, required = FIELDS[key]
        while True:
            try:
                value = getpass.getpass(f"{label}: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nراه‌اندازی لغو شد.")
                raise SystemExit(1)
            if value or not required:
                updates[key] = value
                break
            print("این مقدار اجباری است؛ دوباره تلاش کن.")

    merged = {**current, **updates}
    if not merged["TELEGRAM_BOT_TOKEN"] and not merged["RUBIKA_BOT_TOKEN"]:
        print("برای ادامه باید حداقل توکن تلگرام یا روبیکا را وارد کنی.")
        raise SystemExit(1)

    existing_lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    keys_written = set()
    output = []
    for line in existing_lines:
        stripped = line.strip()
        key = stripped.split("=", 1)[0].removeprefix("export ").strip() if "=" in stripped and not stripped.startswith("#") else ""
        if key in updates:
            value = updates[key]
            output.append(f"{key}={value}" if value else f"{key}=")
            keys_written.add(key)
        else:
            output.append(line)
    for key, value in updates.items():
        if key not in keys_written:
            output.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    try:
        ENV_PATH.chmod(0o600)
    except OSError:
        pass
    load_dotenv(ENV_PATH, override=True)
    print("\nتنظیمات ذخیره شد. مارکوس آمادهٔ اجراست.\n")
