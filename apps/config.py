"""Configuration settings module for the Task Management API.

Loads environment variables from `.env` file using python-dotenv and exports
database connection URLs and JWT security parameters.
"""

from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "secret-key-fallback-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "525600"))

# Brevo (Bravo) Email Configuration
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "noreply@taskmanagement.com")
SENDER_NAME = os.getenv("SENDER_NAME", "Task Management API")