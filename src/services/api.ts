import axios from 'axios';

// Tentukan base URL otomatis: dev / prod
const getApiBaseUrl = (): string => {
  const hostname = window.location.hostname;

  // Production environment
  if (hostname === 'docscan.adilabs.id' || hostname.includes('adilabs.id')) {
    console.log('Production mode: backend already has /api prefix');
    return ''; // gunakan relative path
  }

  // Development environment
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    console.log('Development mode: using localhost:8000');
    return 'http://localhost:8000';
  }

  // Default ke production
  console.log('Unknown domain, defaulting to production');
  return '';
};

const API_BASE_URL = getApiBaseUrl();

// Axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 detik timeout untuk semua request
});

// Request logging
api.interceptors.request.use(
  (config) => {
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Response logging & error handling
api.interceptors.response.use(
  (response) => {
    console.log(`[API Response] ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('[API Response Error]', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Interfaces
export interface DocumentFile { id: string; name: string; type: string; status: string; progress: number; result_id?: string; }
export interface NextGenOCRMetrics { confidence: number; layout_confidence: number; semantic_confidence: number; quality_score: number; processing_time: number; engine_used: string; }
export interface ProcessingQuality { overall_score: number; text_clarity: number; structure_preservation: number; accuracy_rating: 'excellent' | 'good' | 'fair' | 'poor'; }
export interface AIData { extracted_data: any; entities: any[]; document_type: string; confidence: number; }
export interface Batch { id: string; files: DocumentFile[]; status: string; created_at: string; total_files: number; processed_files: number; completed_at?: string; error?: string; }
export interface ScanResult { 
  id: string; batch_id: string; filename: string; document_type: string; extracted_text?: string; extracted_data: any;
  confidence?: number; confidence_score?: number; ocr_engine_used?: string; created_at: string;
  ocr_processing_time?: number; processing_time?: number;
  original_filename?: string; file_type?: string; status?: string; ai_data?: AIData; export_formats?: string[];
  nextgen_metrics?: NextGenOCRMetrics; processing_quality?: ProcessingQuality; document_structure?: any; extracted_entities?: any;
}

// API Service
export const apiService = {
  uploadDocuments: async (files: File[], documentTypes: string[]): Promise<Batch> => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    documentTypes.forEach(type => formData.append('document_types', type));
    const response = await api.post('/api/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
    return response.data;
  },

  getBatchStatus: async (batchId: string): Promise<Batch> => {
    const response = await api.get(`/api/batches/${batchId}`);
    return response.data;
  },

  getBatchResults: async (batchId: string): Promise<ScanResult[]> => {
    const response = await api.get(`/api/batches/${batchId}/results`);
    return Array.isArray(response.data) ? response.data : [];
  },

  getAllBatches: async (): Promise<Batch[]> => {
    const response = await api.get('/api/batches');
    return response.data;
  },

  getAllResults: async (): Promise<ScanResult[]> => {
    const response = await api.get('/api/results');
    return response.data;
  },

  exportResultExcel: async (resultId: string): Promise<Blob> => {
    const response = await api.get(`/api/results/${resultId}/export/excel`, { responseType: 'blob' });
    return response.data;
  },

  exportResultPdf: async (resultId: string): Promise<Blob> => {
    const response = await api.get(`/api/results/${resultId}/export/pdf`, { responseType: 'blob' });
    return response.data;
  },

  exportBatch: async (batchId: string, format: 'excel' | 'pdf'): Promise<Blob> => {
    const response = await api.get(`/api/batches/${batchId}/export/${format}`, { responseType: 'blob' });
    return response.data;
  },

  getProcessingQuality: async (resultId: string): Promise<ProcessingQuality> => {
    const response = await api.get(`/api/results/${resultId}/quality`);
    return response.data;
  },

  getOCRMetrics: async (resultId: string): Promise<NextGenOCRMetrics> => {
    const response = await api.get(`/api/results/${resultId}/metrics`);
    return response.data;
  },

  getSystemHealth: async (): Promise<any> => {
    const response = await api.get('/api/health');
    return response.data;
  },

  createWebSocketConnection: (batchId: string): WebSocket => {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = hostname.includes('adilabs.id') ? window.location.host : 'localhost:8000';
    return new WebSocket(`${protocol}//${host}/ws/batch/${batchId}`);
  },

  downloadFile: (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = filename;
    document.body.appendChild(link); link.click(); document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  saveToGoogleDrive: async (resultId: string, format: 'excel' | 'pdf') => {
    console.log(`Saving result ${resultId} to Google Drive as ${format}`);
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
};

export default api;
