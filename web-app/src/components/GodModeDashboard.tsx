"use client";
import React, { useState, useEffect } from 'react';
import { Html5QrcodeScanner } from 'html5-qrcode';
import Map, { Marker } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { FaQrcode, FaUserShield, FaMapMarkedAlt, FaBrain, FaFilePdf } from 'react-icons/fa';

export default function GodModeDashboard() {
  const [mode, setMode] = useState<'dashboard' | 'scanner'>('dashboard');
  const [scanData, setScanData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // --- SCANNER LOGIC ---
  useEffect(() => {
    if (mode === 'scanner') {
      const scanner = new Html5QrcodeScanner("reader", { fps: 10, qrbox: 250 });
      scanner.render(onScanSuccess, (e) => {});
      
      async function onScanSuccess(decodedText: string) {
        scanner.clear();
        setLoading(true);
        
        try {
          const payload = JSON.parse(decodedText);
          // Call Verification API
          const res = await axios.post('/api/verify-entry', { 
            ticketNo: payload.t, 
            token: payload.c 
          });

          if (res.data.status === 'SUCCESS') {
            setScanData(res.data.profile);
          } else {
            alert(res.data.message); // Fake/Expired QR handling
            setMode('scanner'); // Restart scan
          }
        } catch (err) {
          alert("Invalid QR Format");
        }
        setLoading(false);
      }
    }
  }, [mode]);

  // --- UI RENDER ---
  return (
    <div className="min-h-screen bg-[#0f172a] text-slate-200 p-6 font-sans">
      
      {/* Top Navigation */}
      <div className="flex justify-between items-center mb-8 bg-[#1e293b] p-4 rounded-2xl border border-slate-700 shadow-xl">
        <h1 className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500 flex items-center gap-3">
          <FaUserShield /> ERP God Mode
        </h1>
        <div className="flex gap-4">
          <button onClick={() => {setMode('dashboard'); setScanData(null);}} className={`px-4 py-2 rounded-xl font-bold flex items-center gap-2 ${mode === 'dashboard' ? 'bg-blue-600' : 'bg-slate-700 hover:bg-slate-600'}`}>
            <FaFilePdf /> Hall Tickets
          </button>
          <button onClick={() => setMode('scanner')} className={`px-4 py-2 rounded-xl font-bold flex items-center gap-2 ${mode === 'scanner' ? 'bg-green-600' : 'bg-slate-700 hover:bg-slate-600'}`}>
            <FaQrcode /> AI Gate Scanner
          </button>
        </div>
      </div>

      <AnimatePresence mode="wait">
        
        {/* DASHBOARD MODE (Bulk PDF Generation) */}
        {mode === 'dashboard' && (
          <motion.div key="dash" initial={{opacity:0}} animate={{opacity:1}} className="bg-[#1e293b] p-8 rounded-2xl border border-slate-700">
            <h2 className="text-xl mb-4">Bulk Generate Secure PDFs</h2>
            <button className="bg-purple-600 hover:bg-purple-500 px-6 py-3 rounded-xl font-bold shadow-lg shadow-purple-500/20">
              Generate All Tickets (Blockchain Verified)
            </button>
            {/* Table placeholder for tickets */}
          </motion.div>
        )}

        {/* SCANNER MODE (AI + Routing) */}
        {mode === 'scanner' && (
          <motion.div key="scan" initial={{opacity:0}} animate={{opacity:1}} className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Left: Camera Scanner / AI Profile */}
            <div className="bg-[#1e293b] p-6 rounded-2xl border border-slate-700 min-h-[500px]">
              {!scanData && !loading && (
                <>
                  <h2 className="text-center text-blue-400 font-bold mb-4">Scan Dynamic QR Code</h2>
                  <div id="reader" className="rounded-xl overflow-hidden border-2 border-dashed border-blue-500"></div>
                </>
              )}
              {loading && (
                <div className="flex flex-col items-center justify-center h-full">
                  <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                  <p className="mt-4 text-blue-400 animate-pulse">Verifying Blockchain & AI...</p>
                </div>
              )}
              {scanData && (
                <motion.div initial={{scale:0.9, opacity:0}} animate={{scale:1, opacity:1}}>
                  <div className="bg-green-500/20 text-green-400 p-3 rounded-xl mb-6 flex items-center gap-2">
                    <FaUserShield /> Access Granted - Identity Verified
                  </div>
                  <div className="flex gap-4">
                    <img src={scanData.photo} className="w-24 h-24 rounded-xl object-cover border-2 border-blue-500" />
                    <div>
                      <h3 className="text-2xl font-bold">{scanData.name}</h3>
                      <p className="text-slate-400">Attendance: {scanData.attendance}%</p>
                      <p className="text-green-400 text-sm font-bold mt-1">Fee: {scanData.feeStatus}</p>
                    </div>
                  </div>
                  <button onClick={() => setScanData(null)} className="mt-6 w-full bg-slate-700 py-2 rounded-xl">Scan Next</button>
                </motion.div>
              )}
            </div>

            {/* Right: Mapbox 3D Routing */}
            <div className="bg-[#1e293b] p-6 rounded-2xl border border-slate-700 min-h-[500px] flex flex-col">
              <h2 className="text-lg font-bold flex items-center gap-2 mb-4"><FaMapMarkedAlt className="text-orange-400"/> Exam Routing</h2>
              {scanData ? (
                <div className="flex-1 rounded-xl overflow-hidden relative">
                  <Map
                    initialViewState={{ longitude: scanData.route.lng, latitude: scanData.route.lat, zoom: 16, pitch: 60 }}
                    mapStyle="mapbox://styles/mapbox/dark-v11"
                    mapboxAccessToken="YOUR_MAPBOX_TOKEN"
                  >
                    <Marker longitude={scanData.route.lng} latitude={scanData.route.lat} color="red" />
                  </Map>
                  <div className="absolute bottom-4 left-4 right-4 bg-slate-900/90 p-4 rounded-xl border border-slate-600">
                    <p className="font-bold text-white text-lg">{scanData.route.room} - {scanData.route.seat}</p>
                    <p className="text-sm text-slate-400">Proceed to 2nd Floor, Block B</p>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center border-2 border-dashed border-slate-600 rounded-xl">
                  <p className="text-slate-500">Scan ticket to load route...</p>
                </div>
              )}
            </div>

          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
