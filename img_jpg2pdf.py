from PIL import Image

def jpeg_to_pdf(jpeg_path, pdf_path):
    # Open the JPEG image
    img = Image.open(jpeg_path)
    
    # Convert the image to RGB (in case it's a different mode)
    img = img.convert("RGB")
    
    # Save the image as a PDF
    img.save(pdf_path, "PDF", resolution=100.0)

# Example usage
jpeg_path = "output.jpeg"  # Path to your JPEG file
pdf_path = "edited_example.pdf"  # Path where the PDF file will be saved
jpeg_to_pdf(jpeg_path, pdf_path)

