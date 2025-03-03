# https://huggingface.co/docs/diffusers/en/api/pipelines/stable_diffusion/img2img

import requests

import torch

from PIL import Image

from io import BytesIO

from diffusers import StableDiffusionImg2ImgPipeline

import datetime

import asyncio

import os
from os import listdir
from os.path import isfile, join

import flask
import argparse

# model_id_or_path = "runwayml/stable-diffusion-v1-5"

# Slotting in DreamBooth output
DreamBooth_instance_prompt="kraakan"
model_id_or_path = "./DreamBooth/kraakan_modell"

def main(args):
    pipe = initialize_pipe(args.pretrained_model_name_or_path) #TODO: Move code here!

    input_dir = os.path.join(os.getcwd(), "../avatar-generator/flask_app/static/")
    dir_content = os.listdir(input_dir)
    if 'input' not in dir_content:
        # create input dir
        os.mkdir('input')
    if 'output' not in dir_content:
        # create input dir
        os.mkdir('output')

    init_image = Image.open(input_dir + args.input_image).convert("RGB")
    init_image = init_image.resize((512, 512))

    images = pipe(prompt=args.prompt, image=init_image, strength=0.75, guidance_scale=7.5).images

    
    image_name = args.output_image
    images[0].save("flask_app/static/output/" + image_name)
    print("Image saved at flask_app/static/output/" + image_name)

def initialize_pipe(model_id_or_path = "./DreamBooth/models/default"):
    device = "cuda"
    pipe = StableDiffusionImg2ImgPipeline.from_pretrained(model_id_or_path, torch_dtype=torch.float16, safety_checker = None)
    pipe = pipe.to(device)
    return pipe
    
def display_images(username):
    image_folder = "flask_app/static/users/" + username
    initial_images = [f for f in listdir(image_folder) if isfile(join(image_folder, f))]
    html = ''
    for imagename in initial_images:
        image_path = image_folder + "/" + imagename
        html += "<a href='" + username + "/generate?initimg=" + imagename + "'><img src='" + flask.url_for('static', filename= username + '/' +imagename) + "'></a>"
    return html

def select_image(initial_image, image_folder):

    
    global initial_image_name

    initial_image_name = initial_image.split(".")[0]

    global init_image

    image_path = "flask_app/" + image_folder + "/" + initial_image

    image_path = 'Nathan_Explosion.png' # TODO: init image selection

    init_image = Image.open(image_path).convert("RGB")

    init_image = init_image.resize((768, 512))


def flask_generate(model_selection = -1, initial_image_name = "Nathan_Explosion.png", prompt = "kraakan person"):
    from flask_app import app, db, models
    import sqlalchemy as sa
    model = db.session.scalar(sa.select(models.Model).where(models.Model.id == model_selection))
    prompt = model.fine_tuning_prompt + " " + prompt
    model_path = model.dir or None
    pipe = initialize_pipe(model_id_or_path = model_path)
    input_dir = os.path.join(os.getcwd(), "../avatar-generator/flask_app/static/input/")

    init_image = Image.open(input_dir + initial_image_name).convert("RGB")
    init_image = init_image.resize((768, 512))

    images = pipe(prompt=prompt, image=init_image, strength=0.75, guidance_scale=7.5).images

    initial_image_name = initial_image_name.split(".")[0]
    image_name ='_'.join(str(datetime.datetime.now()).split()) + "_" + '_'.join(prompt.split()) + "_" + initial_image_name + ".png"
    images[0].save("flask_app/static/output/" + image_name) #Not saving?

    #print("Entry:", "user_id =", model.user_id, "model_id =", model.id, "promt =", prompt, "filename =", image_name)
    new_image_entry = models.Generated_image(user_id = model.user_id, model_id = model.id, prompt = prompt, filename = image_name)
    print(new_image_entry)
    db.session.add(new_image_entry)
    db.session.commit()
    
    return image_name

def enter_prompt(): #TODO: Fix or remove
    prompt = DreamBooth_instance_prompt + " " + input("Enter prompt: ")

    images = pipe(prompt=prompt, image=init_image, strength=0.75, guidance_scale=7.5).images

    print(len(images), "images generated.")

    if len(images) > 1:
        while True:
            selection = input("Select image to show. ")
            try:
                selected = images[int(selection)]
                selected.show()
                while True:
                    action = input("Save image? y/n/q: ")
                    if action == 'n' or 'N':
                        break
                    if action == 'y' or 'Y':
                        selected.save("output/" + prompt + str(datetime.datetime.now()) + ".png")
                        break
                    if action == 'n' or 'N':
                        break
                break
            except ValueError:
                print("Enter a number to select: ")
            except IndexError:
                print("Index out of range ")
    else:
        images[0].save("static/output/" + str(datetime.datetime.now()) + "_" + prompt + "_" + initial_image_name + ".png")

def parse_args(input_args=None): # TODO: Parse the args!
    parser = argparse.ArgumentParser(description="Stablediffusion img-to-img pipeline, modified for use with Arcada avatar generator app.")
    parser.add_argument(
        "--pretrained_model_name_or_path",
        type=str,
        default=None,
        required=True,
        help="Path to pretrained model or model identifier from huggingface.co/models.",
    )
    parser.add_argument(
        "--input_image",
        type=str,
        default=None,
        required=True,
        help="Path to input image for img-to-img pipeline.",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        required=True,
        help="Prompt for image-to-image pipeline.",
    )
    parser.add_argument(
        "--output_image",
        type=str,
        default=None,
        required=True,
        help="Path to new image file.",
    )
    if input_args is not None:
        args = parser.parse_args(input_args)
    else:
        args = parser.parse_args()
    return args

def get_command(model_path, input_image, prompt, output_image):
    command = ["python3", "image_generation/img_gen.py", "--pretrained_model_name_or_path=" + model_path, "--input_image=" + 
               input_image, "--prompt=" + prompt, "--output_image=" + output_image]
    return command

if __name__ == "__main__": # This will be ran from the queue with subprocess.Popen()
    args = parse_args()
    main(args)