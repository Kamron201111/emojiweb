# ✨ Telegram Premium Emoji Studio

Telegram uchun **premium emoji dizayn studiyasi** — mavjud emoji-generator botning to'liq qayta ishlangan, zamonaviy **Telegram Mini App** (Web App) versiyasi.

Bu chat/tugma asosidagi eski botni chiroyli grafik interfeysli, tijoriy SaaS darajasidagi Web App'ga aylantiradi. Emoji render mantig'i (Lottie/TGS, SVG, shrift) eski loyihadan **saqlab qolingan** va toza backend servislariga ko'chirilgan.

---

## 📦 Nima ichida bor

| Bo'lim | Texnologiya |
|--------|-------------|
| **Frontend** | React + TypeScript + Vite + Tailwind CSS + Telegram Mini Apps SDK |
| **Backend** | Python + FastAPI + Pydantic (async) |
| **Ma'lumotlar bazasi** | SQLAlchemy (async) — SQLite (default) yoki PostgreSQL |
| **Render** | Saqlab qolingan Lottie/TGS/SVG engine (`app/renderers/`) |
| **To'lov** | Telegram Stars (XTR) |
| **Deploy** | Docker + docker-compose + Nginx |

### Asosiy imkoniyatlar
- 🔐 Telegram `initData` ni **kriptografik tekshirish** (backend, HMAC-SHA256). Foydalanuvchi ID hech qachon frontenddan ishonilmaydi.
- 🎨 **5 ta studiya**: Name Emoji, Logo/Text, Extra 1, Extra 2, Profil foni.
- 🖼 **Shablon galereyalari**: Name = 28, Logo = 103, Extra 1 = 39, Extra 2 = 31 ta (jami 201 shablon), preview custom emoji ID'lari bilan.
- 🌈 **Grafik rang boshqaruvi**: presetlar, color picker, HEX kiritish, "asl rang".
- ✍️ **Shrift tanlash** (6 ta asosiy + 9 ta profil foni shrifti).
- ⚡ **Jonli preview** (backend Lottie render, lottie-web bilan brauzerda).
- ⭐ **Telegram Stars to'lovi** + **bepul kredit** + **stale-price himoyasi** + **refund**.
- 🎁 **Referral tizimi** (self-ref/duplicate himoyasi, birinchi pack'dan keyin +1 kredit).
- 📢 **Majburiy obuna** tekshiruvi (server tomonida).
- 🗂 **Mening to'plamlarim** / tarix.
- 🛡 **Admin panel**: statistika, foydalanuvchilar, narxlar, kanallar, support, to'lovlar, refundlar, audit log.
- 🌐 **3 til**: O'zbek (asosiy), Rus, Ingliz — i18n tizimi bilan.
- 🌗 Dark/Light mavzu, animatsiyalar, skeleton loaderlar, bottom navigatsiya.

---

## 📁 Loyiha tuzilishi

```
telegram-premium-emoji-studio/
├─ backend/
│  ├─ app/
│  │  ├─ api/            # deps + v1 routerlar
│  │  ├─ core/           # config, database, telegram_auth
│  │  ├─ renderers/      # SAQLANGAN engine + assets (templates, fonts)
│  │  ├─ services/       # biznes-mantiq (order, payment, credit, referral, ...)
│  │  ├─ telegram/       # Bot API klienti
│  │  ├─ assets/         # templates/, templates_tgs*/, fonts/
│  │  ├─ models.py       # SQLAlchemy modellar
│  │  ├─ schemas.py      # Pydantic sxemalar
│  │  └─ main.py         # FastAPI app
│  ├─ migrations/        # Alembic
│  ├─ scripts/           # migrate_old_data, set_webhook
│  ├─ tests/             # pytest
│  ├─ requirements.txt
│  └─ Dockerfile
├─ frontend/
│  ├─ src/
│  │  ├─ api/  components/  pages/  hooks/  store/  i18n/  lib/  types/
│  │  └─ App.tsx  main.tsx
│  ├─ package.json
│  └─ Dockerfile
├─ docker-compose.yml
├─ .env.example
└─ README.md
```

---

## ✅ Talablar

- **Python 3.11+**
- **Node.js 20+**
- (ixtiyoriy) **Docker** + **Docker Compose**
- Telegram **bot tokeni** (@BotFather orqali)

---

## 🚀 Lokal o'rnatish (development)

### 1. Muhit o'zgaruvchilari
```bash
cp .env.example .env
# .env ni oching va quyidagilarni to'ldiring (pastda "Qaysi .env qiymatlar" bo'limiga qarang):
#   BOT_TOKEN, BOT_USERNAME, ADMIN_IDS, SECRET_KEY
```
`SECRET_KEY` yaratish:
```bash
python -c "import secrets;print(secrets.token_urlsafe(48))"
```

### 2. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# .env fayl backend/ papkasida ham bo'lishi kerak (yoki yuqoridagi ildizdan nusxa oling)
cp ../.env .env
uvicorn app.main:app --reload --port 8000
```
Backend `http://localhost:8000` da ishga tushadi. Swagger: `http://localhost:8000/docs`.
Health: `http://localhost:8000/health`.

### 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env             # kerak bo'lsa VITE_API_PROXY ni sozlang
npm run dev
```
Frontend `http://localhost:5173` da ishga tushadi va `/api` so'rovlarini backendga proxy qiladi.

> **Eslatma:** Mini App'ni to'liq sinash uchun uni Telegram ichida ochish kerak (chunki `initData` faqat Telegram beradi). Lokal test uchun HTTPS tunnel (masalan `ngrok` yoki `cloudflared`) orqali frontendni ochib, uni BotFather'da Web App URL sifatida sozlang.

---

## 🐳 Docker bilan ishga tushirish (production)

```bash
cp .env.example .env
# .env ni to'ldiring
docker compose up -d --build
```
- Frontend: `http://localhost:8080` (`/api` ni backendga proxy qiladi)
- Backend: ichki tarmoqda `backend:8000`
- Ma'lumotlar `backend_data` volume'da saqlanadi (SQLite).

PostgreSQL kerak bo'lsa: `docker-compose.yml` dagi `db` xizmatini oching va `.env` da:
```
DATABASE_URL=postgresql+asyncpg://emoji:emoji@db:5432/emoji
```
va `backend/requirements.txt` ga `asyncpg>=0.29` qo'shing.

---

## 🖥 Ubuntu VPS'ga deploy

```bash
# 1. Docker o'rnatish
curl -fsSL https://get.docker.com | sh

# 2. Loyihani ko'chirish
git clone <sizning-repo> && cd telegram-premium-emoji-studio

# 3. Sozlash
cp .env.example .env && nano .env      # WEBAPP_URL ni domeningizga qo'ying

# 4. Ishga tushirish
docker compose up -d --build
```

### Reverse-proxy (HTTPS majburiy — Telegram Web App faqat HTTPS'da ishlaydi)
Nginx + Certbot namunasi (host mashinada):
```nginx
server {
    server_name your-domain.com;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
```bash
sudo certbot --nginx -d your-domain.com
```

### Webhook (Stars to'lovlari uchun majburiy)
To'lov `successful_payment` yangilanishlari webhook orqali keladi:
```bash
cd backend && source .venv/bin/activate
python -m scripts.set_webhook https://your-domain.com
```
Bu webhookni `https://your-domain.com/api/v1/payments/telegram-webhook` ga o'rnatadi
(secret_token = `SECRET_KEY` ning birinchi 32 belgisi).

---

## 🗄 Ma'lumotlar bazasi va migratsiya

- **SQLite (default):** jadvallar ilova ishga tushganda avtomatik yaratiladi.
- **PostgreSQL (production):** Alembic ishlatiladi:
  ```bash
  cd backend
  alembic revision --autogenerate -m "init"
  alembic upgrade head
  ```

### Eski botdan ma'lumot ko'chirish (ixtiyoriy, idempotent)
Eski botning JSON fayllaridan (`users.json`, `credits.json`, `stats.json`,
`referrals.json`, `settings.json`, `price_*.json`, `emoji_pack.json`,
`allowed_users.json`) yangi bazaga ko'chirish:
```bash
cd backend && source .venv/bin/activate
python -m scripts.migrate_old_data "/path/to/Ozimmi EMOJI botim"
```
Bir necha marta ishlatish xavfsiz — asl fayllar o'zgartirilmaydi.

---

## 🤖 Telegram BotFather sozlamalari

1. **Bot yaratish:** @BotFather → `/newbot` → token oling → `.env` dagi `BOT_TOKEN` ga qo'ying.
2. **Bot username:** `.env` dagi `BOT_USERNAME` ga (@ siz) yozing.
3. **Mini App / Web App ulash:**
   - @BotFather → `/newapp` (yoki bot sozlamalari → *Configure Mini App*)
   - Web App URL sifatida frontend HTTPS manzilingizni bering (masalan `https://your-domain.com`).
4. **Menu tugmasi (ixtiyoriy):** @BotFather → *Bot Settings → Menu Button* → Web App URL.
5. **To'lovlar (Stars):** Telegram Stars uchun alohida provider token KERAK EMAS
   (kod `currency=XTR`, `provider_token=""` ishlatadi). Faqat webhook o'rnatilgan bo'lsa bas.

---

## 🔧 Web App'ni botga ulash (qisqacha)

1. Frontendni HTTPS domenda joylang (`docker compose` + reverse-proxy).
2. `.env` da `WEBAPP_URL=https://your-domain.com`.
3. BotFather'da Web App URL = shu domen.
4. `python -m scripts.set_webhook https://your-domain.com` — to'lov webhook'i uchun.
5. Botni oching → Menu tugmasi yoki `/start` dagi Web App tugmasi orqali Mini App ochiladi.

---

## 🔑 Qaysi .env qiymatlarni to'ldirish kerak

| O'zgaruvchi | Majburiy | Izoh |
|-------------|:--------:|------|
| `BOT_TOKEN` | ✅ | @BotFather beradigan token |
| `BOT_USERNAME` | ✅ | Bot useri (@ siz) — referral havolalari uchun |
| `ADMIN_IDS` | ✅ | Admin Telegram ID'lari, vergul bilan |
| `SECRET_KEY` | ✅ | Uzun tasodifiy satr (token + webhook secret) |
| `WEBAPP_URL` | ✅ | Mini App HTTPS manzili |
| `DATABASE_URL` | ⬜ | Default SQLite; PostgreSQL ixtiyoriy |
| `LOG_CHAT_ID` | ⬜ | Log kanali ID |
| `CORS_ORIGINS` | ⬜ | Frontend domeni |

> ⚠️ **Xavfsizlik:** eski koddagi haqiqiy bot tokeni bu loyihaga **ko'chirilmagan**.
> Agar u ochiq internetga tushган bo'lsa, @BotFather orqali **bekor qilib, yangi token oling**.

---

## 🧪 Testlar

```bash
cd backend && source .venv/bin/activate
pytest -q
```
Testlar quyidagilarni qamrab oladi: initData validatsiya, admin avtorizatsiya,
HEX validatsiya, narx validatsiya, kredit tranzaksiyasi, referral anti-abuse,
buyurtma holat o'tishlari, to'lov idempotency, shablon validatsiya, render servis.

Frontend build:
```bash
cd frontend && npm run build
```

---

## 🎨 Shablon va shriftlar

- **Shablonlar:** `backend/app/assets/`
  - `templates/*.json` — Name emoji (28)
  - `templates_tgs/*.json` — Logo/Text (103)
  - `templates_tgs2/*.json` — Extra 1 (39)
  - `templates_tgs3/*.json` — Extra 2 (31)
- **Yangi shablon qo'shish:** tegishli papkaga `NNN.json` (masalan `104.json`) qo'ying —
  API fayllar sonini avtomatik hisoblaydi. Preview custom emoji ID'ini
  `app/renderers/logo_emoji_ids.py` ga qo'shsangiz, galereyada animatsiya ko'rinadi.
- **Shriftlar:** `backend/app/assets/fonts/*.ttf`. Yangi shrift qo'shish uchun
  `.ttf` faylни qo'ying va `app/renderers/logo_engine.py` dagi `FONT_OPTIONS` /
  `PROFILE_FONT_OPTIONS` ga kalit qo'shing.

---

## 🩺 Troubleshooting

| Muammo | Yechim |
|--------|--------|
| "initData xatosi" | Mini App'ni Telegram ichida oching; `BOT_TOKEN` to'g'riligini tekshiring |
| Invoice yaratilmadi | `BOT_TOKEN` sozlanganini va botning to'lovga ruxsati borligini tekshiring |
| To'lovdan keyin pack kelmadi | Webhook o'rnatilganini tekshiring (`scripts.set_webhook`) |
| Preview bo'sh | Backend loglarini ko'ring; shablon/shrift fayllari joyidami tekshiring |
| Obuna tekshiruvi ishlamayapti | Bot majburiy kanalda **admin** bo'lishi kerak |
| CORS xatosi | `.env` dagi `CORS_ORIGINS` ga frontend domenini qo'shing |

---

## 📜 Litsenziya / eslatma

Bu loyiha mavjud "Ozimmi EMOJI botim" loyihasining render mantig'ini saqlab qolgan holda
qayta qurilgan. Ishlab chiqarishga tayyor, lekin har bir deploy o'z `BOT_TOKEN`,
`ADMIN_IDS` va `SECRET_KEY` qiymatlarini kiritishi shart.
