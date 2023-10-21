from PIL import Image
import pytesseract

# Set the path to the Tesseract OCR executable
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

# Open an image using PIL (Pillow)
img = Image.open('contrast_adjusted_image.jpg')

# Use pytesseract to extract text
text = pytesseract.image_to_string(img)

# Specify the path and filename for the output text file
output_text_file = 'extracted_text.txt'

# Write the extracted text to the text file
with open(output_text_file, 'w', encoding='utf-8') as file:
    file.write(text)

print("Text extracted from the image and saved in", output_text_file)
