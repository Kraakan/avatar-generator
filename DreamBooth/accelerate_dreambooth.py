from accelerate.commands import launch
import argparse
import json
import os
import subprocess

# TODO: pass arguments

def create_config(user):
    pass

def get_command(user, image_list, new_model_dir, prompt = None, model_name = None):
    image_string = '#'.join(image_list)
    dir_path = "/users/"
    print(dir_path + user + '.json') # TODO: Do users actually need individual settings?
    print(os.path.dirname(__file__))
    try:
        with open(os.path.dirname(__file__) + dir_path + user + '.json') as f: # TODO: add correct file structure
            launch_args = json.load(f)      # (it might be different depending on server)
    except FileNotFoundError:
        print(FileNotFoundError)
        launch_args = create_config(user)

    launch_args["instance_image_list"] = image_string
    launch_args["output_dir"]= new_model_dir

    if prompt is not None:
        launch_args["instance_prompt"] = prompt

    # model_name = "runwayml/stable-diffusion-v1-5" # "pretrained_model_name_or_path":$MODEL_NAME,
    # instance_dir = "./kraakan" # "instance_data_dir":$INSTANCE_DIR,
    # output_dir = "./kraakan_modell"
    # instance_prompt = "kraakan" # "instance_prompt":"kraakan",

    # How do I set environment variables from here?
    # PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32
    # CUDA_VISIBLE_DEVICES=0

    # Also, arguments vithout values:
    # "gradient_checkpointing, "use_8bit_adam"


    parser = launch.launch_command_parser()


    arg_list = ["DreamBooth/train_dreambooth.py"]
    #arg_list = []

    default_args = vars(parser.parse_args(args = arg_list))

    for key, item in launch_args.items():
        if key not in default_args:
            parser.add_argument("--" + key)
        if isinstance(item, str):
            arg_list.append("--" + key + "=" + item)
        else:
            arg_list.append("--" + key)

    #namespace = parser.parse_args(args = arg_list) # Old launch method
    command = ["python3", "-m", "accelerate.commands.launch"]
    command = command + arg_list

    return command

def launch_training(namespace, user, new_model_dir, prompt = "Placeholder prompt", name="Placeholder Name"):
    # Old launch method
    #launch.launch_command(namespace)
    command = ["python3", "-m", "accelerate.commands.launch"]
    #args = ' '.join(namespace)
    command = command + namespace
    print(command)
    #subprocess.run("ls")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, universal_newlines=True)

    from flask_app import queue

    queue.track_process(process)

    # On successful training, return data for the database
    # Comment above suggests this will wait for subprocesses to complete, I hope that's not true...
    model_data = {
        "instance_prompt": prompt,
        "output_dir": new_model_dir
    }
    from flask_app import app, db, models
    new_model_entry = models.Model(name=name, dir=new_model_dir, user_id=user, fine_tuning_promt=prompt)
    db.session.add(new_model_entry)
    db.session.commit()
    return model_data
