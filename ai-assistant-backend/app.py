from flask import Flask, request, jsonify
from flask_cors import CORS
import pyttsx3
import cv2  # OpenCV for webcam test

app = Flask(__name__)
CORS(app)

# Initialize pyttsx3 engine only once
engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

@app.route("/api/detect-object", methods=["POST"])
def detect_object():
    result = "Object detected: Apple 🍎"
    speak(result)
    return jsonify({"result": result})

@app.route("/api/detect-text", methods=["POST"])
def detect_text():
    result = "Detected text: Hello World 🌍"
    speak(result)
    return jsonify({"result": result})

@app.route("/api/speak-text", methods=["POST"])
def speak_text():
    text = request.json.get("text", "")
    speak(text)
    return jsonify({"status": "spoken", "text": text})

# Webcam test route
@app.route("/api/test-webcam", methods=["GET"])
def test_webcam():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return jsonify({"error": "Could not open webcam"}), 500

    print("Video capture opened successfully")
    cap.release()
    return jsonify({"status": "Webcam test passed ✅"})

# Webcam stop simulation route
@app.route("/api/stop-webcam", methods=["POST"])
def stop_webcam():
    # Just a simulated endpoint – the frontend handles actual webcam release
    print("Stop webcam requested from frontend")
    return jsonify({"status": "Webcam stop simulated ✅"})

if __name__ == "__main__":
    app.run(debug=True)





