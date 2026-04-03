# TradeIQ — מדריך Deploy על Railway

## מבנה השירותים ב-Railway

```
Railway Project: TradeIQ
├── Service 1: tradeiq-app      ← Streamlit dashboard (המוצר)
└── Service 2: tradeiq-landing  ← Landing page + Stripe backend
```

---

## שלב 1 — הכנה מקומית (5 דקות)

### מלא את .env
```bash
cp .env.example .env
# ערוך את .env עם API keys אמיתיים
```

### בדוק שהכל עובד
```bash
pip install -r requirements.txt
python agents/sales_manager.py --growth
```

---

## שלב 2 — Stripe Setup (10 דקות)

1. היכנס ל-[dashboard.stripe.com](https://dashboard.stripe.com)
2. **Products** → Add product:
   - שם: `TradeIQ Pro` | מחיר: `$29/month` → העתק Price ID → `STRIPE_PRICE_PRO`
   - שם: `TradeIQ Elite` | מחיר: `$79/month` → העתק Price ID → `STRIPE_PRICE_ELITE`
3. **Developers** → API keys → העתק Secret Key → `STRIPE_SECRET_KEY`
4. **Webhooks** → Add endpoint:
   - URL: `https://your-landing.railway.app/webhook/stripe`
   - Events: `checkout.session.completed`, `customer.subscription.deleted`
   - העתק Webhook Secret → `STRIPE_WEBHOOK_SECRET`

---

## שלב 3 — Deploy ל-Railway (15 דקות)

### א. צור Project
1. היכנס ל-[railway.app](https://railway.app) → New Project
2. **Deploy from GitHub repo** → חבר את הריפו

### ב. Service 1 — Streamlit App
1. + New Service → GitHub repo
2. Settings → **Variables** — הוסף את כל ה-.env keys
3. Settings → **Start Command**:
   ```
   streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
   ```
4. Settings → **Domain** → Generate Domain → שמור את ה-URL

### ג. Service 2 — Landing + Backend
1. + New Service → GitHub repo (אותו ריפו)
2. Settings → **Root Directory**: `landing`
3. Settings → **Start Command**:
   ```
   gunicorn server:app --bind 0.0.0.0:$PORT --workers 2
   ```
4. Settings → **Variables** — הוסף את כל ה-.env keys + `STREAMLIT_URL=<url מסעיף ב>`
5. Settings → **Domain** → Generate Domain (זה יהיה הדומיין הראשי שלך)

### ד. Service 3 — Scheduler (אופציונלי)
1. + New Service → GitHub repo
2. Settings → **Start Command**:
   ```
   python scheduler.py
   ```
3. Settings → **Variables** — הוסף `.env` keys

---

## שלב 4 — בדיקות

```bash
# בדוק landing
curl https://your-landing.railway.app/health

# בדוק Streamlit
curl https://your-app.railway.app/

# בדוק Stripe checkout
open https://your-landing.railway.app/checkout?plan=pro
```

---

## DNS (אופציונלי — אם יש לך דומיין tradeiq.app)

ב-Railway → Service → Settings → **Custom Domain**:
- `tradeiq.app` → landing service
- `app.tradeiq.app` → Streamlit service

---

## עלויות Railway

| שירות | RAM | CPU | מחיר |
|--------|-----|-----|------|
| Streamlit app | 512MB | 0.5 vCPU | ~$5/mo |
| Landing + Flask | 256MB | 0.25 vCPU | ~$3/mo |
| Scheduler | 256MB | 0.1 vCPU | ~$2/mo |
| **סה"כ** | | | **~$10/mo** |

> ✅ Railway נותן $5 חינם לחודש לחשבון חדש — חודש ראשון כמעט בחינם.
