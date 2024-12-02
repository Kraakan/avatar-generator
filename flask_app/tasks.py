from celery import shared_task
from flask_app import app, db, models

@shared_task
def generate(model_selection, prompt):
    with app.app_context():
        from image_generation import img_gen
        img_gen.flask_generate(model_selection = model_selection, prompt = prompt)
        # Make database entry when finished

@shared_task
def tune(user, image_filenames, new_model_dir, username):
    from DreamBooth.accelerate_dreambooth import get_config, launch_training
    namespace = get_config(user, image_filenames, new_model_dir, prompt=username)
    launch_training(namespace, user, new_model_dir, prompt=username)
    # Make database entry when finished

@shared_task
def hello():
    return 'Herllo!'