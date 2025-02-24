import os
import getpass
import flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_app import task_queue

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
)

app.jinja_env.globals.update(reversed=reversed) # Not crucial, but it's nice to have newer stuff on top of the page

db = SQLAlchemy(app)
#init_celery(app, celery) TODO: Remove function if useless

#app.config.from_pyfile('config.py', silent=True)

# Object that will handle task queue
queue = task_queue.queue()

@app.shell_context_processor
def ctx():
    return {"app": app, "db": db, "queue": queue}

from flask_app import routes, models