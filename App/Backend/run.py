"""
Wrapper to ensure .env is loaded before importing main:app.
"""
from dotenv import load_dotenv
load_dotenv()

# Now import the app - database.py also calls load_dotenv() but it's idempotent
from main import app
