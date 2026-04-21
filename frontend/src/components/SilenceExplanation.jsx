// frontend/src/components/SilenceExplanation.jsx
// Radiant Protocol – Silence Explanation Component with Audio Feedback and Live WebSocket Logs

import React, { useState, useCallback, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';

/**
 * Normalize raw distance to 0–1 using a sigmoid function.
 * @param {number} distance - raw distance (≥0)
 * @param {number} steepness - steepness of sigmoid (default 1)
 * @returns {number} normalized uncertainty (0–1)
 */
const normalizeUncertainty = (distance, steepness = 1.0) => {
    return 1 - Math.exp(-steepness * distance);
};

/**
 * Helper to cap distance at a max and then normalize linearly.
 */
const normalizeUncertaintyByMax = (distance, maxDistance = 10.0) => {
    return Math.min(1.0, Math.max(0.0, distance / maxDistance));
};

/**
 * SilenceExplanation component – shows why the system is silent.
 *
 * Props:
 *   uncertaintyRaw: number – raw distance (≥0) from the falsification system.
 *   normalizeMethod: 'sigmoid' or 'max' – method to convert to 0–1 (default 'sigmoid').
 *   maxDistance: number – used with 'max' method (default 10.0).
 *   reason: string – explanation for silence.
 *   testing: object – details of what is being tested (direction, progress, weight).
 *   wsUrl: string – WebSocket URL for real‑time logs (optional).
 */
const SilenceExplanation = ({
    uncertaintyRaw = 0.5,
    normalizeMethod = 'sigmoid',
    maxDistance = 10.0,
    reason = '',
    testing = null,
    wsUrl = null,
}) => {
    const [expanded, setExpanded] = useState(false);
    const [log, setLog] = useState([]); // internal state for real‑time logs
    const audioContextRef = useRef(null);
    const oscillatorRef = useRef(null);
    const gainNodeRef = useRef(null);
    const wsRef = useRef(null);

    // Normalize uncertainty
    let uncertainty = 0.5;
    if (normalizeMethod === 'sigmoid') {
        uncertainty = normalizeUncertainty(uncertaintyRaw, 1.0);
    } else {
        uncertainty = normalizeUncertaintyByMax(uncertaintyRaw, maxDistance);
    }
    uncertainty = Math.min(1.0, Math.max(0.0, uncertainty));

    const getUncertaintyColor = (unc) => {
        if (unc < 0.3) return '#2e7d32';
        if (unc < 0.6) return '#f9a825';
        return '#c62828';
    };

    const uncertaintyPercent = (uncertainty * 100).toFixed(1);

    // Toggle handler with keyboard support
    const handleToggle = useCallback((e) => {
        if (e.type === 'keydown' && !(e.key === 'Enter' || e.key === ' ')) return;
        e.preventDefault();
        setExpanded((prev) => !prev);
    }, []);

    // Helper to get icon for log type
    const getLogIcon = (type) => {
        switch (type) {
            case 'success': return '✅';
            case 'warning': return '⚠️';
            case 'error': return '❌';
            default: return 'ℹ️';
        }
    };

    // Audio feedback (low humming pulse) when expanded
    useEffect(() => {
        if (!expanded) {
            // Stop any ongoing sound
            if (oscillatorRef.current) {
                oscillatorRef.current.stop();
                oscillatorRef.current.disconnect();
                oscillatorRef.current = null;
            }
            if (audioContextRef.current) {
                audioContextRef.current.close();
                audioContextRef.current = null;
            }
            return;
        }

        // Initialize Web Audio API
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            const ctx = new AudioContext();
            audioContextRef.current = ctx;

            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.value = 70; // low hum
            gain.gain.value = 0.05; // very quiet
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            // Create a pulse effect: gain goes up and down slowly
            let time = 0;
            const pulseInterval = setInterval(() => {
                if (!audioContextRef.current) return;
                const now = audioContextRef.current.currentTime;
                // create a short envelope
                const envelope = (t) => Math.sin(t * Math.PI * 2) * 0.5 + 0.5;
                // we'll just modulate gain slightly
                gain.gain.linearRampToValueAtTime(0.1 + envelope(time) * 0.05, now + 0.05);
                time += 0.5;
            }, 500);
            oscillatorRef.current = osc;
            gainNodeRef.current = gain;
            // Cleanup on unmount or collapse
            return () => {
                clearInterval(pulseInterval);
                if (oscillatorRef.current) {
                    oscillatorRef.current.stop();
                    oscillatorRef.current.disconnect();
                }
                if (audioContextRef.current) {
                    audioContextRef.current.close();
                }
            };
        } catch (e) {
            console.warn("Web Audio API not supported or user interaction required");
        }
    }, [expanded]);

    // WebSocket connection for real‑time logs
    useEffect(() => {
        if (!wsUrl) return;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('SilenceExplanation WebSocket connected');
        };
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                // Expect data to have fields: timestamp, type, message
                const newEntry = {
                    timestamp: data.timestamp || new Date().toLocaleTimeString(),
                    type: data.type || 'info',
                    message: data.message || 'Test update',
                };
                setLog((prev) => [...prev.slice(-49), newEntry]); // keep last 50 entries
            } catch (err) {
                console.warn('Failed to parse WebSocket message', err);
            }
        };
        ws.onerror = (err) => {
            console.error('WebSocket error', err);
        };
        ws.onclose = () => {
            console.log('WebSocket disconnected');
        };
        return () => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.close();
            }
        };
    }, [wsUrl]);

    // Helper to add log entries manually (if needed via props)
    useEffect(() => {
        // If external log prop is provided, merge it (initial log)
        if (log.length === 0 && window.initialLog) {
            setLog(window.initialLog);
        }
    }, []);

    return (
        <div
            className="silence-explanation"
            style={{
                background: '#1e2a3a',
                borderRadius: '12px',
                padding: '12px 16px',
                margin: '10px 0',
                color: '#e2e8f0',
                fontFamily: 'system-ui, sans-serif',
                fontSize: '0.9rem',
                borderLeft: `4px solid ${getUncertaintyColor(uncertainty)}`,
            }}
        >
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                }}
                onClick={handleToggle}
                onKeyDown={handleToggle}
                role="button"
                tabIndex={0}
                aria-expanded={expanded}
                aria-label="Toggle silence explanation details"
            >
                <div>
                    <span style={{ fontWeight: 'bold' }}>🔇 Silence mode</span>
                    <span style={{ marginLeft: '12px', fontSize: '0.8rem', opacity: 0.7 }}>
                        Why no response?
                    </span>
                </div>
                <div aria-hidden="true">{expanded ? '▲' : '▼'}</div>
            </div>

            <div style={{ marginTop: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                    <div>
                        <span style={{ opacity: 0.7 }}>Uncertainty:</span>
                        <span
                            style={{
                                marginLeft: '6px',
                                fontWeight: 'bold',
                                color: getUncertaintyColor(uncertainty),
                            }}
                        >
                            {uncertaintyPercent}%
                        </span>
                    </div>
                    {reason && (
                        <div>
                            <span style={{ opacity: 0.7 }}>Reason:</span>
                            <span style={{ marginLeft: '6px' }}>{reason}</span>
                        </div>
                    )}
                </div>
                {/* visual uncertainty bar */}
                <div
                    style={{
                        marginTop: '6px',
                        height: '4px',
                        background: '#3a4a5a',
                        borderRadius: '2px',
                    }}
                >
                    <div
                        style={{
                            width: `${uncertaintyPercent}%`,
                            height: '100%',
                            background: getUncertaintyColor(uncertainty),
                            borderRadius: '2px',
                        }}
                    />
                </div>
            </div>

            {expanded && (
                <div
                    style={{
                        marginTop: '12px',
                        borderTop: '1px solid #3a4a5a',
                        paddingTop: '10px',
                    }}
                >
                    {testing && (
                        <div style={{ marginBottom: '12px' }}>
                            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>🧪 Testing</div>
                            <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>
                                Direction:{' '}
                                {testing.direction
                                    ? testing.direction.map((v) => v.toFixed(2)).join(', ')
                                    : '—'}
                                <br />
                                Progress: {testing.progress || 'searching boundary...'}
                                <br />
                                Weight: {testing.weight?.toFixed(2) || '—'}
                            </div>
                        </div>
                    )}

                    {(log.length > 0 || (wsUrl && log.length > 0)) && (
                        <div>
                            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>📋 Recent tests</div>
                            <div
                                style={{
                                    fontSize: '0.7rem',
                                    maxHeight: '150px',
                                    overflowY: 'auto',
                                    background: '#0f1a24',
                                    padding: '6px',
                                    borderRadius: '6px',
                                }}
                            >
                                {log.slice(-5).map((entry, idx) => (
                                    <div key={idx} style={{ marginBottom: '4px', fontFamily: 'monospace' }}>
                                        <span style={{ opacity: 0.6 }}>{entry.timestamp || ''}</span>
                                        {entry.type && (
                                            <span style={{ marginLeft: '6px' }}>{getLogIcon(entry.type)}</span>
                                        )}
                                        <span style={{ marginLeft: '6px' }}>{entry.message}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

SilenceExplanation.propTypes = {
    uncertaintyRaw: PropTypes.number,
    normalizeMethod: PropTypes.oneOf(['sigmoid', 'max']),
    maxDistance: PropTypes.number,
    reason: PropTypes.string,
    testing: PropTypes.shape({
        direction: PropTypes.arrayOf(PropTypes.number),
        progress: PropTypes.string,
        weight: PropTypes.number,
    }),
    wsUrl: PropTypes.string,
};

SilenceExplanation.defaultProps = {
    uncertaintyRaw: 0.5,
    normalizeMethod: 'sigmoid',
    maxDistance: 10.0,
    reason: '',
    testing: null,
    wsUrl: null,
};

export default SilenceExplanation;
