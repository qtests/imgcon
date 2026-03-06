import os
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json
import pandas as pd


# Upsacaling
# https://github.com/JingyunLiang/SwinIR   -> pip install swinir
# Faces                                    -> pip install gfpgan
# 
# 2024 https://github.com/wyf0912/SinSR
# 2024 https://github.com/3587jjh/PCSR


# --- ImageTool remains the same ---
class ImageTool:
    """
    Handles image generation and loading.
    In a real scenario, this would interface with an actual image generation API.
    """
    def __init__(self, project_folder: Path, image_subfolder: str = "img"):
        self.project_folder = project_folder
        self.image_subfolder_name = image_subfolder 
        
        self.project_folder.mkdir(parents=True, exist_ok=True)
        
        self.image_subfolder_path = self.project_folder / self.image_subfolder_name
        self.image_subfolder_path.mkdir(parents=True, exist_ok=True)

    def _image_path(self, name: str):
        """
        Builds a full path for an image file inside the designated image subfolder.
        """
        return self.image_subfolder_path / f"{name}.png"

    def generate_image(self, prompt: str, context_images=None, f_name: str = None):
        """
        Generates an image and saves it to the designated image subfolder.
        This version ensures proper versioning (`_vX`) even on subsequent regenerations.
        """
        print(f"Generating image for prompt: {prompt[:50]} into subfolder '{self.image_subfolder_name}'...")
        
        if f_name is None:
            safe_name = prompt[:30].replace(" ", "_").replace("/", "_")
            base_f_name = f"img_{safe_name}"
        else:
            base_f_name_without_ext = os.path.splitext(f_name)[0]
            if "_v" in base_f_name_without_ext:
                base_f_name = base_f_name_without_ext.rsplit("_v", 1)[0]
            else:
                base_f_name = base_f_name_without_ext
        
        current_version_num = 0
        versioned_f_name = ""
        while True:
            candidate_f_name = f"{base_f_name}_v{current_version_num}"
            candidate_path = self._image_path(candidate_f_name)
            if not candidate_path.exists():
                versioned_f_name = candidate_f_name
                break
            current_version_num += 1

        save_path = self._image_path(versioned_f_name)

        try:
            if "v2" in str(save_path):
                image_data = Image.new('RGB', (800, 600), color='blue')
            elif "v1" in str(save_path):
                image_data = Image.new('RGB', (800, 600), color='green')
            else:
                image_data = Image.new('RGB', (800, 600), color='gray') 
            
            image_data.save(save_path)
            print(f"Image saved to {save_path}")
            return save_path
        except Exception as e:
            print(f"Could not create image at {save_path}: {e}")
            return None

    @staticmethod
    def load_and_scale(img_path: Path, page_w, page_h, frac_w=0.4, frac_h=0.25):
        if not img_path or not img_path.exists():
            print(f"Image not found or path is None: {img_path}")
            return None

        img = Image.open(img_path).convert("RGB")
        target_max_w = int(page_w * frac_w)
        target_max_h = int(page_h * frac_h)

        img_aspect = img.width / img.height
        target_aspect = target_max_w / target_max_h

        if img_aspect > target_aspect:
            new_w = target_max_w
            new_h = int(target_max_w / img_aspect)
        else:
            new_h = target_max_h
            new_w = int(target_max_h * img_aspect)
        
        img = img.resize((new_w, new_h), Image.LANCZOS)
        return img


