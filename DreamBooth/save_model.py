import argparse
import os
from diffusers import DiffusionPipeline, StableDiffusionPipeline

def main(args):
    model = None
    lora = None
    if args.lora:
        lora = args.lora

    if args.pretrained_model_name_or_path:
        model = DiffusionPipeline.from_pretrained(args.pretrained_model_name_or_path)
    elif args.safetensors_file:
        model = StableDiffusionPipeline.from_single_file(args.safetensors_file)
    
    if model:
        if lora:
            print("Adding lora weights...")
            model.load_lora_weights(args.lora,
            adapter_name=args.lora_name)
        print("Saving...")
        #cwd = os.getcwd()
        model.save_pretrained(os.path.abspath(args.output_dir))

def parse_args(input_args=None):
    parser = argparse.ArgumentParser(description="Simple example model to save.")
    parser.add_argument(
        "--pretrained_model_name_or_path",
        type=str,
        default=None,
        help="Path to pretrained model or model identifier from huggingface.co/models.",
    )
    parser.add_argument(
        "--safetensors_file",
        type=str,
        default=None,
        help="Path to .safetensors file.",
    )
    parser.add_argument(
        "--lora",
        type=str,
        default=None,
        help="lora weights identifier",
    )
    parser.add_argument(
        "--lora_name",
        type=str,
        default="lora",
        help="lora weights identifier",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="new-model",
        help="The output directory where the model will be written.",
    )
    if input_args is not None:
        args = parser.parse_args(input_args)
    else:
        args = parser.parse_args()
    
    return args

if __name__ == "__main__":
    args = parse_args()
    main(args)