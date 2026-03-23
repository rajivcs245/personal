import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key")
    DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_USER = os.getenv("DATABASE_USER", "root")
    DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "personal_service")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "static/uploads")
