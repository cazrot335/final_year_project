from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Profile(db.Model):
    __tablename__ = 'profiles'
    id = db.Column(db.Integer, primary_key=True)
    profile_url = db.Column(db.String(500), unique=True, nullable=False)
    name = db.Column(db.String(150))
    designation = db.Column(db.String(200))
    snippet = db.Column(db.Text)
    is_deep_scraped = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ScrapeLog(db.Model):
    __tablename__ = 'scrape_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    keyword_used = db.Column(db.String(100))
    total_found = db.Column(db.Integer)  # Every link found
    unique_new = db.Column(db.Integer)   # Only those not in DB

class GlobalStats(db.Model):
    __tablename__ = 'global_stats'
    id = db.Column(db.Integer, primary_key=True)
    total_pages_crawled = db.Column(db.Integer, default=0)
    total_api_calls = db.Column(db.Integer, default=0)

class AnalyzedProfile(db.Model):
    __tablename__ = "analyzed_profiles"

    id = db.Column(db.Integer, primary_key=True)
    profile_url = db.Column(db.String(500), unique=True)

    name = db.Column(db.String(150))
    headline = db.Column(db.String(300))

    skills = db.Column(db.Text)
    experience = db.Column(db.Text)
    education = db.Column(db.Text)

    biometric_score = db.Column(db.Integer)

    raw_json = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)    