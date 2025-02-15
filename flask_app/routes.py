import os
import flask
from flask_login import current_user, login_user, logout_user, login_required
import flask_app
from flask_app import app, db, models, queue
from flask_app.forms import LoginForm, RegistrationForm, TuningImageForm, ImageGenerationForm, TuningForm
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa
from werkzeug.utils import secure_filename
from werkzeug.datastructures import CombinedMultiDict
from urllib.parse import urlsplit

import datetime
import time
import threading

import DreamBooth
from image_generation import img_gen

def enter_model(user, new_model_dir, prompt = "Placeholder prompt", name="Placeholder Name"):
    new_model_entry = models.Model(name=name, dir=new_model_dir, user_id=user, fine_tuning_promt=prompt)
    db.session.add(new_model_entry)
    db.session.commit()

class result_object():  # TODO: Make actual result handling
    def __init__(self):
        self.ready = "yes"
        self.successful = False

def check_process(delay=30):
    status = queue.poll_process()
    if status != 0:
        #print(status)
        time.sleep(delay)
        check_process()
    else:
        #print(status)
        # Make database entry!
        task_type, task_key, user, new_model_dir, prompt, name = queue.task_entry(queue.running)
        enter_model(user, new_model_dir, prompt, name)

@app.route('/')
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
        # TODO: Generate .json file in ../DreamBoorth/users 
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

@app.route('/user/generate', methods=['GET','POST']) # Send task to celery, then load a task monitor page
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
        result = result_object() # TODO: Make actual result handling
        model_selection = int(form.models.data)
        prompt = form.promt.data
        if model_selection != -1:
            img_gen.flask_generate(model_selection = model_selection, prompt = prompt) # TODO: Consider lanching a subprocess for this!
            print(prompt)
        else: # Allow generation with untuned model?
            pass
        if queue.busy:
            queue.add({"model" : model_selection,
                       "prompt" : prompt})
            print("Busy flag read!")
        return flask.render_template('tasks.html', queue = queue.q)
    return flask.render_template('generate.html', form=form)

@app.route('/user/tune', methods=['GET', 'POST']) # Launch tuning, then load a task monitor page
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
        name = form.name.data
        image_id_strings = [str(i) for i in form.tuning_images.data]
        selected_images = db.session.query(flask_app.models.Tuning_image).filter(flask_app.models.Tuning_image.id.in_(image_id_strings)).all()
        #scalars(sa.select(flask_app.models.Tuning_image).where( flask_app.models.Tuning_image.id in image_id_strings))
        print(selected_images)
        image_filenames = [i.filename for i in selected_images]
        print(image_filenames)
        from DreamBooth.accelerate_dreambooth import get_command, launch_training
        user = current_user.get_id()
        username = db.session.scalar(sa.select(flask_app.models.User).where(flask_app.models.User.id == user)).username
        all_models = db.session.query(flask_app.models.Model).all()
        new_model_dir = "./models/" + str(len(all_models))
        #result = flask_app.tasks.tune.apply_async(user, image_filenames, new_model_dir, username)
        command = get_command(user, image_filenames, new_model_dir, prompt=username)
        queue.queue_task(user, "model tuning", new_model_dir, prompt=username, name=name, command = command)
        #model_data = launch_training(namespace, user, new_model_dir, prompt=username, name = name) # Old code!

        # Trying to make a polling system to update the database once tuning is finished
        process_checking_thread = threading.Thread(name="process checker", target=check_process)
        process_checking_thread.start()
        return flask.render_template('tasks.html', queue =  queue.q)
    return flask.render_template('tune.html', form=form)

@app.route('/user/tasks', methods=['GET'])
@login_required
def tasks(): # TODO: Create reverse-chronological list of tasks (including pending ones?)
    process_status = queue.poll_process()
    print(process_status)
    return flask.render_template('tasks.html', queue = queue.q)

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

@app.get("/result/<id>")
def result(id):
    return id