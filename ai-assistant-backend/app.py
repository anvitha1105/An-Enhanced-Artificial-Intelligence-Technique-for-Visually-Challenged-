# -- coding: utf-8 --
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import pyttsx3
import cv2
from ultralytics import YOLO
import threading
import time
import base64
import numpy as np
import speech_recognition as sr
import geocoder
from twilio.rest import Client
from difflib import SequenceMatcher
import pytesseract
import torch
import json
from queue import Queue
import os

app = Flask(__name__)
CORS(app)
# === Global Variables ===
navigation_running = False
object_detection_running = False
speech_queue = Queue()
video_lock = threading.Lock()

# === Models ===
model = YOLO('yolov8l.pt')  # Main detection model
nav_model = YOLO('yolov8n.pt')  # Navigation model
nav_model.conf = 0.3
nav_model.iou = 0.2

# === Constants ===
REFERENCE_WIDTH = 100
KNOWN_DISTANCE = 1.0
DISTANCE_THRESHOLD = 0.2
TIME_THRESHOLD = 3
previous_detections = {}
time_tracker = {}
account_sid = ''
auth_token = ''
twilio_whatsapp_number = 'whatsapp:+14155238886'
receiver_number = 'whatsapp:+91'

# === Helper Functions ===
def speech_worker():
    engine = pyttsx3.init()
    engine.setProperty('rate', 180)
    engine.setProperty('volume', 1.0)
    while True:
        text = speech_queue.get()
        if text is None:  # Exit signal
            break
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print("TTS Error:", e)
    engine.stop()

# Start speech worker thread
speech_thread = threading.Thread(target=speech_worker, daemon=True)
speech_thread.start()

def speak(text):
    if text:
        speech_queue.put(text)

def estimate_distance(bbox_width):
    return (REFERENCE_WIDTH * KNOWN_DISTANCE) / bbox_width if bbox_width > 0 else float('inf')

def calculate_direction(center_x, frame_width):
    if center_x < frame_width * 0.4:
        return "left"
    elif center_x > frame_width * 0.6:
        return "right"
    return "ahead"

def get_location_link():
    g = geocoder.ip('me')
    if g.ok and g.latlng:
        latitude, longitude = g.latlng
        city = g.city if g.city else "Unknown Location"
        return f"https://www.google.com/maps?q={latitude},{longitude}", city
    return None, None

def send_whatsapp_alert(location_link, city):
    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=twilio_whatsapp_number,
            body=f"SOS Alert! Emergency help needed.\nLocation: {city}\nLive on Map: {location_link}",
            to=receiver_number
        )
        print("WhatsApp message sent:", message.sid)
        speak("SOS sent to guardian on WhatsApp.")
    except Exception as e:
        print("Error sending WhatsApp message:", e)
        speak("Failed to send SOS.")

def get_obstacle_directions(frame, model):
    results = model.predict(source=frame, show=False, device='cpu')
    boxes = results[0].boxes
    classes = boxes.cls

    obstacles = []
    for i in range(len(classes)):
        cls = int(classes[i].tolist())
        name = results[0].names[cls]
        x1, y1, x2, y2 = map(int, boxes.xyxy[i].tolist())
        distance = estimate_distance(x2 - x1)
        direction = calculate_direction((x1 + x2) / 2, frame.shape[1])

        if distance < 3.0:
            obstacles.append({
                'name': name,
                'distance': distance,
                'direction': direction
            })
    return obstacles

def generate_navigation_instructions(obstacles):
    if not obstacles:
        return "Path is clear, continue straight ahead"

    instructions = []
    center_obstacles = [o for o in obstacles if o['direction'] == 'ahead']

    if center_obstacles:
        closest = min(center_obstacles, key=lambda x: x['distance'])
        if closest['distance'] < 1.5:
            turn = "left" if len([o for o in obstacles if o['direction'] == 'left']) < \
                        len([o for o in obstacles if o['direction'] == 'right']) else "right"
            instructions.append(f"Obstacle ahead at {closest['distance']:.1f} meters, turn {turn}")

    for side in ['left', 'right']:
        side_obstacles = [o for o in obstacles if o['direction'] == side]
        if side_obstacles:
            closest = min(side_obstacles, key=lambda x: x['distance'])
            if closest['distance'] < 1.0:
                instructions.append(f"Close obstacle to your {side} at {closest['distance']:.1f} meters")

    return ". ".join(instructions) if instructions else "Path is clear, continue straight ahead"

