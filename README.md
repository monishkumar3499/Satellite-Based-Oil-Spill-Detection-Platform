# 🌊 Oil Spill Detection Platform

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-orange.svg)](https://www.tensorflow.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-green.svg)](https://flask.palletsprojects.com/)

An **AI-powered satellite image classifier** using Sentinel-1 SAR data and deep learning for real-time oil spill detection and thickness estimation.

---

## ✨ Key Features

✅ **Smart Detection** – CNN-based classification of oil spills using Sentinel-1 SAR imagery  
✅ **Thickness Analysis** – Radiometry-based estimation of oil layer thickness  
✅ **Production Ready** – Flask REST API for real-time predictions  
✅ **Complete Pipeline** – Preprocessing, training, evaluation, and deployment

---

## 🛠 Tech Stack

**ML & Vision:** TensorFlow (Keras), OpenCV, scikit-learn  
**Data Processing:** pandas, NumPy  
**API:** Flask, Flask-CORS

---

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/monishkumar3499/Satellite-Based-Oil-Spill-Detection-Platform.git
cd Satellite-Based-Oil-Spill-Detection-Platform

# Install dependencies
pip install -r requirements.txt

# Train the model
python train.py --epochs 50 --batch-size 32

# Analyze oil thickness
python thickness_estimator.py --input data/radiometry.csv

# Start API server
python app.py
```

---

## 📊 Model Architecture

- **Input:** Sentinel-1 SAR images (224×224)
- **CNN Layers:** 4 conv blocks with batch normalization + MaxPooling
- **Regularization:** Dropout (0.5) to prevent overfitting
- **Output:** Multi-class classification (oil spill, look-alike, clean water)

---

## 🎯 Use Cases

🌍 **Environmental Monitoring** – Track and respond to marine oil spills  
🚢 **Maritime Safety** – Detect illegal discharge from vessels  
🏛️ **Regulatory Compliance** – Support enforcement agencies  
📈 **Research** – Analyze spill patterns and environmental impact

---

## 👨‍💻 Author

**Monish Kumar**  
📧 Email: [your-email@example.com](mailto:monishkumar3499@gmail.com)  
🔗 GitHub: [@monishkumar3499](https://github.com/monishkumar3499)

---

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

1. Fork the repository
2. Create feature branch (`git checkout -b feature/enhancement`)
3. Commit changes (`git commit -m 'Add new feature'`)
4. Push to branch (`git push origin feature/enhancement`)
5. Open Pull Request
