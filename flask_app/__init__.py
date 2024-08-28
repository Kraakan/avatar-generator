import os
import getpass
import flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy



# create and configure the app
basedir = os.path.abspath(os.path.dirname(__file__))

app = flask.Flask(__name__, instance_relative_config=True)

login = LoginManager(app)
login.login_view = 'login'

# ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(basedir, 'app.db'),
)

db = SQLAlchemy(app)

#app.config.from_pyfile('config.py', silent=True)

from flask_app import routes, models


