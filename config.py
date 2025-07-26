# config.py

import os
from dotenv import load_dotenv
load_dotenv() # memuat variabel dari file .env (untuk development lokal)

    

class Config:
    # Pengaturan Flask
    SESSION_COOKIE_NAME = 'session'

    # Pengaturan Database MySQL
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'default_secret_key'
    HOST = os.environ.get('DB_HOST')
    DATABASE = os.environ.get('DB_NAME')
    USER = os.environ.get('DB_USER')
    PASSWORD = os.environ.get('DB_PASSWORD')

    # Pengaturan lainnya (misalnya untuk email atau lainnya)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    @staticmethod
    def init_app(app):
        pass
