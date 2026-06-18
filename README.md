# 📡 Software Validation Agent

A lightweight automation system that monitors Gmail firmware validation emails, extracts firmware data using regex, stores results in a local SQLite database, and generates weekly HTML reports automatically.

---

## 🚀 Features

- 📥 Gmail API integration (OAuth2)
- 🔍 Regex-based firmware parsing (no AI dependency)
- 🗄️ Local SQLite database storage
- 📊 Device lifecycle tracking (active / updated / wait_for_updated)
- 📧 Weekly HTML report generation
- ⏱️ Scheduled automatic execution
- 🧾 Event history tracking per firmware update

---

## 📁 Project Structure

```text
firmware-agent/
│
├── main.py                # Entry point (scheduler)
├── gmail_agent.py        # Gmail API integration
├── parser.py             # Regex firmware parser
├── db.py                 # SQLite database layer
├── report_agent.py      # Weekly report generator
├── scheduler.py         # Job scheduler
├── config.py            # Configuration
│
├── .env                 # Environment variables (NOT committed)
├── firmware.db          # Local database (NOT committed)
├── logs/                # Runtime logs
└── reports/             # Generated HTML reports
