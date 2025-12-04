import axios from 'axios';
import { getApiBaseUrl } from '../utils/config';

const API_BASE_URL = getApiBaseUrl();

// Axios instance
// NOTE: Default timeout is for general API calls. Individual endpoints can override this.
// - Status polling: 10 minutes (processing can take long, but API call returns instantly)
// - Uploads: Default 5 minutes is fine (upload itself is quick)
// - Exports: Default 5 minutes should be sufficient
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes default timeout
});

// Request logging and JWT token interceptor
api.interceptors.request.use(
  (config) => {
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);

    // Add JWT token to requests if available (check both 'token' and 'access_token')
    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Response logging & error handling with 401 auto-logout
api.interceptors.response.use(
  (response) => {
    console.log(`[API Response] ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('[API Response Error]', error.response?.data || error.message);

    // Handle 401 Unauthorized - auto logout and cleanup
    if (error.response?.status === 401) {
      console.warn('🔒 401 Unauthorized - Token expired or invalid');

      // Clear all auth-related data from localStorage
      localStorage.removeItem('token');
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');

      // Clear sessionStorage as well
      sessionStorage.clear();

      // Redirect to login page if not already there
      if (!window.location.pathname.includes('/login') &&
          !window.location.pathname.includes('/register')) {
        console.log('🔄 Redirecting to login page...');

        // Save current path to redirect back after login
        const currentPath = window.location.pathname + window.location.search;
        if (currentPath !== '/' && currentPath !== '/login') {
          localStorage.setItem('redirectAfterLogin', currentPath);
        }

        // Redirect with a small delay to allow cleanup
        setTimeout(() => {
          window.location.href = '/login';
        }, 100);
      }
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      console.warn('🚫 403 Forbidden - Access denied');
    }

    // Handle network errors
    if (error.message === 'Network Error') {
      console.error('❌ Network Error - Check if backend is running');
      error.message = 'Cannot connect to server. Please check your connection.';
    }

    // Handle timeout errors
    if (error.code === 'ECONNABORTED') {
      console.error('⏱️ Request Timeout');
      error.message = 'Request timeout. Please try again.';
    }

    return Promise.reject(error);
  }
);

// Interfaces
export interface DocumentFile { id: string; name: string; type: string; status: string; progress: number; result_id?: string; }
export interface NextGenOCRMetrics { confidence: number; layout_confidence: number; semantic_confidence: number; quality_score: number; processing_time: number; engine_used: string; }
export interface ProcessingQuality { overall_score: number; text_clarity: number; structure_preservation: number; accuracy_rating: 'excellent' | 'good' | 'fair' | 'poor'; }
export interface AIData { extracted_data: any; entities: any[]; document_type: string; confidence: number; }
export interface Batch {
  id: string;
  files: DocumentFile[];
  status: 'pending' | 'processing' | 'completed' | 'error';
  created_at: string;
  total_files: number;
  processed_files: number;
  completed_at?: string;
  error?: string;
  // New fields for improved animation
  failed_files?: number;
  current_file?: string;
  eta_seconds?: number;
  error_message?: string;
  results?: any[];  // Per-file progress data
}
export interface ScanResult {
  id: string; batch_id: string; filename: string; document_type: string; extracted_text?: string; extracted_data: any;
  confidence?: number; confidence_score?: number; ocr_engine_used?: string; created_at: string;
  ocr_processing_time?: number; processing_time?: number;
  original_filename?: string; file_type?: string; status?: string; ai_data?: AIData; export_formats?: string[];
  nextgen_metrics?: NextGenOCRMetrics; processing_quality?: ProcessingQuality; document_structure?: any; extracted_entities?: any;
  raw_ocr_result?: any; // Raw OCR JSON from Google Document AI
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
    // Status polling should have very long timeout since backend processing can take 10+ minutes
    // The actual API call returns instantly, but we need to wait for processing to complete
    const response = await api.get(`/api/batches/${batchId}`, { timeout: 600000 }); // 10 minutes
    return response.data;
  },

  getBatchResults: async (batchId: string): Promise<ScanResult[]> => {
    const response = await api.get(`/api/batches/${batchId}/results`);
    return Array.isArray(response.data) ? response.data : [];
  },

  getAllBatches: async (limit?: number, offset?: number): Promise<Batch[]> => {
    const params = new URLSearchParams();
    if (limit !== undefined) params.append('limit', limit.toString());
    if (offset !== undefined) params.append('offset', offset.toString());
    // ✅ PERFORMANCE FIX: Don't include files in list view - massive over-fetching!
    // Files are only needed when viewing batch details (getBatchStatus has include_files=true)
    // This reduces initial load from 150+ records to just 15 batches
    // params.append('include_files', 'true');  // ❌ REMOVED - causes slow loading

    const response = await api.get(`/api/batches?${params.toString()}`);
    return response.data;
  },

  getAllResults: async (batchIds?: string[]): Promise<ScanResult[]> => {
    const params = new URLSearchParams();
    // ✅ PERFORMANCE FIX: Only load results for specific batches
    if (batchIds && batchIds.length > 0) {
      params.append('batch_ids', batchIds.join(','));
    }
    const response = await api.get(`/api/results?${params.toString()}`);
    return response.data;
  },

  deleteBatch: async (batchId: string): Promise<void> => {
    await api.delete(`/api/batches/${batchId}`);
  },

  getResultById: async (resultId: string): Promise<ScanResult> => {
    const response = await api.get(`/api/results/${resultId}`);
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

  getResultFileBlob: async (resultId: string): Promise<Blob> => {
    const response = await api.get(`/api/results/${resultId}/file`, { responseType: 'blob' });
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
  },

  updateResult: async (resultId: string, updatedData: any): Promise<any> => {
    const response = await api.patch(`/api/results/${resultId}`, updatedData);
    return response.data;
  },

  getResultFile: (resultId: string): string => {
    return `${API_BASE_URL}/api/results/${resultId}/file`;
  }
};

export default api;
