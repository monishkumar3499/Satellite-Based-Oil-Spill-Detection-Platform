import os
import cv2
import numpy as np
from sar_fetcher import fetch_sar_image, get_sar_image_as_jpeg_bytes
from dotenv import load_dotenv

load_dotenv()

def test_fetch():
    # A known location with ocean (near a busy shipping lane for oil spills)
    # User specified coordinates
    lat, lon = 18.6265, 68.0356
    print(f"Testing SAR fetch at {lat}, {lon}...")
    
    # Test getting JPEG bytes
    jpeg_bytes, meta = get_sar_image_as_jpeg_bytes(lat, lon, radius_km=10.0)
    
    if jpeg_bytes:
        with open("test_sar_preview.jpg", "wb") as f:
            f.write(jpeg_bytes)
        print(f"Preview saved to test_sar_preview.jpg ({len(jpeg_bytes)} bytes)")
        print(f"Metadata: {meta}")
    else:
        print(f"Fetch failed: {meta}")

    # Test getting numpy array
    image, meta = fetch_sar_image(lat, lon, radius_km=10.0)
    if image is not None:
        # Scale back to 0-255 for saving
        save_img = (image * 255).astype(np.uint8)
        cv2.imwrite("test_sar_processed.png", save_img)
        print(f"Processed image saved to test_sar_processed.png")
    else:
        print(f"Array fetch failed: {meta}")

if __name__ == "__main__":
    test_fetch()
