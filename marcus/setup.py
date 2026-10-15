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
MODELS = {
    "1": ("openrouter/free", "پیشنهاد من؛ انتخاب خودکار از مدل‌های رایگان"),
    "2": ("nvidia/nemotron-3.5-lightning:free", "پاسخ‌گویی سریع"),
    "3": ("nvidia/nemotron-3-super-120b-a12b:free", "گفت‌وگوی عمومی و استدلال"),
    "4": ("google/gemma-4-31b-it:free", "مدل عمومی چندمنظوره"),
    "5": ("qwen/qwen3.8-27b:free", "مدل عمومی Qwen"),
    "6": ("cohere/north-mini-code:free", "بیشتر مناسب کدنویسی"),
    "7": ("custom", "وارد کردن شناسهٔ مدل رایگان دیگر از OpenRouter"),
}


def run_first_setup() -> None:
    load_dotenv(ENV_PATH)
    current = {key: os.getenv(key, "").strip() for key in FIELDS}
    missing = [key for key, value in current.items() if not value]
    model_missing = not os.getenv("OPENROUTER_MODEL", "").strip()

    if not missing and not model_missing:
        return

    print("\nمارکوس — راه‌اندازی اولیه")
    print("توکن‌ها در ترمینال به‌صورت مخفی دریافت می‌شوند و در فایل محلی .env ذخیره خواهند شد.")
    print("برای فعال کردن هر پلتفرم، توکنش را وارد کن؛ پلتفرم دیگر را می‌توانی رد کنی.\n")

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

    if model_missing:
        print("\nمدل رایگان هوش مصنوعی را انتخاب کن:")
        for number, (model_id, description) in MODELS.items():
            print(f"{number}. {model_id} — {description}")
        choice = input("انتخاب [1]: ").strip() or "1"
        if choice not in MODELS:
            print("انتخاب نامعتبر است؛ مدل پیشنهادی انتخاب شد.")
            choice = "1"
        model_id = MODELS[choice][0]
        if model_id == "custom":
            model_id = input("شناسهٔ مدل رایگان در OpenRouter: ").strip() or MODELS["1"][0]
        updates["OPENROUTER_MODEL"] = model_id

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
    print("\nتنظیمات ذخیره شد. در اجراهای بعدی دوباره پرسیده نمی‌شوند.\n")
