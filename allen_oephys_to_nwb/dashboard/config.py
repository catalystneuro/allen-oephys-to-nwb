class Config:
    """Base config."""
    # SECRET_KEY = 'SECRET_KEY'
    SESSION_COOKIE_NAME = 'SESSION_COOKIE_NAME'
    STATIC_FOLDER = 'static'
    TEMPLATES_FOLDER = 'templates'
    SEND_FILE_MAX_AGE_DEFAULT = 0


class ConfigDev(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    TESTING = True
    DATABASE_URI = 'DEV_DATABASE_URI'

    DATA_PATH = '/home/vinicius/Área de Trabalho/Trabalhos/allen-to-nwb/files/'