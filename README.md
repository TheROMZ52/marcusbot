<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:050505,35:171717,70:303030,100:050505&height=190&section=header&text=MarcusBot&fontSize=54&fontColor=ffffff&fontAlignY=38&desc=AN%20AI%20BUDDY%20FOR%20TELEGRAM%20AND%20RUBIKA&descAlignY=62&descSize=13" width="100%" />

<br/>

<img src="https://img.shields.io/badge/PYTHON-111111?style=for-the-badge&logo=python&logoColor=white" /> <img src="https://img.shields.io/badge/OPENROUTER-111111?style=for-the-badge&logo=openai&logoColor=white" /> <img src="https://img.shields.io/badge/TELEGRAM-111111?style=for-the-badge&logo=telegram&logoColor=white" /> <img src="https://img.shields.io/github/stars/TheROMZ52/marcusbot?style=for-the-badge&color=111111&labelColor=050505&logo=github" /> <img src="https://img.shields.io/github/last-commit/TheROMZ52/marcusbot?style=for-the-badge&color=111111&labelColor=050505" />

<br/>

[فارسی](README.md) · [English](README.en.md)

### مارکوس یه رفیق هوش مصنوعیه؛ نه از اون رفیق‌هایی که فقط می‌گن «درسته». حرف می‌زنه و حافظه‌اش هم دست خودته.

<img src="https://skillicons.dev/icons?i=py,sqlite,githubactions&theme=dark" />

</div>

---

مارکوس رفیق هوش مصنوعی گروه‌هاست؛ با لحن خودمونی فارسی ایران، حافظهٔ قابل‌کنترل و مدل‌های OpenRouter. پروژه با Python نوشته شده و از SQLite برای نگهداری داده‌ها استفاده می‌کند.

---

## 01 / امکانات

- پاسخ‌گویی در گفت‌وگوی خصوصی تلگرام و هنگام منشن/صدا زدن در گروه
- حافظهٔ بلندمدت فقط با دستور صریح کاربر
- دیدن و حذف خاطرات و حذف اطلاعات قابل‌شناسایی
- کد یک‌بارمصرف ۱۰ دقیقه‌ای برای پیوند دادن هویت تلگرام و روبیکا؛ دو حساب فقط با اقدام خود کاربر پیوند می‌خورند
- تاریخچهٔ کوتاه جداگانه برای هر چت و یک پایگاه SQLite مشترک
- اجرای محلی روی ویندوز و Termux
- پاسخ خودجوش در گروه تلگرام اختیاری و به‌صورت پیش‌فرض خاموش

---

## 02 / نصب در Termux

```bash
pkg update
pkg install python git
git clone https://github.com/TheROMZ52/marcusbot.git
cd marcusbot
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

---

## 03 / نصب در ویندوز

Python 3.11 یا جدیدتر نصب کن، سپس در PowerShell:

```powershell
git clone https://github.com/TheROMZ52/marcusbot.git
cd marcusbot
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

فایل `.env` را باز کن و کلید OpenRouter و توکن پلتفرم‌هایی را که می‌خواهی فعال باشند وارد کن. حداقل یکی از توکن‌های تلگرام یا روبیکا لازم است. اگر شناسهٔ مدل را خالی بگذاری، راه‌انداز اولیه فهرست مدل‌ها را نشان می‌دهد و به‌صورت پیش‌فرض `openrouter/free` را انتخاب می‌کند.

```bash
python -m marcus
```

---

## 04 / تنظیمات

| متغیر | کاربرد |
|---|---|
| `TELEGRAM_BOT_TOKEN` | توکن ربات تلگرام از BotFather |
| `RUBIKA_BOT_TOKEN` | توکن ربات روبیکا برای BotClient |
| `OPENROUTER_API_KEY` | کلید API از OpenRouter؛ چند کلید را می‌شود با کاما جدا کرد تا اگر یکی لیمیت خورد بعدی امتحان شود |
| `OPENROUTER_MODEL` | شناسهٔ مدل؛ پیش‌فرض `openrouter/free` برای مسیریابی خودکار بین مدل‌های رایگان |
| `OPENROUTER_FALLBACK_MODELS` | مدل‌های جایگزین با کاما؛ اگر مدل اصلی لیمیت خورد یا خراب شد به‌ترتیب امتحان می‌شن (خالی = فهرست پیش‌فرض) |
| `DATABASE_PATH` | مسیر پایگاه دادهٔ SQLite |
| `MAX_HISTORY_MESSAGES` | تعداد پیام‌های اخیر هر چت در متن مدل |
| `PROACTIVE_REPLIES` | پاسخ خودجوش تلگرام؛ پیش‌فرض خاموش |
| `PROACTIVE_PROBABILITY` | احتمال پایهٔ پاسخ خودجوش در هر پیام؛ حداکثر ۰٫۱۲ |
| `REPLY_COOLDOWN_SECONDS` | فاصلهٔ حداقلی پاسخ‌های گروهی خودجوش |

