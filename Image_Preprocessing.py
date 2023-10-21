import cv2
import numpy as np

# Load the image
image = cv2.imread("test.jpeg")  # Replace with the path to your input image

if image is None:
    print("Image not found")
else:
    # Convert the image to grayscale
    grayscale_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply contrast adjustment
    alpha = 1.3  # Adjust the alpha value as needed
    beta = 2.2    # Adjust the beta value as needed
    contrast_adjusted_image = cv2.convertScaleAbs(grayscale_image, alpha=alpha, beta=beta)

    # Save the contrast-adjusted image
    cv2.imwrite("contrast_adjusted_image.jpg", contrast_adjusted_image)

    print("Image converted to grayscale and contrast adjusted. Saved as contrast_adjusted_image.jpg")
