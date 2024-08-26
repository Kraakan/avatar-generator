import os
import getpass

from flask import Flask
from flask import request

import DreamBooth
from image_generation import img_gen

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    username = "kraakan"

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        print('Hello, world!')
        
        return 'Hi ' + username

    @app.route('/kraakan')
    async def kraakan():
        return await img_gen.initialize_pipe()

    @app.route('/<username>')
    def menu(username):
        return img_gen.display_images(username)

    @app.route('/<username>/generate')
    async def generate(username):
        initial_image = request.args.get('initimg')
        await img_gen.initialize_pipe()
        img_gen.select_image(initial_image, image_folder="static/users/" + username)
        image_name = await img_gen.flask_generate()
        return "<img src='flask_app/" + {{Flask.url_for('static', filename= "users/" + username + "/output/" + image_name) }} + "'>"
    
    @app.route('/<username>/train')
    async def train(username):
        from DreamBooth.accelerate_dreambooth import get_config, launch_training
        namespace = get_config(username)
        await launch_training(namespace)
        return "Training run?"
    
    return app

