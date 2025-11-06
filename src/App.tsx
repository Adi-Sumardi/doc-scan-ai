import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Documents from './pages/Documents';
import History from './pages/History';
import ScanResults from './pages/ScanResults';
import ResultEditor from './pages/ResultEditor';
import Login from './pages/Login';
import Register from './pages/Register';
import AdminDashboard from './pages/AdminDashboard';
import UserActivities from './pages/UserActivities';
import ExcelReconciliation from './pages/ExcelReconciliation';
import PPNReconciliation from './pages/PPNReconciliation';
import PPNProjectDetail from './pages/PPNProjectDetail';
import { DocumentProvider } from './context/DocumentContext';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';
import './App.css';

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <DocumentProvider>
          <Router>
            <div className="min-h-screen bg-gray-50">
              <Navbar />
              <main className="pt-20 p-6">
                <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/upload" element={
                  <ProtectedRoute>
                    <Upload />
                  </ProtectedRoute>
                } />
                <Route path="/documents" element={
                  <ProtectedRoute>
                    <Documents />
                  </ProtectedRoute>
                } />
                <Route path="/history" element={
                  <ProtectedRoute>
                    <History />
                  </ProtectedRoute>
                } />
                <Route path="/scan-results/:batchId" element={
                  <ProtectedRoute>
                    <ScanResults />
                  </ProtectedRoute>
                } />
                <Route path="/results/:id/editor" element={
                  <ProtectedRoute>
                    <ResultEditor />
                  </ProtectedRoute>
                } />
                <Route path="/admin" element={
                  <ProtectedRoute>
                    <AdminDashboard />
                  </ProtectedRoute>
                } />
                <Route path="/admin/user-activities/:userId" element={
                  <ProtectedRoute>
                    <UserActivities />
                  </ProtectedRoute>
                } />
                <Route path="/reconciliation" element={
                  <ProtectedRoute>
                    <ExcelReconciliation />
                  </ProtectedRoute>
                } />
                <Route path="/excel-reconciliation" element={
                  <ProtectedRoute>
                    <ExcelReconciliation />
                  </ProtectedRoute>
                } />
                <Route path="/ppn-reconciliation" element={
                  <ProtectedRoute>
                    <PPNReconciliation />
                  </ProtectedRoute>
                } />
                <Route path="/ppn-reconciliation/:projectId" element={
                  <ProtectedRoute>
                    <PPNProjectDetail />
                  </ProtectedRoute>
                } />
              </Routes>
            </main>
            <Toaster position="top-right" />
          </div>
        </Router>
      </DocumentProvider>
    </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;