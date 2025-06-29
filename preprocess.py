import os
import numpy as np
import cv2
from sklearn.model_selection import train_test_split
import glob

def create_directories(output_dir='data/processed'):
    """Create necessary directories for processed data"""
    os.makedirs(os.path.join(output_dir, 'train/oil'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'train/no_oil'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'val/oil'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'val/no_oil'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'test/oil'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'test/no_oil'), exist_ok=True)

def read_image(file_path):
    """Read image (handle .jpg and other formats)"""
    try:
        if file_path.lower().endswith('.jpg'):
            # Read image in grayscale for SAR images
            image = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            if image is not None:
                image = np.expand_dims(image, axis=-1)  # Add channel dimension (height, width, 1)
            return image
        elif file_path.lower().endswith(('.tif', '.tiff', '.jp2')):
            # For .tif, .tiff, .jp2 use rasterio (if you have multi-band SAR images)
            import rasterio
            with rasterio.open(file_path) as src:
                image = src.read()
                # Get all bands and transpose to channel-last format (height, width, channels)
                image = np.transpose(image, (1, 2, 0))
            return image
        else:
            print(f"Unsupported file type: {file_path}")
            return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def preprocess_image(image, size=(256, 256)):
    """Preprocess SAR image (log transform, resize, normalize)"""
    if image is None:
        return None
    
    # If the image is grayscale (single channel), convert to 3 channels for CNN
    if len(image.shape) == 2:  # Grayscale image (height, width)
        image = np.stack([image, image, image], axis=-1)  # Stack to (height, width, 3)
    
    # Log transform to enhance contrast (common for SAR)
    epsilon = 1e-6  # Small value to avoid log(0)
    log_image = np.log(image + epsilon)
    
    # Normalize to 0-1 range
    normalized = (log_image - np.min(log_image)) / (np.max(log_image) - np.min(log_image) + epsilon)
    
    # Resize image
    resized = cv2.resize(normalized, size)
    
    return resized

def process_dataset(oil_dir, no_oil_dir, output_dir='data/processed', test_size=0.2, val_size=0.2):
    """Process the dataset, split into train/val/test sets, and save the processed images"""
    create_directories(output_dir)
    
    # Get all oil spill images (including .jpg)
    oil_files = glob.glob(os.path.join(oil_dir, '*.jpg')) + \
                glob.glob(os.path.join(oil_dir, '*.tif')) + \
                glob.glob(os.path.join(oil_dir, '*.tiff')) + \
                glob.glob(os.path.join(oil_dir, '*.jp2'))  # Handle multiple formats
    
    # Get all non-oil spill images (including .jpg)
    no_oil_files = glob.glob(os.path.join(no_oil_dir, '*.jpg')) + \
                   glob.glob(os.path.join(no_oil_dir, '*.tif')) + \
                   glob.glob(os.path.join(no_oil_dir, '*.tiff')) + \
                   glob.glob(os.path.join(no_oil_dir, '*.jp2'))  # Handle multiple formats
    
    print(f"Found {len(oil_files)} oil spill images and {len(no_oil_files)} non-oil spill images")
    
    # Split datasets into training, validation, and testing
    oil_train, oil_temp = train_test_split(oil_files, test_size=test_size + val_size, random_state=42)
    oil_val, oil_test = train_test_split(oil_temp, test_size=test_size / (test_size + val_size), random_state=42)
    
    no_oil_train, no_oil_temp = train_test_split(no_oil_files, test_size=test_size + val_size, random_state=42)
    no_oil_val, no_oil_test = train_test_split(no_oil_temp, test_size=test_size / (test_size + val_size), random_state=42)
    
    # Process and save oil spill images
    process_images(oil_train, os.path.join(output_dir, 'train/oil'), 'oil')
    process_images(oil_val, os.path.join(output_dir, 'val/oil'), 'oil')
    process_images(oil_test, os.path.join(output_dir, 'test/oil'), 'oil')
    
    # Process and save non-oil spill images
    process_images(no_oil_train, os.path.join(output_dir, 'train/no_oil'), 'no_oil')
    process_images(no_oil_val, os.path.join(output_dir, 'val/no_oil'), 'no_oil')
    process_images(no_oil_test, os.path.join(output_dir, 'test/no_oil'), 'no_oil')
    
    print("Dataset processing completed")

def process_images(file_list, output_dir, prefix):
    """Process and save a list of images"""
    os.makedirs(output_dir, exist_ok=True)
    
    for i, file_path in enumerate(file_list):
        # Read the image
        image = read_image(file_path)
        
        if image is not None:
            # Preprocess the image (log transform, resize)
            processed = preprocess_image(image)
            
            if processed is not None:
                # Save the processed image as a PNG file
                output_path = os.path.join(output_dir, f"{prefix}_{i:04d}.png")
                cv2.imwrite(output_path, (processed * 255).astype(np.uint8))
                print(f"Processed {file_path} -> {output_path}")
            else:
                print(f"Failed to process {file_path}")
        else:
            print(f"Failed to read {file_path}")

if __name__ == "__main__":
    # Update these paths to point to your dataset
    oil_dataset_dir = r"E:\oil_spill_detection\data\raw\oil"
    no_oil_dataset_dir = r"E:\oil_spill_detection\data\raw\no_oil"
    
    process_dataset(oil_dataset_dir, no_oil_dataset_dir)
