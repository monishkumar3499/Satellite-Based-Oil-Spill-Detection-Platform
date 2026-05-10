import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, ChevronRight, Download, Compass, Share, ChevronRight as ChevronRightIcon, FileText, AlertTriangle, CheckCircle, MapPin, Loader, Info, Thermometer, Wind, Target, Eye, Navigation } from 'lucide-react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './App.css';

// Leaflet fix
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const API_BASE = "http://127.0.0.1:5000";

function MapClickHandler({ onLocationSelect }) {
  useMapEvents({ click: (e) => onLocationSelect(e.latlng.lat, e.latlng.lng) });
  return null;
}

const LOADING_STEPS = [
  "Synchronizing Satellite Mission...",
  "Acquiring C-band SAR Imagery...",
  "Analyzing Backscatter Morphology...",
  "Running Deep Inference...",
  "Authoring Research Narrative...",
  "Finalizing Tactical Report..."
];

function LoadingArtifact() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => {
      setStep((s) => (s + 1) % LOADING_STEPS.length);
    }, 1500);
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="loading-artifact">
      <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }} className="pulse-claude" />
      <div style={{ color: 'var(--text-primary)', fontWeight: '600', marginBottom: '8px' }}>Generating Intelligence...</div>
      <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{LOADING_STEPS[step]}</div>
    </div>
  );
}

const FormattedParagraph = ({ text, fontSize = '0.9rem' }) => {
  if (!text) return null;
  return (
    <div className="narrative-output" style={{ fontSize, lineHeight: '1.6', textAlign: 'justify' }}>
      {renderBold(text)}
    </div>
  );
};

const renderBold = (text) => {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} style={{ fontWeight: '700' }}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
};

