import fitz  # PyMuPDF - old name
from PIL import Image


def pdf_to_high_quality_jpeg(pdf_path, jpeg_path, zoom=2):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)
    
    # Check if the PDF has at least one page
    if pdf_document.page_count < 1:
        print("The PDF file is empty or does not have any pages.")
        return
    
    # Get the first page
    page = pdf_document.load_page(0)  # Page number starts from 0
    
    # Increase resolution by setting the zoom factor
    mat = fitz.Matrix(zoom, zoom)
    
    # Render the page to an image with the increased resolution
    pix = page.get_pixmap(matrix=mat)
    
    # Convert the image to PIL format
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    # Save the image as JPEG
    img.save(jpeg_path, "JPEG", quality=100)


def pdf_to_jpeg(pdf_path, jpeg_path, zoom=2):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)
    
    # Check if the PDF has at least one page
    if pdf_document.page_count < 1:
        print("The PDF file is empty or does not have any pages.")
        return
    
    # Get the first page
    page = pdf_document.load_page(0)  # Page number starts from 0
    
    # Render the page to an image
    pix = page.get_pixmap()
    
    # Convert the image to PIL format
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    # Save the image as JPEG
    img.save(jpeg_path, "JPEG", quality=100)

# Example usage
pdf_path = "example.pdf"  # Path to your one-page PDF file
jpeg_path = "output.jpeg"  # Path where the JPEG image will be saved
# pdf_to_jpeg(pdf_path, jpeg_path)
pdf_to_high_quality_jpeg(pdf_path, jpeg_path, zoom=4)
