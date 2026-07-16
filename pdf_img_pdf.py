import fitz  # PyMuPDF fitz
from PIL import Image
import os

import shutil
import glob


def stack_images_side_by_side(image_paths, output_folder="stacked_output"):
    """
    Takes a list of image paths and stacks them in pairs:
    (1+2), (3+4), etc.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    stacked_paths =[]
    
    # Iterate through the list in steps of 2
    for i in range(0, len(image_paths), 2):
        # Load the images
        img1 = Image.open(image_paths[i])
        
        # Check if there is a second image, if not, use a blank image or just img1
        if i + 1 < len(image_paths):
            img2 = Image.open(image_paths[i+1])
        else:
            img2 = Image.new('RGB', img1.size, (255, 255, 255)) # White blank
        
        # Calculate dimensions for the new image
        new_width = img1.width + img2.width
        new_height = max(img1.height, img2.height)
        
        # Create a new blank image
        combined_img = Image.new('RGB', (new_width, new_height), (255, 255, 255))
        
        # Paste images
        combined_img.paste(img1, (0, 0))
        combined_img.paste(img2, (img1.width, 0))
        
        # Save the result
        output_path = os.path.join(output_folder, f"stacked_page_{ (i//2) + 1 }.png")
        combined_img.save(output_path, "PNG")
        stacked_paths.append(output_path)
        
    return stacked_paths


def pdf_to_pngs(pdf_path, output_folder):
    """
    Converts all pages of a PDF into high-quality 300 DPI PNG images.
    Returns a list of PNG file paths.
    """
    pdf = fitz.open(pdf_path)
    png_paths = []

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 300 DPI render matrix
    my_dpi = 150
    mat = fitz.Matrix(my_dpi/72, my_dpi/72)

    for page_num in range(pdf.page_count):
        page = pdf.load_page(page_num)
        pix = page.get_pixmap(matrix=mat)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        png_path = os.path.join(output_folder, f"page_{page_num + 1}.png")
        img.save(png_path, "PNG", quality=100)

        png_paths.append(png_path)

    return png_paths


def pdf_to_jpegs(pdf_path, output_folder, zoom=2, forma='PNG'):
    """
    Converts all pages of a PDF into high-quality JPEGs.
    Returns a list of JPEG file paths.
    """
    pdf = fitz.open(pdf_path)
    jpeg_paths = []

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for page_num in range(pdf.page_count):
        page = pdf.load_page(page_num)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        if forma == "JPEG":
            jpeg_path = os.path.join(output_folder, f"page_{page_num + 1}.jpg")
            img.save(jpeg_path, "JPEG", quality=100)
        else:
            jpeg_path = os.path.join(output_folder, f"page_{page_num + 1}.png")
            compressed_image = img.quantize(colors=256)
            compressed_image.save(jpeg_path, "PNG", compress_level=9, optimize=True)            

        jpeg_paths.append(jpeg_path)

    return jpeg_paths


def jpegs_to_pdf(jpeg_paths, output_pdf_path, reso = 100.0):
    """
    Combines JPEG images into a single PDF.
    """

    jpeg_paths = sorted(
        jpeg_paths,
        key=lambda p: int(os.path.splitext(os.path.basename(p))[0].split("_")[1])
    )
    images = [Image.open(p).convert("RGB") for p in jpeg_paths]

    # Save first image, append the rest
    images[0].save(
        output_pdf_path,
        format="PDF",
        save_all=True,
        append_images=images[1:],
        resolution=reso
    )


def pdf_to_image_pdf(pdf_path, output_folder, final_pdf_path, zoom=2, reso=100.0, first_step = True):
    """
    Full pipeline:
    1. PDF → JPEGs
    2. JPEGs → Image-only PDF
    """
    os.makedirs(output_folder, exist_ok=True)
    if first_step:
        jpeg_paths = pdf_to_jpegs(pdf_path, output_folder, zoom=zoom)
    else:
        jpeg_paths = glob.glob(f"{output_folder}/*.png")
    # jpeg_paths = pdf_to_pngs(pdf_path, output_folder)
    jpegs_to_pdf(jpeg_paths, final_pdf_path, reso=reso)
    print(f"Done! Saved image-based PDF to: {final_pdf_path}")

# --- Example Usage ---
if __name__ == "__main__":

    clean_folder = False
    out_folder = "temp_jpegs"
    result_pdf = "output_image_only.pdf"
    final_pdf_path = os.path.join(out_folder, result_pdf)

    # if clean_folder and os.path.isdir(out_folder):
    #     shutil.rmtree(out_folder)
    #     print(f"Removed directory: {out_folder}")

    pdf_to_image_pdf(
        pdf_path        = os.path.join(out_folder, "Meravi_BusinessCard_MiryungKim_KR_print.pdf"),
        output_folder   = out_folder,
        final_pdf_path  = final_pdf_path,
        zoom            = 4,
        reso            = 100.0,
        first_step      = True
    )

    work_folder = "temp_jpegs"
    pdfs = [
            "Meravi_BusinessCard_MiryungKim_EN_print.pdf",
            "Meravi_BusinessCard_MiryungKim_KR_print.pdf"
        ]

    # merged = fitz.open()
    # for pdf in pdfs:
    #     pdf = os.path.join(work_folder, pdf)
    #     with fitz.open(pdf) as m:
    #         merged.insert_pdf(m)

    # result = os.path.join(work_folder, "merged.pdf")
    # merged.save(result)
    # merged.close()


    print("Finito")
