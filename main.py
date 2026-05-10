import os
import glob
import uuid
import threading
import numpy as np
import cv2
import tensorflow as tf
import pandas as pd
import base64
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# Configure production-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('platform.log')
    ]
)
logger = logging.getLogger(__name__)

# Import our custom PhD-grade modules
from sar_fetcher import fetch_sar_image, get_sar_image_as_jpeg_bytes
from marine_data import fetch_all_marine_data, compute_final_decision

load_dotenv()

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)
CORS(app)  # Enable CORS for React frontend

# In-memory store for async LLM research jobs
research_jobs = {}

# Automatically find the latest trained model
def get_latest_model():
    model_files = glob.glob(os.path.join("cnn-model", "models", "oil_spill_model_final_*.h5"))
    if not model_files:
        model_files = glob.glob(os.path.join("cnn-model", "models", "oil_spill_model_*.h5"))
    
    if not model_files:
        raise FileNotFoundError("No trained model found in the 'cnn-model/models' directory.")
    
    latest_model = max(model_files, key=os.path.getmtime)
    print(f"Loading model: {latest_model}")
    return latest_model

MODEL_PATH = get_latest_model()
model = tf.keras.models.load_model(MODEL_PATH)

# Helper function for manual file uploads
def preprocess_manual_image(image, size=(256, 256)):
    if image is None: return None
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image_3ch = np.stack([image, image, image], axis=-1)
    epsilon = 1e-6
    log_image = np.log(image_3ch.astype(np.float32) + epsilon)
    normalized = (log_image - np.min(log_image)) / (np.max(log_image) - np.min(log_image) + epsilon)
    return cv2.resize(normalized, size)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze_location", methods=["POST"])
def analyze_location():
    """
    Ph.D. Researcher Endpoint:
    1. Extract SAR image from CDSE by lat/lon.
    2. Extract Marine context (Wind/SST) from CMEMS.
    3. Run CNN inference.
    4. Perform Multi-modal Decision Fusion.
    """
    data = request.json
    lat = data.get("lat")
    lon = data.get("lon")

    logger.info(f"--- Starting Analysis for Location: {lat}, {lon} ---")

    if lat is None or lon is None:
        logger.warning("Request rejected: Missing Latitude or Longitude.")
        return jsonify({"error": "Latitude and Longitude are required"}), 400

    # 1. Unified Fetch: Get raw bytes first (as per successful test_sar.py)
    logger.info("Step 1: Fetching Satellite SAR Imagery (Unified Fetch)...")
    jpeg_bytes, sar_meta = get_sar_image_as_jpeg_bytes(lat, lon, radius_km=10.0, days_back=60)
    
    if not jpeg_bytes:
        error_msg = sar_meta.get("error", "No data found")
        logger.error(f"Satellite Data Acquisition Failed: {error_msg}")
        return jsonify({
            "error": "Failed to fetch satellite imagery for this location.",
            "details": error_msg
        }), 404

    # 2. Process bytes for CNN (Avoid second API call)
    logger.info("Step 2: Processing imagery for Deep Learning...")
    nparr = np.frombuffer(jpeg_bytes, np.uint8)
    image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    
    # Normalization: The image is already log-scaled by the evalscript.
    # We just normalize to [0, 1] for the model input.
    sar_image = image_rgb.astype(np.float32) / 255.0
    sar_image = cv2.resize(sar_image, (256, 256))
    
    sar_b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
    logger.info(f"Successfully processed SAR image. BBox: {sar_meta.get('bbox')}")

    # 3. Fetch All Marine context (Wind/SST/Waves)
    logger.info("Step 3: Fetching Physical Ocean Context via Open-Meteo API...")
    ocean_context = fetch_all_marine_data(lat, lon)
    logger.info(f"Context retrieved from Open-Meteo: Wind {ocean_context.get('wind_speed_ms')}m/s, Temp {ocean_context.get('temperature_c')}C, Waves {ocean_context.get('wave_height_m')}m")

    # 4. CNN Inference
    logger.info("Step 4: Running CNN Deep Learning Inference...")
    input_data = np.expand_dims(sar_image, axis=0)
    prediction_score = float(model.predict(input_data)[0][0])
    logger.info(f"CNN Raw Confidence Score: {prediction_score*100:.2f}%")

    # 5. Scientific Decision Fusion
    logger.info("Step 5: Performing Multi-modal Decision Fusion...")
    decision = compute_final_decision(prediction_score, ocean_context)

    # 6. Fire LLM Research Synthesis in background (non-blocking)
    job_id = str(uuid.uuid4())
    research_jobs[job_id] = {"status": "pending"}

    def run_llm(j_id, lt, ln, score, ctx, label):
        from intelligence_engine import generate_research_brief
        logger.info(f"Step 6: [BG Thread] Generating Research Brief for job {j_id}...")
        try:
            brief = generate_research_brief(lt, ln, score, ctx, label)
            research_jobs[j_id] = {"status": "ready", "data": brief}
            logger.info(f"Step 6: [BG Thread] Research Brief ready for job {j_id}")
        except Exception as e:
            research_jobs[j_id] = {"status": "error", "data": {"location_name": f"{lt:.4f}°N, {ln:.4f}°E", "research_summary": str(e), "ieee_report_body": "N/A"}}

    thread = threading.Thread(target=run_llm, args=(job_id, lat, lon, decision['raw_cnn_confidence'], ocean_context, decision['final_label']), daemon=True)
    thread.start()

    logger.info("--- Core Analysis Complete. LLM running in background. ---")

    return jsonify({
        "lat": lat,
        "lon": lon,
        "sar_image_b64": sar_b64,
        "results": decision,
        "research_job_id": job_id,
        "metadata": sar_meta
    })


@app.route("/research_status/<job_id>", methods=["GET"])
def research_status(job_id):
    """Poll this endpoint to get the LLM research brief when ready."""
    job = research_jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404
    return jsonify(job)

@app.route("/predict", methods=["POST"])
def predict():
    """Legacy endpoint for manual file uploads"""
    if 'image' not in request.files or 'radiometry' not in request.files:
        return jsonify({"error": "Both SAR image and radiometry CSV file are required"}), 400

    image_file = request.files['image']
    npimg = np.frombuffer(image_file.read(), np.uint8)
    image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if image is None:
        return jsonify({"error": "Failed to read the image"}), 400

    processed_image = preprocess_manual_image(image)
    input_data = np.expand_dims(processed_image, axis=0)
    prediction_score = float(model.predict(input_data)[0][0])
    
    # Simple logic for legacy radiometry CSV
    try:
        df = pd.read_csv(request.files['radiometry'])
        avg_thickness = df['Thickness'].mean() if 'Thickness' in df.columns else 0
    except:
        avg_thickness = 0

    confidence = round(prediction_score * 100, 2)
    label = "Oil Spill Detected" if (prediction_score >= 0.5 or avg_thickness > 10) else "No Oil Spill Found"

    return jsonify({
        "prediction": label,
        "confidence": confidence,
        "thickness_hint": avg_thickness
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
