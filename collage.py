import os
import requests
import io
import math
from PIL import Image

def open_image(path):
    """Opens an image from a local file path or a web URL."""
    if path.startswith(("http://", "https://")):
        try:
            response = requests.get(path, stream=True)
            response.raise_for_status()
            image_data = io.BytesIO(response.content)
            return Image.open(image_data)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching image from URL {path}: {e}")
            return None
    else:
        try:
            return Image.open(path)
        except FileNotFoundError:
            print(f"Warning: Image file not found at local path: {path}")
            return None
    return None

# --- NEW FUNCTION: crop_to_square ---
def crop_to_square(img, gravity=0.5):
    """
    Crops an image to a square by cutting from the larger dimension.

    Args:
        img (PIL.Image.Image): The input image object.
        gravity (float, optional): The "center of gravity" for the crop,
                                   as a percentage (0.0 to 1.0) from the top or left.
                                   0.0 = top/left, 0.5 = center, 1.0 = bottom/right.
                                   Defaults to 0.5 (center).

    Returns:
        PIL.Image.Image: The cropped square image.
    """
    if not isinstance(img, Image.Image):
        return None

    width, height = img.size
    if width == height:
        return img  # Image is already square

    # Determine the smaller dimension, which will be the size of the square
    min_dim = min(width, height)
    
    # Ensure gravity is within the valid range [0.0, 1.0]
    gravity = max(0.0, min(1.0, gravity))

    if width > height:
        # Landscape image: crop the width
        crop_width = min_dim
        # Calculate how much can be cut from one side
        max_offset = width - crop_width
        # Position the crop based on gravity
        left = int(max_offset * gravity)
        right = left + crop_width
        top, bottom = 0, min_dim
    else:
        # Portrait image: crop the height
        crop_height = min_dim
        max_offset = height - crop_height
        top = int(max_offset * gravity)
        bottom = top + crop_height
        left, right = 0, min_dim

    # Define the crop box and perform the crop
    crop_box = (left, top, right, bottom)
    return img.crop(crop_box)


def create_collage(
    image_paths,
    output_size,
    grid_cols,
    grid_rows,
    frame_spacing=10,
    col_spacing=10,
    row_spacing=10,
    bg_color="white",
    crop_images_to_square=False, # New: Toggle for square cropping
    crop_gravity=0.5,            # New: Gravity for the crop
    output_filename="collage.jpg",
):
    """
    Creates a high-quality collage with detailed spacing and cropping controls.
    """
    if not image_paths:
        print("Error: No image paths provided.")
        return

    output_width, output_height = output_size
    collage_image = Image.new("RGB", output_size, bg_color)

    # Cell calculation logic (unchanged from previous version)
    total_col_spacing = (grid_cols - 1) * col_spacing
    total_row_spacing = (grid_rows - 1) * row_spacing
    available_width = output_width - (2 * frame_spacing) - total_col_spacing
    available_height = output_height - (2 * frame_spacing) - total_row_spacing
    cell_width = available_width // grid_cols
    cell_height = available_height // grid_rows
    cell_size = (cell_width, cell_height)

    # As we now crop to a square, the cell size for the thumbnail should also be a square
    # to avoid distortion. We take the smaller of the two cell dimensions.
    if crop_images_to_square:
        thumb_size_val = min(cell_width, cell_height)
        cell_size = (thumb_size_val, thumb_size_val)

    # Grid centering logic (unchanged)
    total_grid_width = (grid_cols * cell_width) + total_col_spacing
    total_grid_height = (grid_rows * cell_height) + total_row_spacing
    grid_origin_x = (output_width - total_grid_width) // 2
    grid_origin_y = (output_height - total_grid_height) // 2
    
    image_index = 0
    for row in range(grid_rows):
        for col in range(grid_cols):
            if image_index < len(image_paths):
                cell_origin_x = grid_origin_x + col * (cell_width + col_spacing)
                cell_origin_y = grid_origin_y + row * (cell_height + row_spacing)

                img = open_image(image_paths[image_index])
                if img:
                    # --- MODIFICATION: Apply square crop if requested ---
                    if crop_images_to_square:
                        img = crop_to_square(img, gravity=crop_gravity)
                        if not img: continue # Skip if cropping failed
                    # --- End of modification ---

                    img.thumbnail(cell_size, Image.Resampling.LANCZOS)
                    
                    paste_x = cell_origin_x + (cell_width - img.width) // 2
                    paste_y = cell_origin_y + (cell_height - img.height) // 2
                    
                    collage_image.paste(img, (paste_x, paste_y))
                image_index += 1

    try:
        collage_image.save(output_filename, "JPEG", quality=95)
        print(f"Collage saved successfully as {output_filename}")
    except Exception as e:
        print(f"Failed to save collage: {e}")


