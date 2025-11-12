# Multi Convo Sender (SAFE test version)

This is a **safe** testable version of a multi-message runner (for learning and local/Railway testing).
It **does not** call Facebook's API; it simulates sends by printing/logging.

## Files
- `main.py` — Flask UI + worker logic (safe: prints messages)
- `token.txt` — one token per line (optional; can paste tokens in UI form)
- `message.txt` — one message per line (optional; can paste messages in UI form)
- `hater.txt` — blocked words (one per line)
- `time.txt` — default seconds between messages (used if not set in UI)
- `requirements.txt`, `Procfile` — for deployment on Railway/Render

## Deploy
1. Upload repo to GitHub.
2. Connect and deploy on Railway (or run locally).
3. Open web UI, create a task, or leave fields empty to use `token.txt` / `message.txt`.

**Note:** This project is for learning/testing only. Do not use it for spammy or unauthorized messaging.
