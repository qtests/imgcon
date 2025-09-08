import cv2
import numpy as np
import os
import time
import random
 
def horizontal_scroll(img, i):
    width = img.shape[1]
    i = i % width
    l = img[:, :i]
    r = img[:, i:]
    return np.hstack((r, l))
 
def vertical_scroll(img, i):
    height = img.shape[0]
    i = i % height
    t = img[:i, :]
    b = img[i:, :]
    return np.vstack((b, t))
 
def rotate_image(img, i):
    angle = i % 360
    center = (img.shape[1] // 2, img.shape[0] // 2)
    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(img, rot_mat, (img.shape[1], img.shape[0]))
 
def zoom_image(img, i):
    zoom_factor = 1 + 0.5 * np.sin(i / 20.0)
    center = (img.shape[1] // 2, img.shape[0] // 2)
    M = cv2.getRotationMatrix2D(center, 0, zoom_factor)
    zoomed = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]))
    return zoomed
 
def fade_image(img, i):
    alpha = 0.5 + 0.5 * np.sin(i / 20.0)
    faded = cv2.convertScaleAbs(img, alpha=alpha)
    return faded
 
def get_image_files(directory):
    supported_exts = ['.jpg', '.jpeg', '.png', '.bmp']
    return [f for f in os.listdir(directory)
            if os.path.isfile(f) and os.path.splitext(f)[1].lower() in supported_exts]
 
if __name__ == "__main__":
    animations = [horizontal_scroll, vertical_scroll, rotate_image, zoom_image, fade_image]
    image_files = get_image_files(".")
 
    if not image_files:
        print("No image files found in the current directory.")
        exit()
 
    for filename in image_files:
        img = cv2.imread(filename)
        if img is None:
            print(f"Error reading {filename}. Skipping...")
            continue
 
        animation_fn = random.choice(animations)
        i = 0
        start_time = time.time()
 
        while True:
            i += 1
            frame = animation_fn(img, i)
 
            cv2.imshow("Image Slideshow", frame)
            key = cv2.waitKey(10) & 0xFF
 
            if key == ord('q'):
                cv2.destroyAllWindows()
                exit()
 
            # Show animation for 3 seconds
            if time.time() - start_time > 3:
                break
 
    cv2.destroyAllWindows()
