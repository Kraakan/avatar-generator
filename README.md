# avatar-generator
In-house app for creating user avatars using Stable Diffusion

# Installation guide (Only for linux!)

## Clone repository
`git clone https://github.com/Kraakan/avatar-generator`

## Create python env (recommended!)
`cd avatar-generator`  
`python3 -m venv env`  
`source env/bin/activate`  

## Install dependencies
`pip install -r requirements.txt`  

## Create direcrory for base image generateion model
`cd DreamBooth`  
`mkdir models`  
`cd models`  

## Download base model
`wget https://huggingface.co/botp/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors`

## If you downloaded a .safetensors file:
`cd ..`  
`python3 save_model.py --safetensors_file="./models/v1-5-pruned-emaonly.safetensors" --output_dir="./models/v1-5-pruned-emaonly"`
`cd ..`  

## To run (make sure you are in the avatar-generator directory)
`flask –app flask_app run`  

## To serve the app over local network
`flask --app flask_app run --host=0.0.0.0`
