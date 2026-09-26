"""Seed the database with sample citizen feedback across states/categories,
so the dashboard is populated for a demo without needing live submissions
or a Gemini API key.

Run after `python app.py` has been started at least once (to create the DB):
    python seed_demo.py
"""
import os
import random
import sqlite3
from datetime import datetime, timedelta

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "data", "citizenpulse.db")

# (state, district, language, raw_text, translated_text, category, urgency, sentiment)
SAMPLES = [
    ("Uttar Pradesh", "Prayagraj", "hi", "Sadak me bade gaddhe hain, accident ho sakta hai",
     "There are big potholes on the road, an accident could happen", "Roads & Transport", 0.85, "negative"),
    ("Uttar Pradesh", "Gorakhpur", "hi", "Mobile network bahut kamzor hai gaon me",
     "Mobile network is very weak in the village", "Digital Connectivity", 0.55, "negative"),
    ("Bihar", "Gaya", "hi", "3 din se paani nahi aa raha",
     "There has been no water supply for 3 days", "Water Supply", 0.9, "negative"),
    ("Bihar", "Purnia", "hi", "Naali jaam hai, gandagi phail rahi hai",
     "The drain is blocked and filth is spreading", "Sanitation & Waste", 0.75, "negative"),
    ("Maharashtra", "Nagpur", "en", "Frequent power cuts every evening disrupt work",
     "Frequent power cuts every evening disrupt work", "Electricity", 0.7, "negative"),
    ("Maharashtra", "Nashik", "en", "Local bus service is unreliable and overcrowded",
     "Local bus service is unreliable and overcrowded", "Roads & Transport", 0.5, "negative"),
    ("West Bengal", "Malda", "bn", "Gram e internet songjog nei",
     "There is no internet connectivity in the village", "Digital Connectivity", 0.6, "negative"),
    ("Madhya Pradesh", "Rewa", "hi", "Aspatal me doctor nahi hai emergency ke liye",
     "There is no doctor available at the hospital for emergencies", "Healthcare", 0.95, "negative"),
    ("Rajasthan", "Jodhpur", "en", "Garbage has not been collected for two weeks",
     "Garbage has not been collected for two weeks", "Sanitation & Waste", 0.6, "negative"),
    ("Odisha", "Koraput", "en", "School has had no science teacher for a year",
     "School has had no science teacher for a year", "Education", 0.65, "negative"),
    ("Jharkhand", "Ranchi", "hi", "Bijli ka voltage bahut kam hai, machine kaam nahi karti",
     "Electricity voltage is very low, machines don't work", "Electricity", 0.5, "negative"),
    ("Chhattisgarh", "Bastar", "hi", "Gaon tak sadak nahi hai, barish me raasta band ho jata hai",
     "There is no road to the village, the path gets blocked during rains", "Roads & Transport", 0.9, "negative"),
    ("Assam", "Dibrugarh", "en", "Frequent flooding damages local roads every monsoon",
     "Frequent flooding damages local roads every monsoon", "Roads & Transport", 0.8, "negative"),
    ("Assam", "Barpeta", "en", "No functioning primary health centre nearby",
     "No functioning primary health centre nearby", "Healthcare", 0.85, "negative"),
    ("Bihar", "Muzaffarpur", "hi", "Bachchon ke school jaane ka rasta kharab hai",
     "The path for children to go to school is in poor condition", "Roads & Transport", 0.6, "negative"),
    ("Uttar Pradesh", "Kanpur", "hi", "Safai karamchari niyamit nahi aate",
     "Sanitation workers do not come regularly", "Sanitation & Waste", 0.55, "negative"),
    ("West Bengal", "Murshidabad", "bn", "Rasta ta khub kharap, gari cholte pare na",
     "The road is in very bad condition, vehicles can't pass", "Roads & Transport", 0.7, "negative"),
    ("Madhya Pradesh", "Satna", "hi", "Bijli 6 ghante se gayab hai",
     "Electricity has been gone for 6 hours", "Electricity", 0.75, "negative"),
    ("Kerala", "Wayanad", "en", "Landslide-prone road badly needs reinforcement",
     "Landslide-prone road badly needs reinforcement", "Roads & Transport", 0.9, "negative"),
    ("Punjab", "Bathinda", "en", "Groundwater contamination affecting drinking water",
     "Groundwater contamination affecting drinking water", "Water Supply", 0.8, "negative"),
]


def run():
    if not os.path.exists(DB_PATH):
        raise SystemExit("Database not found. Run `python app.py` once first to initialize it.")
    conn = sqlite3.connect(DB_PATH)
    now = datetime.utcnow()
    for state, district, lang, raw, translated, cat, urgency, sentiment in SAMPLES:
        ts = (now - timedelta(days=random.randint(0, 25))).isoformat()
        conn.execute(
            """INSERT INTO feedback
               (state, district, language, raw_text, translated_text, category,
                urgency_score, sentiment, source, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (state, district, lang, raw, translated, cat, urgency, sentiment, "seed", ts),
        )
    conn.commit()
    conn.close()
    print(f"Seeded {len(SAMPLES)} demo feedback entries into {DB_PATH}")


if __name__ == "__main__":
    run()
