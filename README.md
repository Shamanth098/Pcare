# PCare AI — Healthcare Triage & Clinic Discovery Portal

**PCare AI** is an intelligent medical triage and clinic discovery web application designed for rapid symptom assessment and emergency routing. It provides patients with instantaneous clinical guidance—categorizing complaints into **Self-Care**, **OPD Consult**, or **Emergency** tiers—while dynamically surfacing verified open clinics and trauma centers across Bengaluru.

---

## 🚀 Key Features

- **Instant 0ms Red-Flag Detection**: Pre-filters life-threatening red-flag keywords (chest pain, stroke symptoms, acute respiratory distress) to immediately trigger emergency routing with zero network latency.
- **Resilient AI Model Cascade**: Employs Google GenAI Flash models in a cascading sequence (`gemini-3.8-flash` → `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite`) with a 5-second per-model timeout.
- **Zero-Downtime Clinical Rule Engine**: Built-in deterministic fallback engine ensures the user interface never crashes even during upstream quota exhaustion (503) or offline scenarios.
- **Nearby Clinic Discovery & Urgency Highlighting**: Interactive card grid mapping verified clinics in Bengaluru. Open trauma and OPD centers are automatically highlighted when high-acuity symptoms are detected.
- **Bulk CSV Data Pipeline**: Custom Django management command (`import_clinics`) for seamless ingestion and updating of clinic registries from CSV files.
- **Clinic Staff Authentication**: Built-in authentication system (`/login/`, `/register/`, `/logout/`) allowing clinic operators to manage records via Django Admin, while keeping patient triage 100% public.
- **Accessible, Responsive UI**: Tailwind CSS single-page layout with dark/light mode toggle, mobile navigation drawer, and 1-click clinical intake note copying.

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Django Framework
- **Database**: SQLite
- **AI / LLM**: Google GenAI SDK (`google-genai`)
- **Frontend**: HTML5, Tailwind CSS (via CDN), Vanilla JavaScript
- **Mapping & Geolocation**: Google Maps URLs / External Leaflet.js compatibility
- **Environment Management**: `python-dotenv`

---

## 💻 Step-by-Step Setup Guide

Follow these steps in your terminal (Command Prompt / PowerShell / Bash):

### 1. Clone & Navigate to Project
```bash
cd pcare
```

### 2. Create & Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the template file to `.env`:
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```
Open `.env` in any text editor and add your credentials:
```ini
DJANGO_SECRET_KEY=your-django-secret-key-here
GEMINI_API_KEY=your-gemini-api-key-here
```
*(Note: A built-in fallback parser is included in `settings.py` so the project runs cleanly even in standard environments.)*

### 5. Apply Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Import Clinic Data
Ingest the Bengaluru clinic registry into SQLite:
```bash
python manage.py import_clinics --csv bangalore_clinics.csv
```

### 7. Create an Administrator / Staff Account (Optional)
```bash
python manage.py createsuperuser
```

### 8. Run the Development Server
```bash
python manage.py runserver
```

Open your browser and navigate to:
- **Public Patient Portal**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Staff Login**: [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)
- **Staff Registration**: [http://127.0.0.1:8000/register/](http://127.0.0.1:8000/register/)
- **Admin Dashboard**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 📁 Project Structure

```
pcare/
│
├── pcare/                              ← Project configuration package
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py                         ← Root URL router
│   └── settings.py                     ← Settings with python-dotenv loading
│
├── portal/                             ← Core healthcare & triage application
│   ├── __init__.py
│   ├── admin.py                        ← Clinic model admin registration
│   ├── apps.py
│   ├── models.py                       ← Clinic database model
│   ├── urls.py                         ← Triage API & auth endpoints
│   ├── views.py                        ← Async triage cascade, rules & auth views
│   ├── tests.py                        ← Automated test cases
│   │
│   ├── data/
│   │   └── clinics.json                ← Fallback clinic seed data
│   │
│   ├── management/
│   │   └── commands/
│   │       └── import_clinics.py       ← CSV ingestion management command
│   │
│   └── templates/
│       └── portal/
│           ├── index.html              ← Single-page triage UI & clinic directory
│           ├── login.html              ← Staff login template
│           └── register.html           ← Staff registration template
│
├── bangalore_clinics.csv               ← Verified clinic dataset (61 clinics)
├── requirements.txt                    ← Pinned project dependencies
├── manage.py                           ← Django CLI entrypoint
├── .env.example                        ← Environment configuration template
├── .env                                ← Local secrets (untracked)
└── README.md                           ← Project documentation
```

---

## ⚖️ Clinical Disclaimer

*PCare AI is an informational decision-support tool and does not provide formal medical diagnoses. For life-threatening emergencies, patients should immediately contact national emergency services (112 / 108 in India) or report to the nearest hospital emergency room.*

