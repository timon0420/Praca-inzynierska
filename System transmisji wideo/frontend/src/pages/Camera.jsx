import { useRef, useEffect, useState } from 'react' 
import { Link } from 'react-router-dom';
import '../styles/camera.css';

export const Camera = () => {

    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const wsRef = useRef(null);
    const [stream, setStream] = useState(null);
    const [error, setError] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState('connecting');

    const startCamera = async () => {
        setError(null);
        try {
            const mediaStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'envioronment',
                    width: {ideal: 1280},
                    height: {ideal: 720}
                }
            });

            setStream(mediaStream);
            if (videoRef.current) {
                videoRef.current.srcObject = mediaStream;
            }
        } catch (err) {
            alert(err);
            setError("Camera not available");
        }
    };

    const stopCamera = () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            setStream(null);
            if (videoRef.current) {
                videoRef.current.srcObejct = null;
            }
        }
    };

    useEffect(() => {
        const websocket = new WebSocket('ws://localhost:8080/ws');
        wsRef.current = websocket;

        websocket.onopen = () => {
            setConnectionStatus('connected');
            console.log('Connected to server');
        };
        websocket.onmessage = (event) => console.log(event.data);
        websocket.onerror = () => setConnectionStatus('disconnected');
        websocket.onclose = () => {
            setConnectionStatus('disconnected');
            console.log('Disconnected from server');
        };

        return () => {
            wsRef.current = null;
            websocket.close();
        };
    }, [])

    useEffect(() => {
        if (!stream) return undefined;

        const interval = setInterval(() => {
            if (!videoRef.current || !canvasRef.current) return;

            const canvas = canvasRef.current;
            const video = videoRef.current;
            const context = canvas.getContext('2d');

            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0, canvas.width, canvas.height);

            canvas.toBlob((blob) => {
                const websocket = wsRef.current;
                if (blob && websocket?.readyState === WebSocket.OPEN) {
                    websocket.send(blob);
                }
            }, 'image/jpeg', 0.5);
        }, 33); // 30 fps

        return () => clearInterval(interval);
    }, [stream]);

    return (
        <main className="camera-page">
            <header className="camera-header">
                <div>
                    <span className="eyebrow">Transmisja obrazu</span>
                    <h1>Kamera sterująca</h1>
                    <p>Przekaż obraz do systemu analizy gestów.</p>
                </div>
                <div
                    className={`connection-status connection-status--${connectionStatus}`}
                    role="status"
                >
                    <span className="connection-status__dot" aria-hidden="true" />
                    {connectionStatus === 'connected'
                        ? 'WebSocket połączony'
                        : connectionStatus === 'connecting'
                            ? 'Łączenie z WebSocket…'
                            : 'WebSocket rozłączony'}
                </div>
            </header>

            <section className="camera-workspace" aria-label="Panel kamery">
                <aside className="camera-controls">
                    <div className="camera-controls__heading">
                        <span className="camera-controls__step">01</span>
                        <div>
                            <h2>Sterowanie</h2>
                            <p>Włącz kamerę i ustaw dłoń w kadrze.</p>
                        </div>
                    </div>

                    <div className="camera-controls__actions">
                    {!stream ? (
                        <button className="button button--primary" onClick={startCamera}>
                            Uruchom kamerę
                        </button>
                    ) : (
                        <button className="button button--danger" onClick={stopCamera}>
                            Zatrzymaj kamerę
                        </button>
                    )}
                    </div>

                    {error && (
                        <p className="camera-error" role="alert">
                            <span aria-hidden="true">!</span>
                            {error}
                        </p>
                    )}

                    <div className="camera-help">
                        <h3>Wskazówki</h3>
                        <ul>
                            <li>Zadbaj o równomierne oświetlenie.</li>
                            <li>Trzymaj całą dłoń w obszarze kamery.</li>
                            <li>Nie zasłaniaj palców podczas ruchu.</li>
                        </ul>
                    </div>
                </aside>

                <div className={`camera-preview ${stream ? 'camera-preview--active' : ''}`}>
                    <div className="camera-preview__topbar">
                        <span>Podgląd na żywo</span>
                        <span className={`camera-state ${stream ? 'camera-state--active' : ''}`}>
                            {stream ? 'Aktywna' : 'Nieaktywna'}
                        </span>
                    </div>
                    <div className="camera-preview__viewport">
                        <video
                            ref={videoRef}
                            autoPlay
                            playsInline
                            className={`camera-preview__video ${stream ? 'is-visible' : ''}`}
                        />
                        <canvas ref={canvasRef} className="visually-hidden-canvas" />
                        {!stream && (
                            <div className="camera-placeholder">
                                <div className="camera-placeholder__icon" aria-hidden="true">
                                    <span />
                                </div>
                                <h2>Kamera jest wyłączona</h2>
                                <p>Uruchom kamerę, aby zobaczyć podgląd obrazu.</p>
                            </div>
                        )}
                    </div>
                </div>
            </section>

            <Link className="camera-back-link" to="/">
                <span aria-hidden="true">←</span>
                Powrót do strony głównej
            </Link>
        </main>
    )
}