# --- NEW HELPER FUNCTION: calc_grid ---
def calc_grid(n):
    """
    Calculates the best grid (x*x or x*(x+2)) for n items.
    """
    if n < 1:
        return None
    min_error = float('inf')
    result = {}
    limit = int(math.sqrt(n)) + 2
    for x in range(1, limit):
        sq_error = n - (x * x)
        if sq_error >= 0 and sq_error < min_error:
            min_error = sq_error
            result = {'error': sq_error, 'equation': 'SQ', 'x': x, 'grid': (x, x)}
        sq2_error = n - (x * (x + 2))
        if sq2_error >= 0 and sq2_error < min_error:
            min_error = sq2_error
            result = {'error': sq2_error, 'equation': 'SQ2', 'x': x, 'grid': (x, x + 2)}
    return result


# --- NEW WRAPPER FUNCTION ---
def create_auto_grid_collage(image_paths, output_size, **kwargs):
    """
    Automatically determines the best grid for the number of images
    and then calls create_collage.
    """
    n = len(image_paths)
    if n == 0:
        print("No images to create a collage from.")
        return

    grid_info = calc_grid(n)
    if not grid_info:
        print(f"Could not calculate a grid for {n} images.")
        return
    
    print(f"For {n} images, best grid found: {grid_info['grid']} (from equation {grid_info['equation']}) with {grid_info['error']} empty cells.")

    rows, cols = grid_info['grid']
    
    # Smart orientation: if output is landscape, prefer more columns.
    output_width, output_height = output_size
    if output_width > output_height and rows > cols:
        rows, cols = cols, rows # Swap to make it wider
    # If output is portrait, prefer more rows.
    elif output_height > output_width and cols > rows:
        rows, cols = cols, rows # Swap to make it taller
        
    create_collage(
        image_paths=image_paths,
        output_size=output_size,
        grid_cols=cols,
        grid_rows=rows,
        **kwargs # Pass all other keyword arguments through
    )



