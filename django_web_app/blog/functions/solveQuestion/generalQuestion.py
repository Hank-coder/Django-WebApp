from PIL import Image

import pytesseract

# Timeout/terminate the tesseract job after a period of time
try:
    print(pytesseract.image_to_string('test.png', timeout=30))  # Timeout after 30 seconds
except RuntimeError as timeout_error:
    # Tesseract processing is terminated
    pass
