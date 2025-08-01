from PIL import Image, ImageEnhance, ImageFilter

# Open an image
image = Image.open("image.jpg")

# Make the image lighter
enhancer = ImageEnhance.Brightness(image)
lighter_image = enhancer.enhance(0.5)  # Adjust the factor for brightness

# Apply a blur effect
blurred_image = lighter_image.filter(ImageFilter.GaussianBlur(radius=5))  # Radius controls the level of blur

# Save the final image
blurred_image.save("modified_image.jpg")

# Show the image (optional)
blurred_image.show()