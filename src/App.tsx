import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Documents from './pages/Documents';
import History from './pages/History';
import ScanResults from './pages/ScanResults';
import { DocumentProvider } from './context/DocumentContext';
import './App.css';

function App() {
  return (
    <DocumentProvider>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Navbar />
          <main className="pt-20 p-6">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/history" element={<History />} />
              <Route path="/scan-results/:batchId" element={<ScanResults />} />
            </Routes>
          </main>
          <Toaster position="top-right" />
        </div>
      </Router>
    </DocumentProvider>
  );
}

export default App;