---

## 05 / فرمان‌ها

- `/start` و `/help` — راهنما
- `/remember متن` — ثبت خاطره با اجازهٔ خودت
- `/memories` — دیدن خاطرات ثبت‌شده
- `/forget شماره` — حذف یک خاطره
- `/linkcode` — ساخت کد پیوند با اعتبار ۱۰ دقیقه
- `/link کد` — پیوند دادن حساب خودت روی پلتفرم دیگر
- `/forgetme` — حذف خاطرات و تاریخچهٔ قابل‌شناسایی همهٔ حساب‌های پیوندخورده

---

<details>
<summary><b>06 / پایداری و لیمیت</b></summary>
<br/>

- اگر مدل اصلی لیمیت بخورد، تایم‌اوت شود، خطای سرور بدهد یا جواب خالی/خراب برگرداند، مارکوس خودکار سراغ مدل بعدی (و کلید بعدی) می‌رود؛ کل این زنجیره حداکثر حدود ۴۵ ثانیه وقت دارد.
- پیام‌های هر چت پشت‌سرهم پردازش می‌شوند (جواب‌ها قاطی نمی‌شوند) ولی چت‌های مختلف همزمان جواب می‌گیرند.
- پیام‌های خطای خود ربات (لیمیت، خالی، قطعی) هرگز وارد تاریخچه نمی‌شوند و پیام بی‌جواب هم از تاریخچه پاک می‌شود؛ پس پیام بعدی به سؤال قبلی نمی‌چسبد و مدل خطا را تقلید نمی‌کند.
- هنگام فکر کردن، در تلگرام «در حال تایپ…» نشان داده می‌شود.
- مدل‌های رایگان سقف روزانه دارند؛ برای گروه شلوغ یک مدل پولی ارزان به‌عنوان `OPENROUTER_MODEL` پایدارترین راه است (رایگان‌ها در `OPENROUTER_FALLBACK_MODELS` می‌مانند).

</details>

---

## 07 / نکات مهم

- فایل `.env` حاوی اسرار است و نباید commit شود.
- تاریخچهٔ کوتاه گفتگو در SQLite ذخیره می‌شود تا پیوستگی مکالمه حفظ شود؛ از گروه‌ها و اعضا دربارهٔ حضور ربات شفاف باش.
- حافظهٔ بلندمدت تنها با `/remember` ثبت می‌شود؛ مارکوس پیام‌ها را خودکار به خاطره تبدیل نمی‌کند.
- پیوند هویت فقط با کدی انجام می‌شود که خود کاربر از حساب اول می‌گیرد و در حساب دوم وارد می‌کند.
- اتصال روبیکا با `BotClient` از نسخهٔ Rubpy موجود در ریپوی `web3even/rubika-1` نوشته شده است. چون API روبیکا غیررسمی است، اولین اجرا باید با توکن واقعی در چت خصوصی و سپس یک گروه آزمایش شود؛ سازگاری کامل با هر نوع حساب/گروه تضمین‌شده نیست.
- در تلگرام، برای دریافت پیام‌های معمولی گروه ممکن است لازم باشد Group Privacy ربات را در BotFather تغییر بدهی. از این قابلیت فقط در گروه‌هایی استفاده کن که اعضا از آن خبر دارند.
- مدیریت پاسخ هوش مصنوعی، خروجی خالی مدل را تشخیص می‌دهد و در صورت نیاز با بودجهٔ reasoning محدودتر دوباره تلاش می‌کند؛ پاسخ‌های خراب مانند `None` هم وارد تاریخچهٔ مدل نمی‌شوند.

---

<div align="center">

<a href="https://github.com/TheROMZ52?tab=repositories"><img src="https://img.shields.io/badge/MORE%20PROJECTS-111111?style=for-the-badge&logo=github&logoColor=white" /></a>

<br/><br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:050505,50:202020,100:050505&height=110&section=footer" width="100%" />

<sub>© TheROMZ52 • ساخته‌شده با کد، کنجکاوی و تعداد مشکوکی تب باز.</sub>

</div>
