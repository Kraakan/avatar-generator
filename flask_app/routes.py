import os
import flask
from flask_login import current_user, login_user, logout_user, login_required
import flask_app
from flask_app import app, db
from flask_app.forms import LoginForm, RegistrationForm, TuningImageForm
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa
from werkzeug.utils import secure_filename
from werkzeug.datastructures import CombinedMultiDict
from urllib.parse import urlsplit

import datetime

import DreamBooth
from image_generation import img_gen

@app.route('/index')
def index():
    
    return flask.render_template('index.html', title='Home')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return flask.redirect(flask.url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(flask_app.models.User).where(flask_app.models.User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flask.flash('Invalid username or password')
            return flask.redirect(flask.url_for('login'))
        login_user(user, remember=form.remember_me.data)
        flask.flash('Logged in successfully.')
        next_page = flask.request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = flask.url_for('index')
        return flask.redirect(next_page)
    return flask.render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return flask.redirect(flask.url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return flask.redirect(flask.url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = flask_app.models.User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flask.flash('Congratulations, you are now a registered user!')
        return flask.redirect(flask.url_for('login'))
    return flask.render_template('register.html', title='Register', form=form)

@app.route('/user')
@login_required
# Show models and images
def user():
    user = db.session.scalar(sa.select(flask_app.models.User).where(flask_app.models.User.id == current_user.get_id()))
    models = db.session.scalars(sa.select(flask_app.models.Model).where(flask_app.models.Model.user_id == current_user.get_id()))
    tuning_images = db.session.scalars(sa.select(flask_app.models.Tuning_image).where(flask_app.models.Tuning_image.user_id == current_user.get_id()))
    generated_images = db.session.scalars(sa.select(flask_app.models.Generated_image).where(flask_app.models.Generated_image.user_id == current_user.get_id()))
    return flask.render_template('user.html', user=user, models=models, tuning_images=tuning_images, generated_images=generated_images)

@app.route('/user/generate', methods=['POST'])
@login_required
def generate():
    return flask.request.form
"""
async def generate(model):
    initial_image = flask.request.args.get('initimg')
    await img_gen.initialize_pipe()
    img_gen.select_image(initial_image, image_folder="static/users/" + username)
    image_name = await img_gen.flask_generate()
    return "<img src='flask_app/" + {{flask.Flask.url_for('static', filename= "users/" + username + "/output/" + image_name) }}""" + "'>"

@app.route('/user/train', methods=['GET'])
@login_required
async def train():
    from DreamBooth.accelerate_dreambooth import get_config, launch_training
    user = current_user.get_id()
    namespace = get_config(user)
    await launch_training(namespace)
    return "Training run?"

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = TuningImageForm(CombinedMultiDict((flask.request.files, flask.request.form)))
    basedir = os.path.abspath(os.path.dirname(__file__))
    if form.validate_on_submit():
        for f in form.photos.data:  # form.photo.data return a list of FileStorage object
            filename = secure_filename(f.filename)
            extension = '.' + filename.split('.')[1]
            tuning_image = flask_app.models.Tuning_image(user_id=current_user.id, filename=str(datetime.datetime.now()) + extension)
            print(tuning_image.filename)
            f.save(os.path.join(
                basedir, 'static', tuning_image.filename
            ))
            db.session.add(tuning_image)
            db.session.commit()
        return flask.redirect(flask.url_for('index'))

    return flask.render_template('upload.html', form=form)