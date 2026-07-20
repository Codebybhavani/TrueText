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

## 3. Using a REAL dataset (important for your final-year project)

The `generate_dataset.py` script only makes ~600 fake rows so you can test
that the whole app works. For real accuracy you need a real dataset:

- Kaggle: "LLM - Detect AI Generated Text" competition dataset
- Hugging Face: `artem9k/ai-text-detection-pile`

Download one of these as a CSV with two columns: `text` and `label`
(`label` = 1 for AI-generated, 0 for human-written), then run:

```bash
python train_model.py --csv path/to/your_real_dataset.csv
```

This overwrites `model.pkl` with a model trained on real data. No other code
changes are needed — `app.py` and `ml_model.py` will automatically use the new model.

## 4. Upgrading to a transformer model (DeBERTa/RoBERTa) later

Right now `ml_model.py` uses a scikit-learn pipeline (TF-IDF + Logistic
Regression) saved with `joblib`. To upgrade to the "Option 2/3" transformer
approach from your project brief:

1. Fine-tune `roberta-base` or `microsoft/deberta-v3-base` on your dataset
   using Hugging Face `transformers` + `Trainer` (this needs a GPU — Colab works).
2. Save the fine-tuned model with `model.save_pretrained("deberta_model/")`.
3. Replace the body of `predict()` in `ml_model.py` to load the transformer
   with `AutoModelForSequenceClassification` + `AutoTokenizer`, run
   `torch.softmax(outputs.logits, dim=1)` for probabilities, and use
   `shap.Explainer` (works directly with Hugging Face pipelines) instead of LIME.
4. Everything else (Flask routes, auth, database, frontend) stays the same.

## 5. Troubleshooting
- **"model.pkl not found"** → you skipped step 5/6 above; run `generate_dataset.py`
  then `train_model.py` inside `backend/`.
- **Port 5000 already in use** → edit the last line of `app.py`:
  `app.run(debug=True, port=5001)` and open `http://127.0.0.1:5001` instead.
- **CORS/connection errors in browser console** → make sure you're opening
  `http://127.0.0.1:5000` (served by Flask itself), not opening `login.html`
  directly as a `file://` path.
- To reset all users/history, just delete `backend/app.db` and restart the app.

## 6. New in this version

- **Real LIME explanation panel**: previously "Style Signals" showed only raw
  stylometric numbers (burstiness, vocab richness, etc.) — those are genuinely
  *not* LIME output, just extracted feature values, and the earlier version
  didn't make that distinction clear. Now there's a separate **"Explainability
  — LIME Word Contributions"** section with an actual horizontal bar chart of
  LIME's per-word weights (positive = supports AI, negative = supports Human),
  plus the same weights shown inline over the original text. "Style Signals"
  is now explicitly labeled as extracted features, not a LIME explanation.
- **PDF / DOCX upload in the Detector panel**: you can now drag-and-drop or
  select a `.pdf`, `.docx`, or `.txt` file directly in the Detector panel (not
  just Instructor Mode) — text is extracted server-side (`file_extract.py`,
  using `pdfplumber` / `python-docx`) and run through the same detector as
  pasted text. Scanned/image-only PDFs with no selectable text will return a
  clear error rather than silently failing.
- **Sidebar layout**: replaced the top tab bar with a persistent left sidebar
  (logo, Detector / Instructor Mode navigation, theme toggle, account info) —
  a more conventional dashboard/app layout instead of a single scrolling page.
- **Rebrand + professional UI/UX**: renamed to **TrueText**, redesigned with a
  warm beige/cream palette, serif headings (Fraunces) + clean sans body
  (Inter), solid cards with subtle borders/shadows instead of neon
  glassmorphism, and a dark-mode toggle for a low-light option. Colors:
  terracotta = AI signal, sage green = Human signal — consistent across the
  gauge, badges, highlighted words, LIME bars, and batch table.
- **Live check**: toggle "Live check" on above the textarea — the AI score updates
  automatically ~1 second after you stop typing, no button click needed.
- **Instructor Batch Mode**: click the "🎓 Instructor Mode" tab at the top. Drag &
  drop (or select) several `.txt` files at once — e.g. one per student — set a
  flagging threshold, and get a sortable class report (click column headers to
  sort) with a flagged count, class average AI score, and CSV export. Each file
  is also saved to your personal history under the hood (tagged with a batch ID
  in the database) for later review.
  - Currently only `.txt` files are supported for batch upload. To support
    `.docx`/`.pdf` uploads too, extract text server-side first (e.g. with
    `python-docx` or `pdfplumber`) before calling `ml_model.predict_fast()`.
- **Plagiarism / Similarity Check** (also in Instructor Mode): every pair of
  uploaded submissions is compared to every other pair using TF-IDF cosine
  similarity — completely independent of the AI/Human detector. Pairs above
  your chosen similarity threshold show up in their own table (e.g. two
  students who copied from each other), with an "Export CSV" available for the
  main table. This catches copying between students, not just AI generation.

## 7. Accuracy fix — why it was misclassifying, and what changed

The original demo dataset (`generate_dataset.py`) used only ~10 fixed sentence
templates per class. The model learned a shortcut: "contains the word
'furthermore' → AI", "sounds casual → Human" — which breaks immediately on
real text that doesn't match those exact phrases. That's why real human
writing using formal words got called AI, and real AI text that avoided those
buzzwords got called human.

Two changes fix this:

1. **`features.py`** — the model no longer relies on word choice alone. It now
   also uses real stylometric signals: sentence-length uniformity
   ("burstiness" — AI text tends to have very uniform sentence lengths),
   contraction rate, first-person pronoun rate, passive-voice rate, vocabulary
   richness, and function-word ratio. These are the same signal families real
   AI-detectors use, and they generalize far better to text the model has
   never seen.
2. **`generate_dataset.py`** — the synthetic dataset is now ~5x larger (3,000
   rows), built from many more sentence templates and topics, and deliberately
   includes "hard" examples: formal-sounding human writing (an essay with a
   personal aside) labeled Human, and casual-sounding AI filler labeled AI —
   so the model can't just shortcut on tone/formality either.

After retraining, it correctly classified realistic out-of-template test
sentences (a casual diary entry, a formal cover letter, a "textbook" AI
paragraph about climate change, etc. — none of which were in the training
templates). One category it still struggles with, like every commercial
detector: **AI text deliberately written to sound casual/human** (e.g. "so
like, ai is honestly changing so much stuff rn..."). That's a genuinely hard,
adversarial case — not a bug — and is worth mentioning as a known limitation
in your project report/demo.

**Bottom line**: this synthetic dataset is still for testing the pipeline, not
for a real dissertation-grade accuracy claim. For real reliability, plug in a
real dataset (Kaggle's "LLM - Detect AI Generated Text" or HuggingFace's
`artem9k/ai-text-detection-pile`) with:
```bash
python train_model.py --csv your_real_dataset.csv
```
`features.py` and the FeatureUnion pipeline work unchanged with real data —
you don't need to touch anything else.

## 8. Ideas to add uniqueness (from your notes — feasible ones)
- Sentence-level detection: run `predict()` per-sentence and color-code paragraphs.
- Writing profile: aggregate a user's `ai_probability` history over time (you
  already store `created_at` per detection — just group by month in a new query).
- Humanization suggestions: a simple rule-based rewrite list (replace common
  "AI phrases" with casual alternatives) — no ML needed, just a dictionary lookup.
- AI fingerprinting / human-editing estimation: label these clearly as
  experimental/estimated in the UI, since they can't be verified with certainty.
