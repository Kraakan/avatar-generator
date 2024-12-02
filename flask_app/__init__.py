import os
import getpass
import flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from celery import Celery
from celery import Task
from flask_celeryext import FlaskCeleryExt
from flask_app.celery_utils import make_celery, init_celery

# create and configure the app
basedir = os.path.abspath(os.path.dirname(__file__))

app = flask.Flask(__name__, instance_relative_config=True)

login = LoginManager(app)
login.login_view = 'login'

# ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    print("Didn't makedir")
    pass

app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(basedir, 'app.db'),
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0"),
)

db = SQLAlchemy(app)

ext_celery = FlaskCeleryExt(create_celery_app=make_celery)
ext_celery.init_app(app)
"""
celery = Celery(
    __name__,
    broker="redis://127.0.0.1:6379/0",
    backend="redis://127.0.0.1:6379/0"
)
"""
celery = ext_celery.celery
#init_celery(app, celery) TODO: Remove function if useless

#app.config.from_pyfile('config.py', silent=True)

@app.shell_context_processor
def ctx():
    return {"app": app, "db": db}

from flask_app import routes, models, tasks