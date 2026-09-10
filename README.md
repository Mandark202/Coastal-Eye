# 🌊 Coastal Threat Alert System (CTAS)

> **HackGenesis Hackathon Project** — A real-time AI-powered platform for coastal disaster management, community reporting, and emergency response coordination.

---

## 📖 Overview

The **Coastal Threat Alert System (CTAS)** is a full-stack web application that integrates AI-driven threat detection, community-based hazard reporting, and authority-level emergency response tools into a single unified platform. It is designed to protect coastal communities across India (and globally) from natural disasters such as cyclones, tsunamis, floods, oil spills, and algal blooms.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🗺️ **Live Threat Map** | Interactive global heatmap showing real-time coastal risk zones using simulated satellite & IoT data |
| 📢 **Community Posts** | Citizens can report hazards with photos, locations, and descriptions |
| 🤖 **AI Risk Scoring** | Automatic risk score (0–100) assigned to every post using NLP-based heuristics |
| 🚨 **Smart Alerts** | Dynamic, location-aware alerts generated from satellite, buoy, radar, and IoT sources |
| 🆘 **Voice SOS** | Voice-activated emergency SOS with transcript analysis, severity scoring, and geolocation |
| 🧭 **Evacuation Engine** | Computes optimal evacuation routes based on threat proximity |
| 🏥 **Resource Allocation** | AI prioritizes dispatch of ambulances, food, medical kits, and rescue boats |
| 🔍 **Fake Report Detection** | Authenticity scoring system that flags spam, duplicates, and geo-mismatched reports |
| 📊 **Trend Analysis** | Tracks community-reported trends over time for data-driven decision making |
| 🛡️ **Authority Dashboard** | Dedicated dashboard for officials to manage aid requests, allocate resources, and monitor alerts |
| 🤝 **AI Copilot** | Integrated AI assistant to help users and authorities with threat assessment and response planning |
| 🔐 **Auth System** | JWT-based user authentication with role-based access (user / authority) |

---

## 🏗️ Project Structure

```
HackGenesis_Temporary/
│
├── backend/                   # FastAPI Python backend
│   ├── main.py                # App entry point, router registration, CORS
│   ├── models.py              # SQLAlchemy ORM models
│   ├── database.py            # Database engine and session setup
│   ├── ai_logic.py            # AI/heuristic risk scoring and heatmap generation
│   ├── fake_detection.py      # Fake report analysis engine
│   ├── evacuation_engine.py   # Evacuation route computation
│   ├── prediction_engine.py   # Disaster prediction models
│   ├── resource_allocator.py  # Smart resource dispatch logic
│   │
│   ├── routers/               # API route handlers
│   │   ├── auth.py            # /auth — Login, Register
│   │   ├── posts.py           # /posts — Community hazard reports
│   │   ├── alerts.py          # /alerts — Real-time threat alerts
│   │   ├── authority.py       # /authority — Aid requests & management
│   │   ├── trends.py          # /trends — Community trend data
│   │   ├── copilot.py         # /copilot — AI assistant
│   │   ├── voice_sos.py       # /voice-sos — Voice emergency SOS
│   │   ├── predictions.py     # /predictions — Threat predictions
│   │   ├── evacuation.py      # /evacuation — Evacuation routes
│   │   ├── fake_reports.py    # /fake-reports — Authenticity checking
│   │   └── resource_routes.py # /resources — Resource allocation
│   │
│   ├── services/              # Business logic services
│   └── utils/                 # Shared utilities
│
├── frontend.html              # Main citizen-facing web app
├── authority_dashboard.html   # Authority/official control panel
├── map.html                   # Standalone threat map view
├── posts.html                 # Community posts feed
├── trends.html                # Trend analytics page
│
├── requirements.txt           # Python dependencies
├── sql_app.db                 # SQLite database (auto-created)
├── seed.py                    # Database seeder with sample data
├── seed_resources.py          # Resource center seeder
└── manage_db.py               # Database management utilities
```

---

## 🛠️ Tech Stack

### Backend
- **Framework:** FastAPI (Python)
- **Database:** SQLite via SQLAlchemy ORM
- **AI/ML:** OpenAI API + custom heuristic engines
- **Auth:** JWT (JSON Web Tokens)
- **Server:** Uvicorn (ASGI)

