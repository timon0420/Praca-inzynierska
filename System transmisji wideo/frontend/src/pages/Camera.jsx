import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import '../styles/camera.css'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'https://websocket-inzynierka.onrender.com').replace(/\/$/, '')

const websocketUrl = (path, token) => {
    const url = new URL(API_BASE_URL)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    url.pathname = path
    url.search = new URLSearchParams({ token }).toString()
    return url.toString()
}

export const Camera = () => {
    const videoRef = useRef(null)
    const canvasRef = useRef(null)
    const wsRef = useRef(null)
    const streamRef = useRef(null)
    const encodingRef = useRef(false)
    const [stream, setStream] = useState(null)
    const [error, setError] = useState(null)
    const [session, setSession] = useState(null)
    const [connectionStatus, setConnectionStatus] = useState('connecting')
    const [analysisStatus, setAnalysisStatus] = useState('unknown')
    const [unityConnected, setUnityConnected] = useState(false)
    const [analysis, setAnalysis] = useState({ detected: false, angles: null, processingMs: null })

    const stopCamera = useCallback(() => {
        streamRef.current?.getTracks().forEach((track) => track.stop())
        streamRef.current = null
        setStream(null)
        setAnalysis({ detected: false, angles: null, processingMs: null })
        if (videoRef.current) videoRef.current.srcObject = null
    }, [])

    useEffect(() => {
        const controller = new AbortController()
        const createSession = async () => {
            try {
                const stored = sessionStorage.getItem('manipulatorSession')
                if (stored) {
                    const restored = JSON.parse(stored)
                    if (restored?.code && restored?.browserToken && new Date(restored.expiresAt) > new Date()) {
                        setSession(restored)
                        return
                    }
                    sessionStorage.removeItem('manipulatorSession')
                }
                const response = await fetch(`${API_BASE_URL}/api/sessions`, {
                    method: 'POST',
                    signal: controller.signal,
                })
                if (!response.ok) throw new Error('Nie udało się utworzyć sesji.')
                const created = await response.json()
                sessionStorage.setItem('manipulatorSession', JSON.stringify(created))
                setSession(created)
            } catch (requestError) {
                if (requestError.name !== 'AbortError') {
                    setConnectionStatus('disconnected')
                    setError(requestError.message)
                }
            }
        }
        createSession()
        return () => controller.abort()
    }, [])

    useEffect(() => {
        if (!session) return undefined
        const socket = new WebSocket(websocketUrl('/ws/browser', session.browserToken))
        wsRef.current = socket
        setConnectionStatus('connecting')

        socket.onopen = () => setConnectionStatus('connected')
        socket.onmessage = (event) => {
            if (typeof event.data !== 'string') return
            try {
                const message = JSON.parse(event.data)
                if (message.type === 'status') {
                    setAnalysisStatus(message.analysis || 'unavailable')
                    setUnityConnected(Boolean(message.unity))
                } else if (message.type === 'analysis') {
                    setAnalysisStatus('ready')
                    setAnalysis({
                        detected: Boolean(message.detected),
                        angles: message.detected ? message.angles : null,
                        processingMs: message.processingMs,
                    })
                    setError(null)
                } else if (message.type === 'analysis_error') {
                    setAnalysisStatus('unavailable')
                    setError(message.message || 'Analiza obrazu jest niedostępna.')
                }
            } catch {
                setError('Serwer przesłał nieprawidłowy komunikat.')
            }
        }
        socket.onerror = () => setConnectionStatus('disconnected')
        socket.onclose = () => setConnectionStatus('disconnected')

        return () => {
            wsRef.current = null
            socket.close()
        }
    }, [session])

    useEffect(() => {
        if (connectionStatus !== 'connected') stopCamera()
    }, [connectionStatus, stopCamera])
    useEffect(() => () => stopCamera(), [stopCamera])

    const startCamera = async () => {
        setError(null)
        try {
            const mediaStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment',
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                },
            })
            streamRef.current = mediaStream
            setStream(mediaStream)
            if (videoRef.current) videoRef.current.srcObject = mediaStream
        } catch {
            setError('Kamera jest niedostępna lub odmówiono dostępu.')
        }
    }

    useEffect(() => {
        if (!stream) return undefined
        const interval = setInterval(() => {
            const socket = wsRef.current
            const video = videoRef.current
            const canvas = canvasRef.current
            if (encodingRef.current || !video || !canvas || socket?.readyState !== WebSocket.OPEN) return
            if (!video.videoWidth || !video.videoHeight) return
            encodingRef.current = true
            canvas.width = 640
            canvas.height = 480
            canvas.getContext('2d').drawImage(video, 0, 0, 640, 480)
            canvas.toBlob((blob) => {
                try {
                    if (blob && blob.size <= 200 * 1024 && socket.readyState === WebSocket.OPEN) {
                        socket.send(blob)
                    }
                } finally {
                    encodingRef.current = false
                }
            }, 'image/jpeg', 0.7)
        }, 100)
        return () => {
            clearInterval(interval)
            encodingRef.current = false
        }
    }, [stream])

    const cameraReady = analysisStatus === 'ready' && connectionStatus === 'connected'
    const expiresAt = session ? new Date(session.expiresAt).toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' }) : '—'

    return (
        <main className="camera-page">
            <header className="camera-header">
                <div>
                    <span className="eyebrow">Analiza obrazu</span>
                    <h1>Kamera sterująca</h1>
                    <p>Obraz dłoni jest analizowany na serwerze i zamieniany na kąty manipulatora.</p>
                </div>
                <div className={`connection-status connection-status--${connectionStatus}`} role="status">
                    <span className="connection-status__dot" aria-hidden="true" />
                    {connectionStatus === 'connected' ? 'Serwer połączony' : connectionStatus === 'connecting' ? 'Łączenie…' : 'Serwer rozłączony'}
                </div>
            </header>

            <section className="session-panel" aria-label="Dane sesji">
                <div>
                    <span className="session-panel__label">Kod sesji Unity</span>
                    <strong className="session-panel__code">{session?.code || '…'}</strong>
                    <span className="session-panel__expiry">Ważny do {expiresAt}</span>
                </div>
                <div className="session-panel__clients">
                    <span className={analysisStatus === 'ready' ? 'client-state is-online' : 'client-state'}>
                        <i /> Analiza {analysisStatus === 'ready' ? 'gotowa' : 'niedostępna'}
                    </span>
                    <span className={unityConnected ? 'client-state is-online' : 'client-state'}>
                        <i /> Unity {unityConnected ? 'połączone' : 'oczekuje'}
                    </span>
                </div>
            </section>

            <section className="camera-workspace" aria-label="Panel kamery">
                <aside className="camera-controls">
                    <div className="camera-controls__heading">
                        <span className="camera-controls__step">01</span>
                        <div>
                            <h2>Sterowanie</h2>
                            <p>Wpisz powyższy kod w Unity, a następnie uruchom kamerę.</p>
                        </div>
                    </div>

                    <div className="camera-controls__actions">
                        {!stream ? (
                            <button className="button button--primary" onClick={startCamera} disabled={!cameraReady}>Uruchom kamerę</button>
                        ) : (
                            <button className="button button--danger" onClick={stopCamera}>Zatrzymaj kamerę</button>
                        )}
                    </div>

                    {!cameraReady && !error && <p className="camera-notice">Oczekiwanie na usługę analizy obrazu.</p>}
                    {error && <p className="camera-error" role="alert"><span aria-hidden="true">!</span>{error}</p>}

                    <div className="analysis-results" aria-live="polite">
                        <h3>{analysis.detected ? 'Dłoń wykryta' : 'Brak wykrytej dłoni'}</h3>
                        {analysis.angles && (
                            <div className="analysis-results__angles">
                                {analysis.angles.map((angle, index) => (
                                    <span key={index}>A{index + 1}: <strong>{Number(angle).toFixed(1)}°</strong></span>
                                ))}
                            </div>
                        )}
                        {analysis.processingMs != null && <small>Analiza: {Number(analysis.processingMs).toFixed(1)} ms</small>}
                    </div>

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
                        <span className={`camera-state ${stream ? 'camera-state--active' : ''}`}>{stream ? 'Aktywna' : 'Nieaktywna'}</span>
                    </div>
                    <div className="camera-preview__viewport">
                        <video ref={videoRef} autoPlay playsInline muted className={`camera-preview__video ${stream ? 'is-visible' : ''}`} />
                        <canvas ref={canvasRef} className="visually-hidden-canvas" />
                        {!stream && (
                            <div className="camera-placeholder">
                                <div className="camera-placeholder__icon" aria-hidden="true"><span /></div>
                                <h2>Kamera jest wyłączona</h2>
                                <p>Uruchom kamerę, aby rozpocząć analizę dłoni na backendzie.</p>
                            </div>
                        )}
                    </div>
                </div>
            </section>
            <Link className="camera-back-link" to="/"><span aria-hidden="true">←</span>Powrót do strony głównej</Link>
        </main>
    )
}
