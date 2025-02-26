import os
import flask
from flask_login import current_user, login_user, logout_user, login_required
import flask_app
from flask_app import app, db, models, queue
from flask_app.forms import LoginForm, RegistrationForm, TuningImageForm, ImageGenerationForm, TuningForm, TaskForm
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa
from werkzeug.utils import secure_filename
from werkzeug.datastructures import CombinedMultiDict
from urllib.parse import urlsplit

import datetime
import time
import threading

from image_generation import img_gen

# svg conversion
from cairosvg import svg2png

global app_status
app_status = "Pending"

def enter_model(app, user, new_model_dir, prompt = "Placeholder prompt", name="Placeholder Name"):
    new_model_entry = models.Model(name=name, dir=new_model_dir, user_id=user, fine_tuning_promt=prompt)
    db.session.add(new_model_entry)
    db.session.commit()
    queue.running = None
    print(new_model_dir, "entered")

def enter_image(app, user, path, prompt, model_id):
    new_image_entry = models.Generated_image(user_id = user, model_id = model_id, promt = prompt, filename = path)
    db.session.add(new_image_entry)
    db.session.commit()
    queue.running = None
    print(path, "entered")

def check_process(app = app, delay=30):
    global app_status
    status = queue.poll_process()
    if status == 0:
        app_status = "Pending"
        with app.app_context():
            #print(status)
            # Make database entry!
            task_type, task_key, user, path, prompt, name_or_model_id = queue.get_task_entry(queue.running)
            if task_type == "model tuning":
                enter_model(app, user, path,  prompt = prompt, name = name_or_model_id)
            if task_type == "image generation":
                enter_image(app, user, path, prompt, name_or_model_id)
    elif status == None:
        app_status = "Busy"
        print(status)
        time.sleep(delay)
        check_process(delay=delay)
    elif status < 0: # TODO: Stop looping on negative returncode
        app_status = "Crashed"
        queue.crash()

@app.route('/')
def index():
    return flask.render_template('index.html', title='Home', status = app_status)

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
    return flask.render_template('login.html', title='Sign In', form=form, status = app_status)

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
    flask.session['prev'] = flask.url_for('user')
    user = db.session.scalar(sa.select(flask_app.models.User).where(flask_app.models.User.id == current_user.get_id()))
    models = db.session.scalars(sa.select(flask_app.models.Model).where(flask_app.models.Model.user_id == current_user.get_id()).order_by(-flask_app.models.Model.id))
    tuning_images = db.session.scalars(sa.select(flask_app.models.Tuning_image).where(flask_app.models.Tuning_image.user_id == current_user.get_id()).order_by(-flask_app.models.Tuning_image.id))
    generated_images = db.session.scalars(sa.select(flask_app.models.Generated_image).where(flask_app.models.Generated_image.user_id == current_user.get_id()).order_by(-flask_app.models.Generated_image.id))
    print(tuning_images)
    return flask.render_template('user.html', user=user, models=models, tuning_images=tuning_images, generated_images=generated_images, status = app_status)

