from flask import Flask, request, jsonify, render_template
import numpy as np
import cv2
import tensorflow as tf
import pandas as pd
import os

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

# Load the trained model once at startup
MODEL_PATH = os.path.join("models", "oil_spill_model_final_20250519-134505.h5")
model = tf.keras.models.load_model(MODEL_PATH)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    if 'image' not in request.files or 'radiometry' not in request.files:
        return jsonify({"error": "Both SAR image and radiometry CSV file are required"}), 400

    # ----------- Handle SAR Image ----------
    image_file = request.files['image']
    image_bytes = image_file.read()
    npimg = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if image is None:
        return jsonify({"error": "Failed to read the image"}), 400

    image = cv2.resize(image, (256, 256))
    image = image / 255.0
    image = np.expand_dims(image, axis=0)

    prediction_score = model.predict(image)[0][0]
    cnn_label = "Oil Spill Detected" if prediction_score >= 0.5 else "No Oil Spill Found"
    confidence = round(float(prediction_score) * 100, 2)

    # ----------- Handle Radiometry CSV ----------
    csv_file = request.files['radiometry']
    try:
        df = pd.read_csv(csv_file)

        if 'Thickness' in df.columns:
            avg_thickness = df['Thickness'].mean()

            if avg_thickness > 50:
                thickness = "Thick layer"
                reason = "High thickness value indicates a strong presence of oil."
                oil_type = "Crude Oil or Emulsified Oil"
                thickness_flag = "high"
            elif 20 < avg_thickness <= 50:
                thickness = "Moderate layer"
                reason = "Moderate thickness suggests a medium oil spread."
                oil_type = "Diesel or Lubricant Oil"
                thickness_flag = "moderate"
            elif 0 < avg_thickness <= 20:
                thickness = "Thin layer"
                reason = "Low thickness points to a light oil film."
                oil_type = "Sheen or Light Oil"
                thickness_flag = "low"
            else:
                thickness = "None"
                reason = "Zero thickness indicates no visible oil layer."
                oil_type = "None"
                thickness_flag = "none"
        else:
            thickness = "Unknown"
            reason = "Missing 'Thickness' column in radiometry data."
            oil_type = "Unknown"
            thickness_flag = "unknown"

    except Exception as e:
        thickness = "Error"
        reason = f"Failed to read radiometry file: {str(e)}"
        oil_type = "Unknown"
        thickness_flag = "unknown"

    # ----------- Override Based on Cross-Check ----------
    if thickness_flag in ["moderate", "high", "low"]:
        final_label = "Oil Spill Detected"
    else:
        final_label = "No Oil Spill Found"
        

    # ----------- Response JSON ----------
    return jsonify({
        "prediction": final_label,
        "confidence": confidence,
        "thickness": thickness,
        "reason": reason,
        "oil_type": oil_type
    })

if __name__ == "__main__":
    app.run(debug=True)
