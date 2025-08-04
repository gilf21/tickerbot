# 📊 Telegram TickerBot on Render (Free Tier)

A minimal bot that collects stock tickers from pasted messages, keeps one vote per user×ticker, and returns a live pie‑chart.

## 1. Fork & Deploy
1. Click **Fork** (GitHub)  
2. Log in to **Render** → **New Web Service** → **Connect GitHub Repo**  
3. In the *Environment* tab add:
   - `TOKEN` – your Telegram bot token
   - `PUBLIC_URL` – the URL Render shows after first deploy (e.g. `https://tickerbot.onrender.com`)
4. Add a **Disk** (1 GB) mounted at `/app/data` (click *Advanced* → *New Disk*).  
5. Deploy. First build takes ~1 min.
6. Set the webhook once:
   ```bash
   curl "https://api.telegram.org/bot$TOKEN/setWebhook?url=$PUBLIC_URL/$TOKEN"