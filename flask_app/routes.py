import os
import flask
from flask_login import current_user, login_user, logout_user, login_required
import flask_app
from flask_app import app, db
from flask_app.forms import LoginForm, RegistrationForm, TuningImageForm, ImageGenerationForm, TuningForm
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

@app.route('/user/generate', methods=['GET','POST'])
@login_required
async def generate():
    # List models
    # Base model + user generated
    model_list = [(-1, "Base model")]
    user_id = current_user.get_id()
    user_models = db.session.scalars(sa.select(flask_app.models.Model).where(flask_app.models.Model.user_id == int(user_id)))
    #all_user_models = db.session.query(flask_app.models.Model)
    #print(type(all_user_models.all()[0].user_id), type(user_id))
    #print(all_user_models.all()[0].user_id == int(user_id))
    model_list += [(m.id, m.name) for m in user_models]
    print(model_list)
    form = ImageGenerationForm()
    form.models.choices = model_list
    if form.validate_on_submit():
        #need user?
        print(current_user)
        model_selection = form.models.data
        prompt = form.promt.data
        if int(model_selection) != -1:
            model = db.session.scalar(sa.select(flask_app.models.Model).where(flask_app.models.Model.id == int(model_selection))) # Assuming the form will have the model id's
            prompt = model.fine_tuning_promt + " " + prompt
            img_gen.flask_generate(model = model, prompt = prompt)
            print(prompt)
        else: # Allow generation with untuned model?
            pass
        return flask.render_template('tasks.html')
    return flask.render_template('generate.html', form=form)

@app.route('/user/tune', methods=['GET', 'POST'])
@login_required
async def tune():
    available_images = db.session.scalars(sa.select(flask_app.models.Tuning_image).where(flask_app.models.Tuning_image.user_id == current_user.get_id()))
    form = TuningForm()
    form.tuning_images.choices = [(i.id, i.filename) for i in available_images]
    if form.tuning_images.data:
        print(form.tuning_images.data)
    else:
        print(form.tuning_images)
        print("What's this?")
    if form.validate_on_submit():
        image_id_strings = [str(i) for i in form.tuning_images.data]
        selected_images = db.session.query(flask_app.models.Tuning_image).filter(flask_app.models.Tuning_image.id.in_(image_id_strings)).all()
        #scalars(sa.select(flask_app.models.Tuning_image).where( flask_app.models.Tuning_image.id in image_id_strings))
        print(selected_images)
        image_filenames = [i.filename for i in selected_images]
        print(image_filenames)
        from DreamBooth.accelerate_dreambooth import get_config, launch_training
        user = current_user.get_id()
        username = db.session.scalar(sa.select(flask_app.models.User).where(flask_app.models.User.id == user)).username
        all_models = db.session.query(flask_app.models.Model).all()
        new_model_dir = "./models/" + str(len(all_models))
        namespace = get_config(user, image_filenames, new_model_dir, prompt=username)
        launch_training(namespace, user, new_model_dir, prompt=username)
        #model_data["dir"] = new_model_dir
        #return model_data
    return flask.render_template('tune.html', form=form)

@app.route('/user/tasks', methods=['GET'])
@login_required
def tasks(): # TODO: Create reverse-chronological list of tasks (including pending ones?)
    return flask.render_template('tasks.html')

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = TuningImageForm(CombinedMultiDict((flask.request.files, flask.request.form)))
    basedir = os.path.abspath(os.path.dirname(__file__))
    if form.validate_on_submit():
        for f in form.photos.data:  # form.photo.data return a list of FileStorage object
            filename = secure_filename(f.filename)
            extension = '.' + filename.split('.')[1] #''.join(sentence.split())
            tuning_image = flask_app.models.Tuning_image(user_id=current_user.id, filename=''.join(str(datetime.datetime.now()).split()) + extension)
            print(tuning_image.filename)
            f.save(os.path.join(
                basedir, 'static', tuning_image.filename
            ))
            db.session.add(tuning_image)
            db.session.commit()
        return flask.redirect(flask.url_for('index'))

    return flask.render_template('upload.html', form=form)