# --- PDFGenerator Class with 4 shots per page logic ---
class PDFGenerator:
    """
    Handles the generation of PDF documents from storyboard data.
    """
    def __init__(self, project_folder: Path):
        self.project_folder = project_folder
        
        # PDF Layout constants - these are now specific to the PDF generation
        self.base_dpi = 150
        self.a4_width_inch = 8.27
        self.a4_height_inch = 11.69
        self.margin_x_factor = 50 # pixels at base_dpi
        self.margin_y_factor = 50
        self.right_col_x_factor = 0.50 # as fraction of page width (for text description)
        self.title_font_size_factor = 18
        self.body_font_size_factor = 14
        self.img_frac_w = 0.45 # Max fractional width for images
        self.spacing_between_frames_factor = 15 # Reduced spacing for more shots
        self.spacing_between_shots_factor = 30 # Reduced spacing between shots for 4/page

    def _get_font(self, size_factor, scale):
        """Helper to load a font with fallbacks."""
        try:
            font_path = "arial.ttf"
            if not os.path.exists(font_path):
                windows_font_path = Path("C:/Windows/Fonts/arial.ttf")
                if windows_font_path.exists():
                    font_path = str(windows_font_path)
                else:
                    print("Warning: Arial font not found. Using default PIL font.")
                    return ImageFont.load_default()
            
            return ImageFont.truetype(font_path, int(size_factor * scale))
        except Exception as e:
            print(f"Error loading font: {e}. Using default PIL font.")
            return ImageFont.load_default()

    def _wrap_text(self, text: str, font, max_width: int):
        """
        Wraps text to fit within a maximum width.
        """
        if not text:
            return [""]
        lines = []
        words = text.split(' ')
        current_line_words = []
        
        # Create a dummy Draw object for text measurement
        dummy_img = Image.new('RGB', (1, 1)) 
        draw = ImageDraw.Draw(dummy_img)

        for word in words:
            test_line = ' '.join(current_line_words + [word])
            # Check the width of the potential new line
            if draw.textbbox((0, 0), test_line, font=font)[2] <= max_width:
                current_line_words.append(word)
            else:
                if current_line_words: 
                    lines.append(' '.join(current_line_words))
                current_line_words = [word] # Start a new line with the current word
                
                # Handle cases where a single word is longer than max_width
                if draw.textbbox((0,0), word, font=font)[2] > max_width:
                    lines.append(word) # Put the long word on its own line
                    current_line_words = [] # Reset for next word
        
        if current_line_words:
            lines.append(' '.join(current_line_words))
        
        return lines


    def generate_pdf(self, storyboard_data: list, output_filename: str = "storyboard.pdf", dpi: int = 150, shots_per_page: int = 2):
        """
        Generates a PDF from the provided storyboard data.
        
        Args:
            storyboard_data (list): List of storyboard shot dictionaries.
            output_filename (str): The name of the PDF file to save.
            dpi (int): Dots per inch for the PDF resolution.
            shots_per_page (int): Number of shots to display on each page (1, 2, or 4).
        """
        if not storyboard_data:
            print("No storyboard data provided to generate PDF.")
            return

        if shots_per_page not in [1, 2, 4]: # Added 4 as a valid option
            print("Warning: shots_per_page must be 1, 2 or 4. Defaulting to 2.")
            shots_per_page = 2

        output_path = self.project_folder / output_filename
        scale = dpi / self.base_dpi

        a4_width = int(self.a4_width_inch * self.base_dpi * scale)
        a4_height = int(self.a4_height_inch * self.base_dpi * scale)

        margin_x = int(self.margin_x_factor * scale)
        right_col_x = int(a4_width * self.right_col_x_factor)
        margin_y = int(self.margin_y_factor * scale)
        
        text_column_width = a4_width - right_col_x - margin_x 

        # --- Dynamic calculation for img_frac_h based on shots_per_page ---
        # Assuming only 'first_frame' is present, adjust calculations
        if shots_per_page == 1:
            # For 1 shot, more height is available for the image and text
            # Title + 3 lines of body text (estimated)
            estimated_text_height = (1 * self.title_font_size_factor * scale) + (self.body_font_size_factor * scale * 3) 
            # Total vertical space minus margins, text height, and inter-frame spacing
            available_img_space_h = a4_height - (2 * margin_y) - estimated_text_height - int(self.spacing_between_frames_factor * scale)
            img_frac_h = available_img_space_h / a4_height
            img_frac_h = max(img_frac_h, 0.40) # Larger image for single shot
        elif shots_per_page == 2:
            # For 2 shots, divide vertical space between them
            estimated_text_height_per_shot = (1 * self.title_font_size_factor * scale) + (self.body_font_size_factor * scale * 3)
            total_estimated_text_height = estimated_text_height_per_shot * 2
            # Subtract margins and spacing between shots and frames
            available_img_space_h = a4_height - (2 * margin_y) - total_estimated_text_height - (self.spacing_between_shots_factor * scale) - (2 * int(self.spacing_between_frames_factor * scale))
            img_frac_h = (available_img_space_h / 2) / a4_height # Divide by 2 as there are 2 images per page
            img_frac_h = max(img_frac_h, 0.20)
        elif shots_per_page == 4:
            # For 4 shots, divide vertical space into quarters
            estimated_text_height_per_shot = (1 * self.title_font_size_factor * scale) + (self.body_font_size_factor * scale * 2) # Less text space
            total_estimated_text_height = estimated_text_height_per_shot * 4
            # Subtract margins and spacing between shots and frames
            available_img_space_h = a4_height - (2 * margin_y) - total_estimated_text_height - (3 * self.spacing_between_shots_factor * scale) - (4 * int(self.spacing_between_frames_factor * scale))
            img_frac_h = (available_img_space_h / 4) / a4_height # Divide by 4 as there are 4 images per page
            img_frac_h = max(img_frac_h, 0.10) # Smallest image size
        # -------------------------------------------------------------------

        font_title = self._get_font(self.title_font_size_factor, scale)
        font_body = self._get_font(self.body_font_size_factor, scale)

        pages = []
        current_page_shots = []

        for entry in storyboard_data:
            current_page_shots.append(entry)

            if len(current_page_shots) == shots_per_page or entry == storyboard_data[-1]:
                page = Image.new("RGB", (a4_width, a4_height), "white")
                draw = ImageDraw.Draw(page)
                
                current_y_offset = margin_y

                for shot_idx, shot_entry in enumerate(current_page_shots):
                    shot_num = shot_entry["shot_number"]
                    title = shot_entry["shot_title"]
                    desc1 = shot_entry["description_f1"] # Only using first frame description
                    frames = shot_entry["keyframes"]

                    draw.text(
                        (margin_x, current_y_offset),
                        f"Shot {shot_num}: {title}",
                        fill="black",
                        font=font_title
                    )
                    title_bbox = draw.textbbox((0,0), f"Shot {shot_num}: {title}", font=font_title)
                    current_y_offset += title_bbox[3] + int(5 * scale) # Reduced spacing after title

                    # ImageTool.load_and_scale is a static method
                    img1_path = Path(frames["first_frame"]) if frames["first_frame"] else None
                    img1 = ImageTool.load_and_scale(img1_path, a4_width, a4_height, frac_w=self.img_frac_w, frac_h=img_frac_h)
                    
                    # --- First frame and its description with text wrapping ---
                    # The prompt for desc1 is now just "Description:"
                    wrapped_desc1 = self._wrap_text(desc1, font_body, text_column_width)
                    desc1_text_to_draw = "Description:\n" + "\n".join(wrapped_desc1) # Adjusted label
                    desc1_text_height = draw.textbbox((0,0), desc1_text_to_draw, font=font_body)[3]

                    if img1:
                        page.paste(img1, (margin_x, current_y_offset))
                        draw.text(
                            (right_col_x, current_y_offset),
                            desc1_text_to_draw,
                            fill="black",
                            font=font_body
                        )
                        current_y_offset += max(img1.height, desc1_text_height) + int(self.spacing_between_frames_factor * scale)
                    else:
                        draw.text(
                            (right_col_x, current_y_offset),
                            desc1_text_to_draw,
                            fill="black",
                            font=font_body
                        )
                        current_y_offset += max(int(a4_height * img_frac_h), desc1_text_height) + int(self.spacing_between_frames_factor * scale)

                    # Add spacing between shots if not the last shot on the page
                    if shot_idx < shots_per_page - 1:
                        current_y_offset += int(self.spacing_between_shots_factor * scale)

                pages.append(page)
                current_page_shots = []

        if pages:
            pages[0].save(output_path, save_all=True, append_images=pages[1:])
            print(f"Storyboard PDF saved to {output_path} at {dpi} DPI")


