<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:050505,35:171717,70:303030,100:050505&height=190&section=header&text=MarcusBot&fontSize=54&fontColor=ffffff&fontAlignY=38&desc=AN%20AI%20BUDDY%20FOR%20TELEGRAM%20AND%20RUBIKA&descAlignY=62&descSize=13" width="100%" />

<br/>

<img src="https://img.shields.io/badge/PYTHON-111111?style=for-the-badge&logo=python&logoColor=white" /> <img src="https://img.shields.io/badge/OPENROUTER-111111?style=for-the-badge&logo=openai&logoColor=white" /> <img src="https://img.shields.io/badge/TELEGRAM-111111?style=for-the-badge&logo=telegram&logoColor=white" /> <img src="https://img.shields.io/github/stars/TheROMZ52/marcusbot?style=for-the-badge&color=111111&labelColor=050505&logo=github" /> <img src="https://img.shields.io/github/last-commit/TheROMZ52/marcusbot?style=for-the-badge&color=111111&labelColor=050505" />

<br/>

[فارسی](README.md) · [English](README.en.md)

### Marcus is the group’s AI buddy: casual Persian, controllable memory, and a habit of actually replying.

<img src="https://skillicons.dev/icons?i=py,sqlite,githubactions&theme=dark" />

</div>

---

MarcusBot is a conversational AI companion for Telegram and Rubika, designed around natural Iranian Persian, user-controlled memory, and OpenRouter model routing. It is written in Python and uses SQLite for persistent data.

---

## 01 / FEATURES

- Replies in private Telegram chats and when mentioned or addressed in groups
- Long-term memory is saved only when a user explicitly requests it
- Users can view and delete memories, including identifiable information
- 10-minute one-time codes let users link their own Telegram and Rubika identities
- Separate short conversation history per chat, stored in a shared SQLite database
- Runs locally on Windows and Android through Termux
- Optional proactive Telegram group replies; disabled by default

---

## 02 / INSTALL ON TERMUX

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

## 03 / INSTALL ON WINDOWS

Install Python 3.11 or newer, then run in PowerShell:

```powershell
git clone https://github.com/TheROMZ52/marcusbot.git
cd marcusbot
python -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and add the OpenRouter key and the platform tokens you want to enable. At least one Telegram or Rubika token is required. If no model ID is configured, the first-run setup displays available models and defaults to `openrouter/free`.

Start the bot:

```bash
python -m marcus
```

---

## 04 / CONFIGURATION

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from BotFather |
| `RUBIKA_BOT_TOKEN` | Rubika bot token for BotClient |
| `OPENROUTER_API_KEY` | OpenRouter API key; multiple keys can be comma-separated for fallback |
| `OPENROUTER_MODEL` | Model ID; defaults to `openrouter/free` |
| `OPENROUTER_FALLBACK_MODELS` | Comma-separated fallback model IDs |
| `DATABASE_PATH` | SQLite database path |
| `MAX_HISTORY_MESSAGES` | Number of recent messages included per chat |
| `PROACTIVE_REPLIES` | Enable proactive Telegram group replies; off by default |
| `PROACTIVE_PROBABILITY` | Base probability of a proactive reply; maximum 0.12 |
| `REPLY_COOLDOWN_SECONDS` | Minimum interval between proactive group replies |

---

## 05 / COMMANDS

- `/start`, `/help` — show help
- `/remember text` — save a memory with explicit consent
- `/memories` — list saved memories
- `/forget number` — delete a saved memory
- `/linkcode` — generate a 10-minute account-linking code
- `/link code` — link your own account on another platform
- `/forgetme` — delete memories and identifiable history across linked accounts

---

<details>
<summary><b>06 / RELIABILITY AND RATE LIMITS</b></summary>
<br/>

- If a model is rate-limited, times out, returns a server error, or produces an empty/invalid response, MarcusBot tries the next configured model and API key. The full fallback chain is limited to approximately 45 seconds.
- Messages are processed sequentially within each chat to prevent replies from getting mixed up; separate chats can be handled concurrently.
- Bot-generated error messages are never added to conversation history. Unanswered messages are removed from history so a later prompt does not inherit a failed exchange.
- Telegram shows a typing indicator while the bot is generating a response.
- Free models have daily limits. For busy groups, a low-cost paid model as `OPENROUTER_MODEL` is generally more reliable; free models can remain in `OPENROUTER_FALLBACK_MODELS`.

</details>

---

## 07 / IMPORTANT NOTES

- `.env` contains secrets and must never be committed.
- Short conversation history is stored in SQLite to preserve context. Be transparent with group members about the bot's presence.
- Long-term memory is created only through `/remember`; messages are not automatically converted into memories.
- Identity linking requires a code generated by the user from their first account and entered by that same user on the second platform.
- Rubika integration uses `BotClient` from the Rubpy version in `web3even/rubika-1`. Rubika's API is unofficial, so test with a real token in a private chat and then a test group. Compatibility with every account or group type is not guaranteed.
- In Telegram, receiving regular group messages may require changing the bot's Group Privacy setting in BotFather. Use this only in groups where members know the bot is present.
- AI response handling detects empty model output and can retry with a more limited reasoning budget. Invalid values such as `None` are not added to model history.

---

<div align="center">

<a href="https://github.com/TheROMZ52?tab=repositories"><img src="https://img.shields.io/badge/MORE%20PROJECTS-111111?style=for-the-badge&logo=github&logoColor=white" /></a>

<br/><br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:050505,50:202020,100:050505&height=110&section=footer" width="100%" />

<sub>© TheROMZ52 • Built with code, curiosity, and a suspicious number of tabs.</sub>

</div>
