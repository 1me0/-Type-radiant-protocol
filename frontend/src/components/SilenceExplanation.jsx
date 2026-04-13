import React, { useState, useCallback } from 'react';

/**
 * Normalize raw distance to 0–1 using a sigmoid function.
 * @param {number} distance - raw distance (≥0)
 * @param {number} steepness - steepness of sigmoid (default 1)
 * @returns {number} normalized uncertainty (0–1)
 */
const normalizeUncertainty = (distance, steepness = 1.0) => {
    // sigmoid: 1 / (1 + exp(-steepness * (distance - threshold)))
    // We assume distance 0 → 0, large distance → 1.
    // Simple logistic: 1 - exp(-distance) works for distance >=0, giving 0 at 0, 1 at ∞.
    return 1 - Math.exp(-steepness * distance);
};

/**
 * Helper to cap distance at a max and then normalize linearly.
 * Alternative: use if you know maximum possible distance.
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
 *   log: array of structured log entries – each entry: { timestamp, message, type, icon? }.
 */
const SilenceExplanation = ({ 
    uncertaintyRaw = 0.5, 
    normalizeMethod = 'sigmoid', 
    maxDistance = 10.0,
    reason = "", 
    testing = null, 
    log = [] 
}) => {
    const [expanded, setExpanded] = useState(false);

    // Normalize uncertainty
    let uncertainty = 0.5;
    if (normalizeMethod === 'sigmoid') {
        uncertainty = normalizeUncertainty(uncertaintyRaw, 1.0);
    } else {
        uncertainty = normalizeUncertaintyByMax(uncertaintyRaw, maxDistance);
    }
    // Clamp to [0,1] just in case
    uncertainty = Math.min(1.0, Math.max(0.0, uncertainty));

    const getUncertaintyColor = (unc) => {
        if (unc < 0.3) return '#2e7d32'; // green
        if (unc < 0.6) return '#f9a825'; // yellow
        return '#c62828'; // red
    };

    const uncertaintyPercent = (uncertainty * 100).toFixed(1);

    // Toggle handler with keyboard support
    const handleToggle = useCallback((e) => {
        if (e.type === 'keydown' && !(e.key === 'Enter' || e.key === ' ')) return;
        e.preventDefault();
        setExpanded(prev => !prev);
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

    return (
        <div className="silence-explanation" style={{
            background: '#1e2a3a',
            borderRadius: '12px',
            padding: '12px 16px',
            margin: '10px 0',
            color: '#e2e8f0',
            fontFamily: 'system-ui, sans-serif',
            fontSize: '0.9rem',
            borderLeft: `4px solid ${getUncertaintyColor(uncertainty)}`
        }}>
            <div 
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                onClick={handleToggle}
                onKeyDown={handleToggle}
                role="button"
                tabIndex={0}
                aria-expanded={expanded}
                aria-label="Toggle silence explanation details"
            >
                <div>
                    <span style={{ fontWeight: 'bold' }}>🔇 Silence mode</span>
                    <span style={{ marginLeft: '12px', fontSize: '0.8rem', opacity: 0.7 }}>Why no response?</span>
                </div>
                <div aria-hidden="true">{expanded ? '▲' : '▼'}</div>
            </div>

            <div style={{ marginTop: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                    <div>
                        <span style={{ opacity: 0.7 }}>Uncertainty:</span>
                        <span style={{ marginLeft: '6px', fontWeight: 'bold', color: getUncertaintyColor(uncertainty) }}>
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
                {/* Optional: visual uncertainty bar */}
                <div style={{ marginTop: '6px', height: '4px', background: '#3a4a5a', borderRadius: '2px' }}>
                    <div style={{ width: `${uncertaintyPercent}%`, height: '100%', background: getUncertaintyColor(uncertainty), borderRadius: '2px' }} />
                </div>
            </div>

            {expanded && (
                <div style={{ marginTop: '12px', borderTop: '1px solid #3a4a5a', paddingTop: '10px' }}>
                    {testing && (
                        <div style={{ marginBottom: '12px' }}>
                            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>🧪 Testing</div>
                            <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>
                                Direction: {testing.direction ? testing.direction.map(v => v.toFixed(2)).join(', ') : '—'}<br />
                                Progress: {testing.progress || 'searching boundary...'}<br />
                                Weight: {testing.weight?.toFixed(2) || '—'}
                            </div>
                        </div>
                    )}

                    {log.length > 0 && (
                        <div>
                            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>📋 Recent tests</div>
                            <div style={{ fontSize: '0.7rem', maxHeight: '150px', overflowY: 'auto', background: '#0f1a24', padding: '6px', borderRadius: '6px' }}>
                                {log.slice(-5).map((entry, idx) => (
                                    <div key={idx} style={{ marginBottom: '4px', fontFamily: 'monospace' }}>
                                        <span style={{ opacity: 0.6 }}>{entry.timestamp || ''}</span>
                                        {entry.type && <span style={{ marginLeft: '6px' }}>{getLogIcon(entry.type)}</span>}
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

export default SilenceExplanation;
