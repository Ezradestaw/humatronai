# Humatron Telegram Bot & Companion Backend Service

Official companion service and Telegram Bot interface for **Humatron** ([https://humatron.me](https://humatron.me/)), primarily targeting university and college students.

The bot provides students with instant, mobile-friendly access to document productivity tools, account synchronization, usage monitoring, student discount verification, and subscriptions.

---

## 🏛️ System Architecture

The architecture maintains the Humatron website as the primary web application while providing the Telegram bot as a synchronized official companion:

```
 Telegram User (Mobile / Desktop)
                 │
                 ▼
     Telegram Bot (aiogram 3.x)
                 │
                 ▼
      Humatron Service Layer
  (Account, PDF, Subscription, Payment, Student, Notification)
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
  FastAPI Endpoints     PostgreSQL 18
 (Webhook / Web Auth)   (Relational DB)
```

### Key Architectural Principles
- **Centralized Business Rules**: Handlers in the Telegram bot do not contain raw business or payment logic. All actions pass through decoupled service facades (`PDFService`, `SubscriptionService`, `PaymentService`, `AccountService`, `StudentService`).
- **Single Source of Truth**: User records, usage counters, and subscriptions reside in the shared PostgreSQL database (`humatron_db`).
- **Zero Disk Leakage**: PDF operations occur in isolated memory streams and temporary working directories that are guaranteed to be cleaned up immediately upon completion.
- **Cryptographic Account Linking**: Users link their accounts via short-lived (10-minute) HMAC-SHA256 signed one-time tokens. Passwords are never transmitted through or stored in Telegram.

---

## 🚀 Key Features

1. **📄 Academic PDF Tools**:
   - **Document Inspection**: Validates PDF structure, page count, and title.
   - **Stream Compression**: Compresses content streams and strips redundant objects to produce lightweight files for university submissions.
   - **Text Extraction**: Extracts clean text from reading materials and lecture notes.
   - **Security**: Enforces magic bytes check (`%PDF-`), 20MB file size limits, 300 page limits, and sanitized filenames to prevent directory traversal.
2. **👤 Account Synchronization**:
   - Secure one-time token generation for web-to-telegram account linking.
   - Seamless unlinking at any time.
3. **📊 Live Usage Dashboard**:
   - Visual progress bar showing consumed vs. remaining monthly document quotas.
   - Renewal and reset schedule display.
4. **💳 Subscriptions & Binance Pay**:
   - **Free Plan**: 10 files / month.
   - **Student Plan**: 50 files / month ($5 USDT).
   - **Pro Plan**: 200 files / month ($50 USDT).
   - **Binance Pay Manual Verification**: Bot displays the official Binance QR code (recipient: `Burton Knick rZXe`). Users submit their Transaction ID (TxID) or payment screenshot directly in the bot. Administrators review submissions and approve or reject them with a single tap in Telegram.
   - **Immediate Activation**: Once an admin taps "Approve", the user is instantly credited with their new plan and receives an alert in Telegram.
5. **🎓 Student Discount Program**:
   - Academic email verification for accredited university domains (`.edu`, `.edu.et`, `.ac.*`).
   - One-time verification code workflow that automatically activates the student discount tier.
6. **🛡️ Administrator Panel**:
   - Restricted to authorized Telegram User IDs and database admin flags.
   - Live system statistics (active users, total processed documents, paid subscriptions).
   - Broadcast system for official announcements (respects user notification preferences).

---

## 📋 Prerequisites

- **Python**: Python 3.12+
- **PostgreSQL**: Version 15+ (Version 18 tested and verified)
- **Telegram Bot Token**: Issued from [@BotFather](https://t.me/BotFather)

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory (based on `.env.example`):

```bash
cp .env.example .env
```

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Bot API token from BotFather | `8920812675:AAGjTm-...` |
| `ADMIN_TELEGRAM_IDS` | Comma-separated list of Admin Telegram IDs | `123456789,987654321` |
| `TELEGRAM_PROXY` | *(Optional)* Proxy URL if Telegram API is restricted | `socks5://127.0.0.1:1080` |
| `ENVIRONMENT` | Deployment environment | `development` or `production` |
| `HUMATRON_API_BASE_URL` | Official web application base URL | `https://humatron.me` |
| `HUMATRON_SECRET_KEY` | Secret key for HMAC token signing (64 hex characters) | `94e77248f278...` |
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://postgres:pass@localhost:5432/humatron_db` |
| `USE_WEBHOOK` | Set `true` in production to use webhooks | `false` |
| `TELEGRAM_WEBHOOK_URL`| Public HTTPS webhook endpoint | `https://api.humatron.me/api/telegram-webhook` |
| `TELEGRAM_WEBHOOK_SECRET` | Secret token to authenticate webhook updates | Random string |
| `MAX_PDF_SIZE_MB` | Maximum PDF upload size in megabytes | `20` |
| `MAX_PDF_PAGES` | Maximum PDF pages processed per document | `300` |
| `TELEBIRR_APP_ID` | Telebirr Merchant App ID (Production) | Optional / Sandbox fallback |
| `BINANCE_PAY_API_KEY` | Binance Pay Merchant API Key (Production) | Optional / Sandbox fallback |

---

## 🛠️ Installation & Local Development

### 1. Create Virtual Environment & Install Dependencies
```bash
# Clone or navigate to the project directory
cd humatron

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize Database Schema
Ensure PostgreSQL is running locally and database `humatron_db` exists:
```bash
python -c "import asyncio; from core.database import init_db; asyncio.run(init_db())"
```

### 3. Run the Telegram Bot (Long-Polling Mode)
```bash
python -m bot.main
```

### 4. Run the Companion FastAPI Service
In a separate terminal:
```bash
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🤖 BotFather Configuration Instructions

To set up the bot identity and commands in Telegram, open [@BotFather](https://t.me/BotFather) and execute the following:

### 1. Set Bot Name
`/setname` -> Choose your bot -> `Humatron`

### 2. Set Description
`/setdescription` -> Choose your bot ->
```
Official companion bot for Humatron (https://humatron.me).
Process academic PDFs, compress documents, check student quotas, verify student discounts, and manage your account.
```

### 3. Set About Text
`/setabouttext` -> Choose your bot ->
```
Humatron is a productivity and digital document processing platform built for university and college students.
```

### 4. Set Official Commands
`/setcommands` -> Choose your bot -> Paste the exact list below:
```
start - Open Humatron dashboard & main menu
account - View profile & link Humatron account
pdf - Access student PDF productivity tools
usage - Check monthly quota & remaining usage
subscription - View plans, upgrade & payment options
student - Verify educational status & claim discount
help - Frequently asked questions & official support
settings - Manage notifications & preferences
admin - Administrator control panel (authorized only)
```

---

## 🧪 Automated Testing

The project includes unit and integration tests with 100% pass rate:
- Security token creation, signature verification, and expiration
- PDF magic byte header validation and directory traversal prevention
- In-memory PDF inspection, text extraction, and stream compression
- Subscription quota enforcement and tiered upgrades
- Telebirr & Binance Pay payment order initiation
- Educational email domain verification and student discount activation
- FastAPI health check and token verification endpoints

Run the test suite:
```bash
python -m pytest tests/ -v
```

---

## 🚢 Production Deployment (Linux / Ubuntu)

### 1. Systemd Service Setup
1. Copy the systemd service template to system services:
   ```bash
   sudo cp deploy/humatron-bot.service /etc/systemd/system/humatron-bot.service
   ```
2. Create dedicated non-root system user:
   ```bash
   sudo useradd -r -s /bin/false humatron
   sudo chown -R humatron:humatron /opt/humatron
   ```
3. Enable and start the bot service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable humatron-bot
   sudo systemctl start humatron-bot
   sudo systemctl status humatron-bot
   ```

### 2. Nginx Reverse Proxy Setup
1. Copy the Nginx configuration:
   ```bash
   sudo cp deploy/nginx-humatron.conf /etc/nginx/sites-available/humatron
   sudo ln -s /etc/nginx/sites-available/humatron /etc/nginx/sites-enabled/
   ```
2. Acquire SSL certificate with Certbot:
   ```bash
   sudo certbot --nginx -d api.humatron.me
   ```
3. Test and reload Nginx:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

### 3. Set Webhook with Telegram
Once your HTTPS endpoint is live, configure the webhook:
```bash
curl -F "url=https://api.humatron.me/api/telegram-webhook" \
     -F "secret_token=YOUR_TELEGRAM_WEBHOOK_SECRET" \
     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
```

---

## 🔒 Security & Privacy Audit Checklist

- [x] **No hard-coded secrets**: Real bot tokens and secrets are stored exclusively in `.env` (gitignored).
- [x] **No passwords via Telegram**: Account linking uses one-time signed HMAC tokens expiring in 10 minutes.
- [x] **Safe PDF Processing**: Validates `%PDF-` magic bytes, prevents arbitrary file execution, enforces a 20MB limit.
- [x] **Path Traversal Shield**: All uploaded filenames are stripped of directories and assigned UUID internal identifiers.
- [x] **Zero Disk Leakage**: Memory buffers and temporary directories are purged in `finally` blocks.
- [x] **Rate Limiting**: Leaky-bucket middleware throttles spam and protects server resources.
- [x] **Sanitized Logging**: RegEx formatter automatically redacts bot tokens, authorization keys, and passwords before logging.
- [x] **Admin Authorization**: Multi-layered checks verify Telegram user IDs and database role flags.

---

## 📞 Support & Contacts

- **Website**: [https://humatron.me](https://humatron.me/)
- **Contact Page**: [https://humatron.me/contact](https://humatron.me/contact)
- **Official Email**: `zuhuraengineering@gmail.com`
- **Telegram Channel**: [@ZuhuraEngineering](https://t.me/ZuhuraEngineering)