### Frontend
- **Pure HTML5 + CSS3 + JavaScript** (no framework)
- **Leaflet.js** — Interactive map rendering
- **Charts.js** — Trend visualizations
- **REST API** integration with the FastAPI backend

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- pip

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd HackGenesis_Temporary
```

### 2. Create & Activate a Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Configure OpenAI API Key
The AI Copilot and some features use OpenAI. Set your API key as an environment variable:
```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."

# macOS/Linux
export OPENAI_API_KEY="sk-..."
```

### 5. Seed the Database (Optional but Recommended)
```bash
python seed.py
python seed_resources.py
```

### 6. Start the Server
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
```

### 7. Open the App

| Page | URL |
|---|---|
| Main App | http://127.0.0.1:8001/ |
| Authority Dashboard | http://127.0.0.1:8001/authority_dashboard.html |
| Threat Map | http://127.0.0.1:8001/map.html |
| Community Posts | http://127.0.0.1:8001/posts.html |
| Trends | http://127.0.0.1:8001/trends.html |
| API Docs | http://127.0.0.1:8001/docs |

---

## 🤖 AI Modules

### Risk Scoring
Assigns a 0–100 priority score to community posts based on keywords:
- **P1 (Life-threatening):** tsunami, cyclone, flood, drowning, SOS — +40 pts each
- **P2 (Significant threat):** oil spill, pollution, storm — +20 pts each
- **P3 (Environmental):** algal bloom, erosion, waste — +10 pts each

### Aid Priority
Scores humanitarian aid requests and assigns High / Medium / Low urgency:
- Medical/Rescue requests: base +50 pts
- Keywords like "trapped", "elderly", "pregnant", "baby": +15 pts each

### Fake Report Detection
Analyzes community reports for:
- Authenticity score (0–100)
- Duplicate probability
- Spam probability
- Geographic mismatch detection
- Flagged suspicious keywords

### Dynamic Alert Generation
Simulates real-time alerts from multiple data sources (Sentinel-1 Satellite, Coastal Buoy Sensors, MetDept Radar, IoT Networks) for 8 high-risk Indian coastal zones.

---

## 🗄️ Database Models

| Model | Description |
|---|---|
| `User` | Citizen or authority account |
| `Post` | Community hazard report with AI risk score |
| `Comment` | Comments on posts |
| `Alert` | Real-time threat alert with geo-coordinates |
| `AidRequest` | Humanitarian aid request with AI urgency score |
| `VoiceSOS` | Voice emergency SOS with transcript and severity |
| `FakeReportAnalysis` | Authenticity analysis result for a post |
| `ResourceCenter` | Emergency resource depot (ambulances, food, boats) |
| `ResourceAllocation` | Dispatched resource record linked to aid request |

---

## 🌐 API Endpoints (Summary)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Login and get JWT token |
| `GET/POST` | `/posts` | Get all / create hazard post |
| `GET` | `/alerts` | Get dynamic real-time alerts |
| `GET/POST` | `/authority/aid-requests` | Manage humanitarian aid requests |
| `GET` | `/trends` | Get trend analytics data |
| `POST` | `/copilot/chat` | Chat with AI copilot |
| `POST` | `/voice-sos` | Submit a voice SOS transcript |
| `GET` | `/evacuation/routes` | Get evacuation routes |
| `POST` | `/fake-reports/analyze` | Analyze a report for authenticity |
| `GET/POST` | `/resources` | Manage resource centers and allocations |

Full interactive API docs available at: http://127.0.0.1:8001/docs

---

## 👥 User Roles

| Role | Capabilities |
|---|---|
| **User (Citizen)** | Submit posts, request aid, use Voice SOS, view alerts and map |
| **Authority (Official)** | All citizen features + manage aid requests, allocate resources, view authority dashboard |

---

## 🌍 Targeted Threat Zones

The system currently monitors the following Indian coastal regions:
- Mumbai Coast — Cyclone / Storm Surge
- North Goa — Algal Bloom / Pollution
- Coastal Kerala — Heavy Rainfall / Flooding
- Chennai — Seismic / Tsunami Risk
- Puri, Odisha — High Tide / Cyclone
- Gujarat Coast / Surat — River Surge / Flood
- Andaman Islands — Tropical Storm

---

## 📦 Dependencies

```
fastapi
uvicorn
sqlalchemy
pydantic
requests
openai
```

---

## 🏆 Built For

**HackGenesis Hackathon** — Protecting coastlines through AI, community, and technology.

---

## 📄 License

This project was built for hackathon purposes. All rights reserved by the team.
