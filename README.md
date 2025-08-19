# 🌊 Oil Spill Detection Platform  

An **AI-powered satellite image classifier** using Sentinel-1 SAR data and deep learning for accurate oil spill detection, combined with radiometry-based thickness estimation for oil layers.  

---

## ✨ Features  
✅ Preprocesses Sentinel-1 SAR images (resize, normalize, train/val/test split)  
✅ Classifies images using a **TensorFlow (Keras) CNN** with convolution, pooling, batch normalization, and dropout layers  
✅ Provides **oil layer thickness estimation** by analyzing radiometry CSV data  
✅ Serves predictions through a **Flask API** with real-time inference results  

---

## 🛠 Tech Stack  
- **Backend & Deep Learning:** Python, TensorFlow (Keras)  
- **Image Processing:** OpenCV  
- **ML Utilities:** scikit-learn  
- **Data Handling:** pandas (for radiometry thickness analysis)  
- **Web Framework:** Flask  

---

## 🚀 Usage  

```bash
# Clone the repo
git clone https://github.com/monishkumar3499/Satellite-Based-Oil-Spill-Detection-Platform.git
cd Satellite-Based-Oil-Spill-Detection-Platform

# Install dependencies
pip install -r requirements.txt

# Train the model
python train.py

# Start the API server
python app.py
