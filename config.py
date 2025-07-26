# config.py

import os

class Config:
    # Pengaturan Flask
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'your_secret_key'
    SESSION_COOKIE_NAME = 'session'

    # Pengaturan Database MySQL
    HOST = 'localhost'
    DATABASE = 'pengaduan_db'
    USER = 'postgres'  # Sesuaikan dengan username MySQL Anda
    PASSWORD = 'postgres'  # Sesuaikan dengan password MySQL Anda

    # Pengaturan lainnya (misalnya untuk email atau lainnya)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    @staticmethod
    def init_app(app):
        pass
