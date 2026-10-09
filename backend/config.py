import os

class Config:
    # MySQL Database Configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')   # Change to your MySQL password
    MYSQL_DB = os.environ.get('MYSQL_DB', 'food_db')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))

    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = False

    # MySQL URI for SQLAlchemy (optional reference)
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False