@app.route('/user/generate', methods=['GET','POST']) # Send task to queue, then load a task monitor page
@login_required
async def generate():
    # List models
    # Base model + user generated
    #model_list = [(-1, "Base model")] # Allow generation with untuned model?
    model_list = []
    user_id = current_user.get_id()
    user_models = db.session.scalars(sa.select(flask_app.models.Model).where(flask_app.models.Model.user_id == int(user_id)).order_by(-flask_app.models.Model.id))
    #all_user_models = db.session.query(flask_app.models.Model)
    #print(type(all_user_models.all()[0].user_id), type(user_id))
    #print(all_user_models.all()[0].user_id == int(user_id))
    model_list += [(m.id, m.name) for m in user_models]
    print(model_list)
    form = ImageGenerationForm()
    form.models.choices = model_list
    input_images = os.listdir('flask_app/static/input')
    i = 0
    while i < len(input_images):
        input_images[i] = "/input/" + input_images[i]
        i = i + 1
    print(input_images)
    tuning_images = db.session.scalars(sa.select(flask_app.models.Tuning_image).where(flask_app.models.Tuning_image.user_id == current_user.get_id()).order_by(-flask_app.models.Tuning_image.id))
    form.input_images.choices = input_images + list(tuning_images)
    if form.validate_on_submit():
        #need user?
        print(current_user)
        model_selection = int(form.models.data)
        model = db.session.scalar(sa.select(models.Model).where(models.Model.id == model_selection))
        model_path = model.dir
        username = db.session.scalar(sa.select(flask_app.models.User).where(flask_app.models.User.id == user_id)).username
        prompt = username + " " + form.promt.data
        initial_image = form.input_images.data
        #initial_image = "Nathan_Explosion.png" # TODO: Let user chose something
        split_image_name = initial_image.split(".")
        extension = split_image_name[-1]
        initial_image_name = ".".join(split_image_name[:-1])    
        if len(initial_image_name.split("/")) > 1:
            initial_image_name = initial_image_name.split("/")[-1]
        if extension == "svg": #Convert svg to png
            svg = open("flask_app/static/input/" + initial_image, "r").read()
            png_image_name = initial_image_name +'.png'
            svg2png(bytestring=svg,write_to='flask_app/static/input/' + png_image_name)
            initial_image = png_image_name
        new_image_name ='_'.join(str(datetime.datetime.now()).split()) + "_" + '_'.join(prompt.split()) + "_" + initial_image_name + ".png"
        command = img_gen.get_command(model_path, initial_image, prompt, new_image_name)
        if model_selection != -1:
            task = queue.queue_task(user_id, "image generation", new_image_name, prompt=prompt, command=command, model_id=model_selection)
            # TODO: Don't start process checker unless task is actually launched.
            if task[1] == "launching":
                process_checking_thread = threading.Thread(name="process checker", target=check_process, kwargs = {"delay": 5})
                process_checking_thread.start()
        else: # Allow generation with untuned model?
            pass
        return flask.render_template('tasks.html', queue = queue.q, highlight = task, status = app_status)
    return flask.render_template('generate.html', form=form, status = app_status)

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
        print(selected_images)
        image_filenames = [i.filename for i in selected_images]
        print(image_filenames)
        import DreamBooth.accelerate_dreambooth as dreambooth
        user = current_user.get_id()
        username = db.session.scalar(sa.select(flask_app.models.User).where(flask_app.models.User.id == user)).username
        dir_list = os.listdir('models')
        new_i = 0
        for d in dir_list:
            d_i = int(d.split('_')[0])
            if d_i >= new_i:
                new_i = d_i + 1
        print(new_i)
        new_model_dir = "./models/" + str(new_i) # This caused an error: (sqlite3.IntegrityError) UNIQUE constraint failed: model.dir
        new_model_dir = new_model_dir + "_" + username
        command = dreambooth.get_command(user, image_filenames, new_model_dir, prompt=username)
        task = queue.queue_task(user, "model tuning", new_model_dir, prompt=username, name=name, command = command)
        # TODO: Don't start process checker unless task is actually launched.
        if task[1] == "launching":
            process_checking_thread = threading.Thread(name="process checker", target=check_process, kwargs = {"delay": 15})
            process_checking_thread.start()
        return flask.render_template('tasks.html', queue =  queue.q, highlight = task, status = app_status)
    return flask.render_template('tune.html', form=form, status = app_status)

@app.route('/user/tasks', methods=['GET', 'POST'])
@login_required
def tasks(): # TODO: Create reverse-chronological list of tasks (including pending ones?)
    if queue.running != None:
        process_status = queue.poll_process()
        print(process_status)
    form = TaskForm()
    result = flask.request.form
    print(result)
    message = None
    if 'run' in result.keys():
            print("Run", result['run'])
            message = queue.promote_task(result['run'])
            print(message)
            if message[1] == "launching":
                process_checking_thread = threading.Thread(name="process checker", target=check_process, kwargs = {"delay": 15})
                process_checking_thread.start()
                return flask.render_template('tasks.html', queue =  queue.q, form=form, highlight = result['run'])
    if 'cancel' in result.keys():
            message = queue.remove_task(result['cancel'])
            print("Cancel", result['cancel'])
    return flask.render_template('tasks.html', queue = queue.q, form=form, message = message, status = app_status)

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
        return flask.render_template('upload.html', form=form, message = "Upload successful")

    return flask.render_template('upload.html', form=form, message = None)

@app.route('/delete', methods=['POST'])
@login_required
def delete():
    data = flask.request.get_data(as_text=True)
    data = data.split('=')[1]
    img_type, id = data.split('_')
    print(img_type, id)
    if img_type == "generated":
        img_to_del = db.session.scalar(sa.select(flask_app.models.Generated_image).where(flask_app.models.Generated_image.id == id))
        if img_to_del.user_id == current_user.id:
            db.session.delete(img_to_del)
            db.session.commit()
    if img_type == "tuning":
        img_to_del = db.session.scalar(sa.select(flask_app.models.Tuning_image).where(flask_app.models.Tuning_image.id == id))
        if img_to_del.user_id == current_user.id:
            db.session.delete(img_to_del)
            db.session.commit()
    return flask.redirect(flask.session['prev'])

@app.get("/status")
def status(): # Have attempted to get shell output from subprocess, so far unsuccessfully
    """a_status = queue.get_output()
    print(isinstance(a_status, str))
    print(type(a_status))
    if hasattr(a_status, '__iter__') and not isinstance(a_status, str):
        print("ITERATING!")
        for line in a_status:
            print(type(line))
            yield {"status" : line}"""
    return {"status" : app_status}

@app.get("/result/<id>")
def result(id):
    return id