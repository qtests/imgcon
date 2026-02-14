from PIL import Image
import os

def webp_to_jpg(input_path, output_path=None, quality=100):

    if output_path is None:
        output_path = input_path.rsplit('.', 1)[0] + '.jpg'  # Change extension to .jpg

    # Open the WEBP image
    img = Image.open(input_path).convert("RGB")  # JPG doesn't support alpha

    # Save as JPG
    img.save(output_path, "JPEG", quality=quality)

# Usage
if __name__ == "__main__":
    path = "Fairy_Creature.webp"
    folder = "/Users/vidas/video/kids"
    path = os.path.join(folder, path)
    webp_to_jpg(path)
