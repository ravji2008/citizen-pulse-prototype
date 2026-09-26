# CitizenPulse — AI for Digital Public Infrastructure & Governance

**Track 1 prototype — Google "Build with AI: Code for Communities" (BRICS: Innovation)**

A multilingual, voice-and-text platform that aggregates citizen development
requests, cross-references them with state-level demographic and
infrastructure-index data, and surfaces ranked "demand hotspots" for
policymakers — designed to scale across Indian states, not just one city.

---

## How it works

```
 Citizen (voice/text, any language)
        │
        ▼
 Web form  ──►  /api/submit  ──►  Google Gemini (GenAI)
                                     │  • language detection + translation
                                     │  • category classification
                                     │  • urgency & sentiment scoring
                                     ▼
                              SQLite: feedback table
                                     │
                    joined with  state_index (population, infra index)
                                     ▼
                     /api/hotspots — priority-ranked demand hotspots
                                     ▼
                         Policy Dashboard (charts + ranked table)
```

- **Frontend**: single-page app (`templates/index.html` + `static/`), English/Hindi
  UI toggle, and voice input via the browser's Web Speech API (supports
  `en-IN`, `hi-IN`, `bn-IN`, `ta-IN`, `te-IN`, `mr-IN`, `gu-IN` — extend the
  list in `static/js/app.js` for more languages).
- **Backend**: Flask API (`app.py`) that classifies each complaint with
  **Google Gemini** (`gemini-1.5-flash`) — extracting language, an English
  translation, an infrastructure category, an urgency score, and sentiment.
  If no `GEMINI_API_KEY` is set, it falls back to a rule-based keyword
  classifier so the whole flow still runs end-to-end for a demo.
- **Prioritization**: `/api/hotspots` joins complaint volume/urgency with a
  state's infrastructure index to rank where investment is most needed —
  see the `priority_score` formula documented in `app.py`.
- **Data**: `state_index` table ships with illustrative sample figures for
  16 major states (population, infra index, digital penetration). Swap this
  for a real dataset (Census / NITI Aayog / data.gov.in) for production use.
  `seed_demo.py` adds ~20 realistic sample complaints so the dashboard isn't
  empty on first run.

## Meeting the track requirements

| Requirement | How this prototype meets it |
|---|---|
| End-to-end flow | Citizen submits (voice/text) → AI classifies → stored → aggregated → shown on policy dashboard |
| Google AI integration | Gemini (`google-generativeai`) does language detection, translation, categorization, urgency/sentiment scoring |
| Real/realistic data | Sample state demographic + infra-index table, plus seedable sample citizen complaints |
| Built for India, scale across states | 16-state sample dataset, state-selector, priority ranking works across any number of states/categories |
| Multilingual / voice support | Hindi/English UI, Gemini handles any input language, Web Speech API voice input in 7 Indian languages |

## Setup

```bash
cd citizen-pulse
python -m venv venv && source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env
# edit .env and add your free Gemini key from https://aistudio.google.com/app/apikey
# (optional — the app works without it, using the fallback classifier)

python app.py          # creates & seeds the state-index table, starts on :5000
python seed_demo.py     # optional: adds ~20 sample complaints for the dashboard
```

Open http://localhost:5000 — submit a complaint on the "Submit Feedback" tab
(try typing or speaking in Hindi), then check the "Policy Dashboard" tab.

## Deploying a live link (for your submission)

The quickest free options that support a Python/Flask backend:

**Render.com** (recommended, free tier):
1. Push this folder to a GitHub repo.
2. On Render: New → Web Service → connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variable `GEMINI_API_KEY` (optional).
6. Deploy — Render gives you a public `https://your-app.onrender.com` link.

**Railway.app**: similar flow — connect repo, it auto-detects Flask, add
`GEMINI_API_KEY` as a variable, deploy.

> Note: this repo doesn't include an already-hosted link — deploying requires
> your own free-tier account on Render/Railway (a couple of minutes), since
> that's where the live URL actually comes from.

## Pushing to GitHub

```bash
git init
git add .
git commit -m "CitizenPulse — Track 1 prototype"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

(`.env` and the SQLite `data/*.db` file are already excluded via `.gitignore`.)

## Extending this prototype

- Swap the priority-score formula for a trained regression/ranking model.
- Add a real map view (Leaflet/Mapbox) using the `lat`/`lng` fields already
  returned by `/api/hotspots`.
- Add WhatsApp/SMS ingestion (e.g. Twilio) alongside the web form for
  citizens without smartphones.
- Replace the sample `state_index` table with a live dataset via API.