if __name__ == "__main__":
    image_sources = [
        "https://images.pexels.com/photos/3778680/pexels-photo-3778680.jpeg", # Portrait
        "https://images.pexels.com/photos/376464/pexels-photo-376464.jpeg",    # Landscape
        "image1.jpg",
        "https://images.pexels.com/photos/1036623/pexels-photo-1036623.jpeg", # Portrait
        "https://images.pexels.com/photos/262978/pexels-photo-262978.jpeg",    # Landscape
        "image2.jpg",
        "https://images.pexels.com/photos/774909/pexels-photo-774909.jpeg",   # Portrait
        "https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg",  # Landscape
        "image3.jpg",
    ]

    # Create dummy image files for testing if they don't exist
    for source in image_sources:
        if not (source.startswith("http") or os.path.exists(source)):
            try:
                img = Image.new('RGB', (600, 800), color='blue')
                img.save(source)
                print(f"Created dummy image: {source}")
            except Exception as e:
                print(f"Could not create dummy image {source}: {e}")    

    # --- Example 1: Center-Cropped Square Images ---
    print("--- Creating collage with center-cropped square images ---")
    create_collage(
        image_paths=image_sources,
        output_size=(1000, 1000),
        grid_cols=3,
        grid_rows=3,
        frame_spacing=20, col_spacing=15, row_spacing=15,
        bg_color="#333",
        crop_images_to_square=True, # <-- Enable cropping
        crop_gravity=0.5,           # <-- Crop from the center (default)
        output_filename="collage_center_cropped.jpg"
    )

    # --- Example 2: Top-Cropped Square Images ---
    # Useful for portraits where the head is at the top of the frame.
    print("\n--- Creating collage with top-cropped square images ---")
    create_collage(
        image_paths=image_sources,
        output_size=(1000, 700),
        grid_cols=3,
        grid_rows=3,
        frame_spacing=20, col_spacing=15, row_spacing=15,
        bg_color="darkslategray",
        crop_images_to_square=True, # <-- Enable cropping
        crop_gravity=0.0,           # <-- Crop from the top/left edge
        output_filename="collage_top_cropped.jpg"
    )

    # --- Example 3: No cropping (original behavior) ---
    print("\n--- Creating collage with original, uncropped images ---")
    create_collage(
        image_paths=image_sources,
        output_size=(1000, 700),
        grid_cols=3,
        grid_rows=3,
        frame_spacing=20, col_spacing=15, row_spacing=15,
        bg_color="maroon",
        crop_images_to_square=False, # <-- Disable cropping
        output_filename="collage_no_crop.jpg"
    )


    # --- Example Usage for calc_grid ---
    print("--- Testing calc_grid function ---")
    print(f"For 8 images: {calc_grid(8)}")
    print(f"For 10 images: {calc_grid(10)}")
    print(f"For 15 images: {calc_grid(15)}")
    print(f"For 24 images: {calc_grid(24)}") # Should be SQ2 with x=4 -> (4,6)

    # --- Example Usage for the new auto-grid collage function ---
    image_sources = [
        "https://images.pexels.com/photos/1036623/pexels-photo-1036623.jpeg",
        "https://images.pexels.com/photos/774909/pexels-photo-774909.jpeg",
        "https://images.pexels.com/photos/1239291/pexels-photo-1239291.jpeg",
        "https://images.pexels.com/photos/415829/pexels-photo-415829.jpeg",
        "https://images.pexels.com/photos/1222271/pexels-photo-1222271.jpeg",
        "https://images.pexels.com/photos/1587009/pexels-photo-1587009.jpeg",
        "https://images.pexels.com/photos/3778680/pexels-photo-3778680.jpeg",
        "https://images.pexels.com/photos/376464/pexels-photo-376464.jpeg",
        "https://images.pexels.com/photos/3778680/pexels-photo-3778680.jpeg", # Portrait
        "https://images.pexels.com/photos/376464/pexels-photo-376464.jpeg",    # Landscape
        "image1.jpg",
        "https://images.pexels.com/photos/1036623/pexels-photo-1036623.jpeg", # Portrait
        "https://images.pexels.com/photos/262978/pexels-photo-262978.jpeg",    # Landscape
        "image2.jpg",
        "https://images.pexels.com/photos/774909/pexels-photo-774909.jpeg",   # Portrait
        "https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg",  # Landscape
        "image3.jpg",        
    ] # 8 images

    print("\n--- Creating auto-grid collage (8 images) on a landscape canvas ---")
    create_auto_grid_collage(
        image_paths=image_sources,
        output_size=(1200, 800), # Landscape canvas
        frame_spacing=20,
        col_spacing=10,
        row_spacing=10,
        bg_color="white",
        crop_images_to_square = False,
        output_filename="collage_auto_8_images_landscape.jpg"
    )
    
    print("\n--- Creating auto-grid collage (8 images) on a portrait canvas ---")
    create_auto_grid_collage(
        image_paths=image_sources,
        output_size=(800, 1200), # Portrait canvas
        frame_spacing=20,
        col_spacing=10,
        row_spacing=10,
        bg_color="black",
        crop_images_to_square=True, # Also test with cropping
        output_filename="collage_auto_8_images_portrait.jpg"
    )    