# --- StoryboardManager (modified) ---
class StoryboardManager:
    """
    Manages the creation, saving, loading, and updating of storyboard data.
    """
    def __init__(self, project_folder: str = "StoryboardProject", image_subfolder: str = "images"):
        self.project_folder = Path(project_folder)
        self.project_folder.mkdir(parents=True, exist_ok=True)
        self.image_gen = ImageTool(self.project_folder, image_subfolder=image_subfolder)
        self.storyboard_data = [] # Stores the actual storyboard data (list of dicts)
        self.storyboard_file = self.project_folder / "storyboard_data.json" # Default JSON file path

    def create_storyboard(self, shots: list, character_descriptions: str, save_to_file: bool = True):
        """
        Generates a storyboard consisting of first and last frames for each shot.
        
        Args:
            shots (list): A list of dictionaries containing shot descriptions.
            character_descriptions (str): Detailed traits to ensure consistency.
            save_to_file (bool): If True, the storyboard data will be saved to a JSON file.
        Returns:
            list: The generated storyboard data.
        """
        self.storyboard_data = [] # Reset for new creation
        for i, shot in enumerate(shots):
            shot_n = i + 1
            shot_title = shot['title']
            print(f"--- Processing Shot {shot_n}: {shot_title} ---")
            
            fr1_description = shot['description_1']
            first_frame_prompt = (
                f"First frame of the shot: {fr1_description}. "
                f"Visual Style: Cinematic. Characters involved: {character_descriptions}"
            )
            first_frame_path = self.image_gen.generate_image(first_frame_prompt, f_name=f"Shot{shot_n}_FR1") 

            fr2_description = shot.get('description_2')
            last_frame_path = None
            if fr2_description:
                last_frame_prompt = (
                    f"Last frame of the shot: {fr2_description}. "
                    f"Ensure visual continuity with the first frame. Characters: {character_descriptions}"
                )
                last_frame_path = self.image_gen.generate_image(last_frame_prompt, context_images=[first_frame_path], f_name=f"Shot{shot_n}_FR2")
            
            self.storyboard_data.append({
                "shot_number": shot_n,
                "shot_title": shot_title,
                "description_f1": fr1_description,
                "description_f2": fr2_description,
                "keyframes": {
                    "first_frame": first_frame_path,
                    "last_frame": last_frame_path
                },
                "fixed": False,
            })

        if save_to_file:
            self.save_storyboard()
        
        return self.storyboard_data

    def save_storyboard(self):
        """
        Saves the current storyboard data to a JSON file.
        Paths within storyboard_data are converted to strings for JSON serialization.
        """
        serializable_data = []
        for shot in self.storyboard_data:
            serializable_shot = shot.copy()
            if serializable_shot['keyframes']['first_frame']:
                serializable_shot['keyframes']['first_frame'] = str(serializable_shot['keyframes']['first_frame'])
            if serializable_shot['keyframes']['last_frame']:
                serializable_shot['keyframes']['last_frame'] = str(serializable_shot['keyframes']['last_frame'])
            serializable_data.append(serializable_shot)

        try:
            with open(self.storyboard_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=4)
            print(f"Storyboard data saved to {self.storyboard_file}")
            return True
        except Exception as e:
            print(f"Error saving storyboard data to {self.storyboard_file}: {e}")
            return False

    def load_storyboard(self):
        """
        Loads storyboard data from the JSON file into the manager's storyboard_data attribute.
        Paths are converted back to Path objects after loading.
        """
        try:
            with open(self.storyboard_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            for shot in loaded_data:
                if 'fixed' not in shot:
                    shot['fixed'] = False
                
                if shot['keyframes']['first_frame']:
                    shot['keyframes']['first_frame'] = Path(shot['keyframes']['first_frame'])
                if shot['keyframes']['last_frame']:
                    shot['keyframes']['last_frame'] = Path(shot['keyframes']['last_frame'])
            
            self.storyboard_data = loaded_data
            print(f"Storyboard data loaded from {self.storyboard_file}")
            return self.storyboard_data
        except FileNotFoundError:
            print(f"No storyboard data found at {self.storyboard_file}")
            self.storyboard_data = []
            return None
        except Exception as e:
            print(f"Error loading storyboard data from {self.storyboard_file}: {e}")
            self.storyboard_data = []
            return None

    def update_storyboard(self, character_descriptions: str, save_to_file: bool = True):
        """
        Loads the existing storyboard data and regenerates images for shots
        that are not marked as "fixed".
        
        Args:
            character_descriptions (str): Detailed traits to ensure consistency
                                          for regenerated images.
            save_to_file (bool): If True, the updated storyboard data will be
                                 saved back to the JSON file.
        Returns:
            list: The updated storyboard data.
        """
        if not self.load_storyboard():
            print("Cannot update storyboard: No existing storyboard data found to load.")
            return []

        print("--- Updating Storyboard (regenerating non-fixed shots) ---")
        updated_shots_count = 0
        for i, shot in enumerate(self.storyboard_data):
            if not shot.get("fixed", False):
                print(f"  Regenerating Shot {shot['shot_number']}: {shot['shot_title']}")
                updated_shots_count += 1

                fr1_description = shot['description_f1']
                first_frame_prompt = (
                    f"First frame of the shot: {fr1_description}. "
                    f"Visual Style: Cinematic. Characters involved: {character_descriptions}"
                )
                new_first_frame_path = self.image_gen.generate_image(first_frame_prompt, f_name=f"Shot{shot['shot_number']}_FR1")
                shot['keyframes']['first_frame'] = new_first_frame_path

                fr2_description = shot.get('description_f2')
                if fr2_description:
                    last_frame_prompt = (
                        f"Last frame of the shot: {fr2_description}. "
                        f"Ensure visual continuity with the first frame. Characters: {character_descriptions}"
                    )
                    new_last_frame_path = self.image_gen.generate_image(last_frame_prompt, context_images=[new_first_frame_path], f_name=f"Shot{shot['shot_number']}_FR2")
                    shot['keyframes']['last_frame'] = new_last_frame_path
                else:
                    shot['keyframes']['last_frame'] = None

            else:
                print(f"  Skipping fixed Shot {shot['shot_number']}: {shot['shot_title']}")
        
        if updated_shots_count == 0:
            print("No non-fixed shots found to regenerate.")

        if save_to_file:
            self.save_storyboard()
        
        return self.storyboard_data


# --- Example Usage ---
if __name__ == '__main__':

    story_shots_initial = [
        {"title": "The Discovery",   "description_1": "A capybara enters a dark jungle.", "description_2": None},
        {"title": "The Encounter",   "description_1": "The capybara meets a wise old owl.", "description_2": "The capybara shares the banana with the owl."},
        {"title": "The Dance 1",     "description_1": "The capybara dances happily with the golden banana."},
        {"title": "The Dance 2",     "description_1": "The capybara dances happily with the golden banana."},
        {"title": "The Dance 3",     "description_1": "The capybara dances happily with the golden banana."}
    ]
    chars_common = "A friendly capybara with a small red hat."

    project_folder_name = "Video_Prod1"
    custom_image_subfolder = "shot_keyframes"
    
    # Initialize the StoryboardManager
    manager = StoryboardManager(project_folder=project_folder_name, image_subfolder=custom_image_subfolder)
    # Initialize the PDFGenerator, passing the same project_folder
    pdf_gen = PDFGenerator(project_folder=Path(project_folder_name)) # PDFGenerator needs Path object

    # --- 1. Create a new storyboard ---
    print("\n--- 1. Creating New Storyboard ---")
    manager.create_storyboard(story_shots_initial, chars_common, save_to_file=True)
    # Now call generate_pdf from the pdf_gen instance, passing the storyboard_data from manager
    pdf_gen.generate_pdf(manager.storyboard_data, output_filename="initial_storyboard_2_per_page.pdf", dpi=300, shots_per_page=2)

    # Manually 'fix' one shot for demonstration
    if manager.storyboard_data:
        manager.storyboard_data[0]['fixed'] = True
        print(f"\n--- Manually marked Shot 1 as fixed ---")
        manager.save_storyboard()

    # --- 2. Update the storyboard (regenerates non-fixed shots) ---
    print("\n--- 2. Updating Storyboard (regenerating non-fixed shots) ---")
    manager.update_storyboard(chars_common, save_to_file=True)
    # Generate PDFs after the update
    pdf_gen.generate_pdf(manager.storyboard_data, output_filename="updated_storyboard_2_per_page.pdf", dpi=300, shots_per_page=2)
    pdf_gen.generate_pdf(manager.storyboard_data, output_filename="updated_storyboard_1_per_page.pdf", dpi=300, shots_per_page=1)
    
    # Verify which shots were updated
    print("\n--- Final Storyboard Data After Update ---")
    for shot in manager.storyboard_data:
        status = "FIXED" if shot.get("fixed", False) else "NOT FIXED (REGENERATED)"
        print(f"Shot {shot['shot_number']}: {shot['shot_title']} - {status}")
        print(f"  First Frame: {shot['keyframes']['first_frame']}")
        print(f"  Last Frame: {shot['keyframes']['last_frame']}")
        
    print("\nStoryboard update demonstration complete!")