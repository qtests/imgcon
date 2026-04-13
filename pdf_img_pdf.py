import fitz  # PyMuPDF
from PIL import Image
import os


import fitz  # PyMuPDF
from PIL import Image
import os

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


def pdf_to_image_pdf(pdf_path, output_folder, final_pdf_path, zoom=2, reso=100.0):
    """
    Full pipeline:
    1. PDF → JPEGs
    2. JPEGs → Image-only PDF
    """
    os.makedirs(output_folder, exist_ok=True)
    jpeg_paths = pdf_to_jpegs(pdf_path, output_folder, zoom=zoom)
    # jpeg_paths = pdf_to_pngs(pdf_path, output_folder)
    jpegs_to_pdf(jpeg_paths, final_pdf_path, reso=reso)
    print(f"Done! Saved image-based PDF to: {final_pdf_path}")


pdf_to_image_pdf(
    pdf_path="input.pdf",
    output_folder="temp_jpegs",
    final_pdf_path="output_image_only.pdf",
    zoom=2,
    reso=100.0
)