def generate_frames(mode):
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    last_update_time = 0
    update_interval = 3  # seconds

    try:
        while (navigation_running if mode == 'navigation' else object_detection_running):
            with video_lock:
                ret, frame = cap.read()
                if not ret:
                    break

                current_model = nav_model if mode == 'navigation' else model
                results = current_model.predict(source=frame, show=False, device='cpu')
                boxes = results[0].boxes

                detected_objects = []
                for i in range(len(boxes)):
                    cls = int(boxes.cls[i].tolist())
                    name = results[0].names[cls]
                    x1, y1, x2, y2 = map(int, boxes.xyxy[i].tolist())
                    distance = estimate_distance(x2 - x1)

                    color = (0, 255, 0) if mode == 'navigation' else (0, 0, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f'{name} {distance:.1f}m',
                                (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    detected_objects.append(f"{name} at {distance:.1f}m")

                current_time = time.time()
                if current_time - last_update_time > update_interval:
                    if mode == 'navigation':
                        obstacles = get_obstacle_directions(frame, nav_model)
                        instructions = generate_navigation_instructions(obstacles)
                        speak(instructions)
                    else:
                        speak("I see " + ", ".join(detected_objects) if detected_objects else "No objects detected")
                    last_update_time = current_time

                _, buffer = cv2.imencode('.jpg', frame)
                # fixed parenthesis in the json.dumps call
                yield f"data: {json.dumps({'image': base64.b64encode(buffer).decode('utf-8')})}\n\n"
                time.sleep(0.05)
    finally:
        cap.release()

# === Routes ===
@app.route('/video_feed/<mode>')
def video_feed(mode):
    if mode not in ['navigation', 'object_detection']:
        return jsonify({"error": "Invalid mode"}), 400
    return Response(generate_frames(mode), mimetype='text/event-stream')

@app.route('/start_navigation', methods=['POST'])
def start_navigation():
    global navigation_running
    if not navigation_running:
        navigation_running = True
        return jsonify({'message': 'Navigation started', 'video_feed': '/video_feed/navigation'}), 200
    return jsonify({'message': 'Navigation already running'}), 200

@app.route('/stop_navigation', methods=['POST'])
def stop_navigation():
    global navigation_running
    navigation_running = False
    return jsonify({'message': 'Navigation stopped'}), 200

@app.route("/api/detect-object", methods=["POST"])
def detect_object():
    global object_detection_running
    object_detection_running = True
    return jsonify({
        'message': 'Object detection started',
        'video_feed': '/video_feed/object_detection'
    }), 200

@app.route("/api/stop-object-detection", methods=["POST"])
def stop_object_detection():
    global object_detection_running
    object_detection_running = False
    return jsonify({'message': 'Object detection stopped'}), 200

@app.route("/api/detect-text", methods=["POST"])
def detect_text():
    with video_lock:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
    if not ret or frame is None:
        return jsonify({"error": "Failed to capture frame from webcam."})
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    try:
        text = pytesseract.image_to_string(gray)
        cleaned_text = text.strip()
        if cleaned_text:
            speak(cleaned_text)
            result = f"Detected Text: {cleaned_text}"
        else:
            result = "No readable text found in the frame."
    except Exception as e:
        result = f"OCR Error: {str(e)}"
    _, buffer = cv2.imencode('.jpg', frame)
    return jsonify({
        "result": result,
        "image": base64.b64encode(buffer).decode('utf-8')
    })

@app.route("/api/speak-text", methods=["POST"])
def speak_text():
    text = request.json.get("text", "")
    speak(text)
    return jsonify({"status": "spoken", "text": text})

@app.route("/api/voice-command-sos", methods=["POST"])
def voice_command_sos():
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            speak("Listening for SOS command")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=15, phrase_time_limit=10)
            command = recognizer.recognize_google(audio).lower()
            print("Heard:", command)
            similarity = SequenceMatcher(None, command, "help me").ratio()
            print(f"Similarity: {similarity:.2f}")
            if similarity > 0.7:
                speak("SOS detected. Sending alert.")
                location_link, city = get_location_link()
                if location_link:
                    send_whatsapp_alert(location_link, city)
                    return jsonify({"command": command, "status": "SOS Sent", "location": location_link})
                return jsonify({"command": command, "error": "Could not retrieve location."})
            return jsonify({"command": command, "status": "No action taken"})
    except sr.WaitTimeoutError:
        return jsonify({"error": "Listening timeout exceeded. No speech detected."})
    except sr.UnknownValueError:
        return jsonify({"error": "Could not understand audio"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/test-webcam", methods=["GET"])
def test_webcam():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return jsonify({"error": "Could not open webcam"}), 500
    cap.release()
    return jsonify({"status": "Webcam test passed ✅"})

if __name__ == "__main__":
    app.run(debug=True, threaded=True)

    
