import React, { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [showVideo, setShowVideo] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const videoRef = useRef(null);
  const streamRef = useRef(null); // Store media stream to stop later

  const handleAction = async (actionType) => {
    let speechText = '';

    setIsLoading(true);
    setShowVideo(true);

    try {
      if (actionType === 'Object Detection') {
        const res = await fetch('http://127.0.0.1:5000/api/detect-object', { method: 'POST' });
        const data = await res.json();
        speechText = data.result;
      } else if (actionType === 'Text Recognition') {
        const res = await fetch('http://127.0.0.1:5000/api/detect-text', { method: 'POST' });
        const data = await res.json();
        speechText = data.result;
      } else if (actionType === 'Object + Text Detection') {
        const res1 = await fetch('http://127.0.0.1:5000/api/detect-object', { method: 'POST' });
        const data1 = await res1.json();
        const res2 = await fetch('http://127.0.0.1:5000/api/detect-text', { method: 'POST' });
        const data2 = await res2.json();
        speechText = `${data1.result}. ${data2.result}`;
      }

      await fetch('http://127.0.0.1:5000/api/speak-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: speechText }),
      });

    } catch (error) {
      console.error('Backend error:', error);
      alert('Backend error. Please check if Flask server is running.');
    } finally {
      setIsLoading(false);
    }
  };

  // Open webcam feed
  useEffect(() => {
    if (showVideo && videoRef.current) {
      navigator.mediaDevices.getUserMedia({ video: true })
        .then((stream) => {
          streamRef.current = stream;
          videoRef.current.srcObject = stream;
        })
        .catch((err) => {
          console.error("Error accessing webcam:", err);
        });
    }
  }, [showVideo]);

  const handleStopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setShowVideo(false);
  };

  return (
    <div className="app-container">
      <h1 className="title">VisionBridge AI</h1>

      <div className="button-group">
        <button className="button" onClick={() => handleAction('Object Detection')}>Start Object Detection</button>
        <button className="button" onClick={() => handleAction('Text Recognition')}>Start Text Recognition</button>
        <button className="button" onClick={() => handleAction('Object + Text Detection')}>Start Object + Text + Audio</button>
        {showVideo && (
          <button className="stop-button" onClick={handleStopCamera}>Stop Camera</button>
        )}
      </div>

      {showVideo && (
        <div className="video-container">
          <video autoPlay muted className="video-box" ref={videoRef} />
        </div>
      )}

      {isLoading && (
        <div className="loader">
          <div className="loader-square"></div>
          <div className="loader-square"></div>
          <div className="loader-square"></div>
          <div className="loader-square"></div>
          <div className="loader-square"></div>
          <div className="loader-square"></div>
          <div className="loader-square"></div>
        </div>
      )}
    </div>
  );
}

export default App;