function App() {
  const [selectedPos, setSelectedPos] = useState({ lat: 18.1634, lng: 65.6021 });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isMinimized, setIsMinimized] = useState(true);
  
  const [activeJobId, setActiveJobId] = useState(null);
  const [initialJobData, setInitialJobData] = useState(null);
  const pollTimerRef = useRef(null);

  // Authoritative Polling Effect
  useEffect(() => {
    if (!activeJobId) return;

    let isEffectActive = true;

    const poll = async () => {
      if (!isEffectActive) return;

      try {
        const response = await fetch(`${API_BASE}/research_status/${activeJobId}`);
        const data = await response.json();

        if (!isEffectActive) return;

        if (data.status === 'ready') {
          setResult({ ...initialJobData, research: data.data });
          setLoading(false);
          setActiveJobId(null); // Stop polling
        } else if (data.status === 'error') {
          setError("Research Intelligence Synthesis Failed");
          setLoading(false);
          setActiveJobId(null); // Stop polling
        } else {
          // Continue polling after 3 seconds
          pollTimerRef.current = setTimeout(poll, 3000);
        }
      } catch (err) {
        if (isEffectActive) {
          setLoading(false);
          setActiveJobId(null);
        }
      }
    };

    pollTimerRef.current = setTimeout(poll, 3000);

    return () => {
      isEffectActive = false;
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    };
  }, [activeJobId, initialJobData]);

  const analyzeLocation = async (lat, lng) => {
    // Clear all existing activity
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    setActiveJobId(null);
    
    setSelectedPos({ lat, lng });
    setLoading(true);
    setResult(null);
    setError(null);
    setIsMinimized(false);

    try {
      const response = await fetch(`${API_BASE}/analyze_location`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lon: lng }),
      });
      const data = await response.json();
      
      if (response.ok) {
        if (data.research_job_id) {
          setInitialJobData(data);
          setActiveJobId(data.research_job_id);
        } else {
          setResult(data);
          setLoading(false);
        }
      } else {
        setError(data.error || "Tactical Analysis Failed");
        setLoading(false);
      }
    } catch (err) {
      setError("Network Failure connecting to analysis engine.");
      setLoading(false);
    }
  };

  return (
    <div className="main-layout">
      <section className="map-section no-print">
        <MapContainer center={[selectedPos.lat, selectedPos.lng]} zoom={5} className="full-map" zoomControl={false}>
          <TileLayer attribution='&copy; OpenStreetMap' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <Marker position={[selectedPos.lat, selectedPos.lng]} />
          <MapClickHandler onLocationSelect={analyzeLocation} />
        </MapContainer>
        <div className="map-timeline">
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
            {['1988', '1996', '2004', '2012', '2020', '2026'].map(y => <span key={y}>{y}</span>)}
          </div>
          <div style={{ width: '100%', height: '1px', background: 'var(--claude-border)', marginTop: '8px', position: 'relative' }}>
            <div style={{ position: 'absolute', right: '0', top: '-2px', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--claude-accent)' }} />
          </div>
        </div>
      </section>

      <AnimatePresence>
        {!isMinimized ? (
          <motion.aside 
            key="full-panel"
            initial={{ x: "100%", opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: "100%", opacity: 0 }}
            transition={{ type: "tween", duration: 0.25, ease: "easeInOut" }}
            className="artifact-panel"
          >
            <header className="artifact-header no-print">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button className="minimize-btn" onClick={() => setIsMinimized(true)}><ChevronRightIcon size={18} /></button>
                <div className="artifact-header-title">Satellite Intelligence Brief</div>
              </div>
            </header>

            <main className="artifact-content">
              {loading ? <LoadingArtifact /> : error ? (
                <div className="loading-artifact" style={{ color: 'var(--danger)' }}>
                  <AlertTriangle size={32} style={{ marginBottom: '16px' }} />
                  <div>{error}</div>
                  <button className="claude-btn" style={{ marginTop: '20px' }} onClick={() => analyzeLocation(selectedPos.lat, selectedPos.lng)}>Retry Analysis</button>
                </div>
              ) : result ? (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  
                  {/* --- PREMIUM FULL-WIDTH AUDIT REPORT --- */}
                  <div className="print-only audit-report">
                    <header className="audit-header">
                      <div className="audit-top-bar">
                        <span>{new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} | {new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</span>
                        <span>Oil Spill Detection Platform</span>
                      </div>
                      <h1 className="audit-title">TECHNICAL SURVEILLANCE AUDIT</h1>
                      <div className="audit-subtitle">{renderBold(result.research.location_name)} ({selectedPos.lat.toFixed(3)}°N, {selectedPos.lng.toFixed(3)}°E)</div>
                    </header>

                    <div className="audit-grid">
                      <div className="audit-col-left">
                        <div className="audit-image-container">
                          <div className="north-arrow" style={{ position: 'absolute', top: '10px', left: '10px', background: 'rgba(255,255,255,0.8)', padding: '4px', borderRadius: '4px', display: 'flex', flexDirection: 'column', alignItems: 'center', fontSize: '0.6rem', color: '#002d72', fontWeight: '800' }}>
                            <Navigation size={10} style={{ transform: 'rotate(-45deg)' }} /><span>N</span>
                          </div>
                          <img src={`data:image/jpeg;base64,${result.sar_image_b64}`} className="audit-sar-image" alt="SAR" />
                        </div>
                      </div>
                      <div className="audit-col-right">
                        {[
                          { icon: <Target size={14} />, label: 'STATUS', value: result.results.final_label.toUpperCase().includes('NO') ? 'NOMINAL' : 'POTENTIAL', urgent: !result.results.final_label.includes('No') },
                          { icon: <Thermometer size={14} />, label: 'TEMPERATURE', value: `${result.results.ocean_context.temperature_c} °C` },
                          { icon: <Wind size={14} />, label: 'WIND SPEED', value: `${result.results.ocean_context.wind_speed_ms} m s⁻¹` },
                          { icon: <Shield size={14} />, label: 'CONFIDENCE', value: `${result.results.adjusted_confidence}%` },
                          { icon: <Compass size={14} />, label: 'COORDINATES', value: `${selectedPos.lat.toFixed(3)}°N, ${selectedPos.lng.toFixed(3)}°E` }
                        ].map((m, i) => (
                          <div key={i} className="audit-metric">
                            <div className="audit-icon-circle">{m.icon}</div>
                            <div className="audit-metric-label">{m.label}</div>
                            <div className={`audit-metric-value ${m.urgent ? 'urgent' : ''}`}>{m.value}</div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <section className="audit-section">
                      <div className="audit-section-header">
                        <div className="audit-icon-square"><Eye size={14} /></div>
                        <span>INTELLIGENCE FINDINGS</span>
                      </div>
                      <div className="audit-findings">
                        <FormattedParagraph text={result.research.research_summary} fontSize="0.85rem" />
                      </div>
                    </section>

                    <section className="audit-section">
                      <div className="audit-section-header">
                        <div className="audit-icon-square"><Thermometer size={14} /></div>
                        <span>SEA SURFACE TEMPERATURE (SST) TRENDS</span>
                      </div>
                      <div className="graph-container" style={{ height: '150px', width: '100%', position: 'relative' }}>
                        <AreaChart width={650} height={150} data={result.results.ocean_context.sst_history} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" vertical={false} />
                          <XAxis dataKey="day" hide />
                          <YAxis stroke="#666" fontSize={10} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                          <Area type="monotone" dataKey="temp" stroke="#002d72" fill="rgba(0, 45, 114, 0.05)" strokeWidth={2} animationDuration={0} />
                        </AreaChart>
                      </div>
                    </section>

                    <footer className="audit-footer">
                      <div className="audit-disclaimer">
                        <Shield size={16} color="#002d72" />
                        <span><strong>DISCLAIMER:</strong> This report is generated by an automated oil spill detection system using satellite data and AI analysis. Results should be validated with in-situ observations before operational response.</span>
                      </div>
                    </footer>
                  </div>

                  {/* --- DASHBOARD VIEW (NO PRINT) --- */}
                  <div className="no-print">
                    <div style={{ marginBottom: '24px', padding: '12px 16px', borderRadius: '8px', background: result.results.final_label.includes('No') ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)', border: `1px solid ${result.results.final_label.includes('No') ? 'var(--success)' : 'var(--danger)'}`, display: 'flex', alignItems: 'center', gap: '12px' }}>
                      {result.results.final_label.includes('No') ? <CheckCircle size={20} color="var(--success)" /> : <AlertTriangle size={20} color="var(--danger)" />}
                      <div>
                        <div style={{ fontSize: '0.6rem', fontWeight: '800', textTransform: 'uppercase', color: result.results.final_label.includes('No') ? 'var(--success)' : 'var(--danger)' }}>Command Action Status</div>
                        <div style={{ fontSize: '0.9rem', fontWeight: '700' }}>{result.results.final_label.includes('No') ? 'NO IMMEDIATE ACTION REQUIRED' : 'INITIATE SITE INVESTIGATION'}</div>
                      </div>
                    </div>

                    <div className="claude-section">
                      <div className="claude-label">Intelligence Assessment</div>
                      <h1 className="claude-h1">{result.results.final_label}</h1>
                      <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <div className="tactical-metric"><MapPin size={14} color="var(--claude-accent)" /><span>LOCATION:</span><strong>{renderBold(result.research.location_name)}</strong></div>
                        <div className="tactical-metric"><Compass size={14} color="var(--claude-accent)" /><span>COORDINATES:</span><strong>{selectedPos.lat.toFixed(4)}° N, {selectedPos.lng.toFixed(4)}° E</strong></div>
                        <div className="tactical-metric"><Shield size={14} color="var(--claude-accent)" /><span>FUSION CONFIDENCE:</span><strong>{result.results.adjusted_confidence}%</strong></div>
                      </div>
                    </div>

                    {result.sar_image_b64 && (
                      <div className="claude-section">
                        <div className="claude-label">Microwave Backscatter (Sentinel-1)</div>
                        <img src={`data:image/jpeg;base64,${result.sar_image_b64}`} className="sar-artifact-img" alt="SAR" />
                      </div>
                    )}

                    <div className="claude-section">
                      <div className="claude-label">Research Narrative</div>
                      <div className="claude-text" style={{ padding: '20px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px' }}>
                        <FormattedParagraph text={result.research.research_summary} fontSize="0.85rem" />
                      </div>
                    </div>

                    <div className="claude-section">
                      <div className="claude-label">SST Thermal Baseline (°C)</div>
                      <div style={{ height: '140px', marginTop: '16px', background: 'rgba(0,0,0,0.15)', padding: '12px', borderRadius: '8px' }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={result.results.ocean_context.sst_history}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                            <XAxis dataKey="day" stroke="var(--text-muted)" fontSize={10} tickLine={false} axisLine={false} />
                            <YAxis stroke="var(--text-muted)" fontSize={10} tickLine={false} axisLine={false} domain={['auto', 'auto']} unit="°C" />
                            <Tooltip contentStyle={{ background: '#1d1d1d', border: '1px solid #333', borderRadius: '4px', fontSize: '10px' }} />
                            <Area type="monotone" dataKey="temp" stroke="var(--claude-accent)" fill="rgba(217, 119, 87, 0.1)" strokeWidth={2} />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>

                </motion.div>
              ) : (
                <div className="loading-artifact" style={{ textAlign: 'center', marginTop: '40px' }}>
                  <Info size={40} color="var(--claude-border)" style={{ marginBottom: '16px' }} />
                  <div className="claude-text" style={{ color: 'var(--text-muted)' }}>Select a location to generate a unified intelligence brief.</div>
                </div>
              )}
            </main>

            <footer className="no-print" style={{ padding: '24px', borderTop: '1px solid var(--claude-border)', background: '#191919' }}>
              <button className="claude-btn" onClick={() => window.print()} style={{ width: '100%', justifyContent: 'center', height: '48px' }}>
                <Download size={18} /> Download Technical Audit
              </button>
            </footer>
          </motion.aside>
        ) : (
          <motion.div key="minimized-tab" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="minimized-tab" onClick={() => setIsMinimized(false)}>
            <FileText size={18} /><span>INTELLIGENCE BRIEF</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
