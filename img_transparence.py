from PIL import Image


# Open the image
# image = Image.open("your_image.jpg").convert("RGBA")  # Convert to RGBA for transparency support

# Create a new image with an alpha layer for transparency
# width, height = image.size
# transparent_layer = Image.new("RGBA", (width, height), (255, 255, 255, 0))  # Completely transparent

# Combine the original image with the transparent layer
# for x in range(width):
    # for y in range(height):
        # r, g, b, a = image.getpixel((x, y))
        # Adjust alpha to add transparency (e.g., reduce to 50%)
        # transparent_layer.putpixel((x, y), (r, g, b, int(a * 0.5)))  # Alpha reduced by 50%

# Save the result
# transparent_layer.save("output_image.png")  # Save as PNG to preserve transparency



# Open the image
image = Image.open("image.jpg").convert("RGBA")

# Add transparency
r, g, b, a = image.split()  # Split into channels
a = a.point(lambda p: p * 0.1)  # Reduce alpha channel to 50% transparency
transparent_image = Image.merge("RGBA", (r, g, b, a))

# Save the result
transparent_image.save("output_image.png")


# Create a white background
white_background = Image.new("RGB", image.size, (255, 255, 255))  # Pure white background

# Paste the original image onto the white background, using alpha channel as mask
white_background.paste(image, mask=transparent_image.split()[3])  # Use the alpha channel as mask

# Save as JPEG (JPEG doesn't support transparency)
white_background.save("output_white_bg_image.jpg", "JPEG")