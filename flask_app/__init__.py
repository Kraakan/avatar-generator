import os
import getpass
import flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_app import task_queue
import json

#TODO: On startup, check DreamBooth/models dir and DreamBooth/settings.json
model_dirs = os.listdir('DreamBooth/models')
settings_file = open("DreamBooth/settings.json", "r")
settings = json.load(settings_file)
default_model_path = settings["pretrained_model_name_or_path"]
settings_file.close()
default_model = default_model_path.split("/")[-1]
if default_model not in model_dirs:
    if len(model_dirs) > 0:
        model_selection = None
        while model_selection == None:
            print("Default model", default_model, "not found, use one of the ones listed below?")
            for i, m in enumerate(model_dirs):
                print(i, m)
            model_selection = int(input("Enter the index of the model you would like to use as a base."))
            if model_selection < len(model_dirs):
                print(model_dirs[model_selection])
                if input("Use this model? y/n ") == 'y':
                    new_default_model = model_dirs[model_selection]
                else: model_selection = None
            else: model_selection = None
        new_default_model_path = "/".join("DreamBooth/models".split("/") + [new_default_model])
        print(new_default_model_path)
        settings["pretrained_model_name_or_path"] = new_default_model_path
        settings_file = open("DreamBooth/settings.json", "w")
        json.dump(settings, settings_file, indent=4)
        settings_file.close()
    else:
        print("No folders found in DreamBooth/models. Please donload a base model and extract any .safetensor files before running the app.")


# create and configure the app
basedir = os.path.abspath(os.path.dirname(__file__))

app = flask.Flask(__name__, instance_relative_config=True)


login = LoginManager(app)
login.login_view = 'login'

# ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    #print("Didn't makedir")
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