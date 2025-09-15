import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [recognizedText, setRecognizedText] = useState('');
  const [imageData, setImageData] = useState(null);
  const BACKEND_URL = 'http://127.0.0.1:5000';
  const [isNavigating, setIsNavigating] = useState(false);
  const [isDetectingObjects, setIsDetectingObjects] = useState(false);
  const [videoStream, setVideoStream] = useState(null);
  const [mode, setMode] = useState(null);

  useEffect(() => {
    let eventSource;
    if (mode) {
      // Connect to appropriate video feed
      eventSource = new EventSource(`${BACKEND_URL}/video_feed/${mode}`);
      eventSource.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.image) {
            setVideoStream(`data:image/jpeg;base64,${data.image}`);
          }
        } catch (error) {
          console.error('Error parsing video data:', error);
        }
      };
      eventSource.onerror = (e) => {
        console.error('EventSource error:', e);
        eventSource.close();
      };
    }
    return () => {
      if (eventSource) eventSource.close();
      setVideoStream(null);
    };
  }, [mode, BACKEND_URL]);

  const handleStartNavigation = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/start_navigation`, {
        method: 'POST',
      });
      await response.json();
      setIsNavigating(true);
      setMode('navigation');
      setIsDetectingObjects(false); // Ensure object detection is off
    } catch (err) {
      console.error('Error starting navigation:', err);
      alert('Failed to start navigation.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopNavigation = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/stop_navigation`, {
        method: 'POST',
      });
      await response.json();
      setIsNavigating(false);
      setMode(null);
    } catch (err) {
      console.error('Error stopping navigation:', err);
      alert('Failed to stop navigation.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleObjectDetection = async () => {
    setIsLoading(true);
    try {
      if (isDetectingObjects) {
        // Stop object detection
        await fetch(`${BACKEND_URL}/api/stop-object-detection`, {
          method: 'POST',
        });
        setIsDetectingObjects(false);
        setMode(null);
      } else {
        // Start object detection
        await fetch(`${BACKEND_URL}/api/detect-object`, {
          method: 'POST',
        });
        setIsDetectingObjects(true);
        setMode('object_detection');
        setIsNavigating(false); // Ensure navigation is off
      }
    } catch (err) {
      console.error('Error toggling object detection:', err);
      alert('Failed to toggle object detection.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTextRecognition = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/detect-text`, {
        method: 'POST',
      });
      const data = await response.json();
      setRecognizedText(data.result);
      setImageData(data.image);

      // Speak the recognized text
      await fetch(`${BACKEND_URL}/api/speak-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: data.result }),
      });
    } catch (error) {
      console.error('Error recognizing text:', error);
      alert('Failed to recognize text.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmergency = async () => {
    setIsLoading(true);
    try {
      await fetch(`${BACKEND_URL}/api/voice-command-sos`, {
        method: 'POST',
      });
      // Optionally handle emergency response
    } catch (error) {
      console.error('Error triggering emergency:', error);
      alert('Failed to trigger emergency.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <div className="app-background"></div>
      <h1 className="title">VisionBridge AI</h1>
      <div className="button-group">
        <button
          className={`button ${isDetectingObjects ? 'active' : ''}`}
          onClick={handleObjectDetection}
        >
          {isDetectingObjects ? 'Stop Object Detection' : 'Object Detection'}
        </button>

        <button
          className="button"
          onClick={handleTextRecognition}
        >
          Text Recognition
        </button>

        <button
          className={`button ${isNavigating ? 'active' : ''}`}
          onClick={isNavigating ? handleStopNavigation : handleStartNavigation}
        >
          {isNavigating ? 'Stop Navigation' : 'Start Navigation'}
        </button>

        <button
          className="button emergency"
          onClick={handleEmergency}
        >
          Emergency
        </button>
      </div>
      {isLoading && (
        <div className="loader">
          <div className="loader-square"></div>
          <div className="loader-square"></div>
          <div className="loader-square"></div>
        </div>
      )}
      {/* Video Feed Display */}
      {(isNavigating || isDetectingObjects) && (
        <div className="video-container">
          {videoStream ? (
            <img src={videoStream} alt="Live Feed" className="live-video" />
          ) : (
            <div className="video-placeholder">Starting video feed...</div>
          )}
        </div>
      )}
      {/* Static Image Display (for text recognition) */}
      {imageData && !isNavigating && !isDetectingObjects && (
        <div className="image-container">
          <img
            src={`data:image/jpeg;base64,${imageData}`}
            alt="Detected Scene"
            className="detected-image"
          />
        </div>
      )}
      {/* Recognized Text Display */}
      {recognizedText && (
        <div className="recognized-text">
          <h3>Recognized Text:</h3>
          <p>{recognizedText}</p>
        </div>
      )}
      {/* Status Indicators */}
      {isNavigating && (
        <div className="status-indicator navigation">
          <div className="pulse-dot"></div>
          <span>Navigation Active</span>
        </div>
      )}
      {isDetectingObjects && (
        <div className="status-indicator detection">
          <div className="pulse-dot"></div>
          <span>Object Detection Active</span>
        </div>
      )}
    </div>
  );
}

export default App;











