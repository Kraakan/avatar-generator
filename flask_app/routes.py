import flask
from flask_login import current_user, login_user, logout_user, login_required
import flask_app
from flask_app import app, db
from flask_app.forms import LoginForm, RegistrationForm
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa

import DreamBooth
from image_generation import img_gen

@app.route('/index')
def index():
    print('Hello, world!')
    
    return flask.render_template('index.html', title='Home')

@app.route('/kraakan')
async def kraakan():
    return await img_gen.initialize_pipe()

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
        if not next_page or flask.urlsplit(next_page).netloc != '':
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

@app.route('/<username>')
@login_required
def menu(username):
    return img_gen.display_images(username)

@app.route('/<username>/generate')
@login_required
async def generate(username):
    initial_image = flask.request.args.get('initimg')
    await img_gen.initialize_pipe()
    img_gen.select_image(initial_image, image_folder="static/users/" + username)
    image_name = await img_gen.flask_generate()
    return "<img src='flask_app/" + {{flask.Flask.url_for('static', filename= "users/" + username + "/output/" + image_name) }} + "'>"

@app.route('/<username>/images')
@login_required
def images(username):
    return "Show images for " + username
    
@app.route('/<username>/models')
@login_required
def models(username):
    return "Show models for " + username

@app.route('/<username>/train')
@login_required
async def train(username):
    from DreamBooth.accelerate_dreambooth import get_config, launch_training
    namespace = get_config(username)
    await launch_training(namespace)
    return "Training run?"