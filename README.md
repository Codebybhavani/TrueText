# TrueText — AI Text Detection & Integrity Platform

A working full-stack demo: Flask + SQLite backend, JWT auth, TF-IDF + Logistic
Regression AI-text classifier, LIME word-level explanations, PDF report export,
and a plain HTML/JS dashboard (no React/npm build step needed).

## What's inside
```
truetext/
├── backend/
│   ├── app.py              # Flask app: auth + detection + history + PDF API
│   ├── database.py         # SQLite setup (users, detections)
│   ├── ml_model.py         # predict() + LIME explanation + style stats
│   ├── features.py         # stylometric features (sentence uniformity, etc.)
│   ├── generate_dataset.py # creates a demo dataset to test the pipeline
│   └── train_model.py      # trains model.pkl from the dataset
├── templates/
│   ├── login.html
│   └── dashboard.html
├── static/
│   ├── style.css
│   └── script.js
└── requirements.txt
```

## 1. Prerequisites
- Python 3.9+ installed (check with `python --version` or `python3 --version`)

## 2. Setup (run these in Command Prompt / Terminal)

```bash
# 1. Unzip the project, then move into it
cd truetext

# 2. Create and activate a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Go into the backend folder
cd backend

# 5. Generate a demo training dataset (small, synthetic — for testing only)
python generate_dataset.py

# 6. Train the model (creates model.pkl)
python train_model.py

# 7. Run the app
python app.py
```

Now open your browser at: **http://127.0.0.1:5000**

Sign up with a username/email/password, log in, paste some text (5+ words),
and click Detect. You'll see the AI/Human probability, a gauge, LIME-highlighted
influential words, style stats, and can download a PDF report. History and
stats persist in `backend/app.db` (SQLite file, created automatically).

