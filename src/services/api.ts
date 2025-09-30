import axios from 'axios';

// Determine API base URL based on environment
const getApiBaseUrl = () => {
  // In production, use relative URLs to work with Nginx proxy
  if (import.meta.env.PROD) {
    return '/api';
  }
  
  // In development, use localhost
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds timeout for file uploads
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export interface DocumentFile {
  id: string;
  name: string;
  type: string;
  status: string;
  progress: number;
  result_id?: string;
}

export interface NextGenOCRMetrics {
  confidence: number;
  layout_confidence: number;
  semantic_confidence: number;
  quality_score: number;
  processing_time: number;
  engine_used: string;
}

export interface ProcessingQuality {
  overall_score: number;
  text_clarity: number;
  structure_preservation: number;
  accuracy_rating: 'excellent' | 'good' | 'fair' | 'poor';
}

export interface AIData {
  extracted_data: any;
  entities: any[];
  document_type: string;
  confidence: number;
}

export interface Batch {
  id: string;
  files: DocumentFile[];
  status: string;
  created_at: string;
  total_files: number;
  processed_files: number;
  completed_at?: string;
  error?: string;
}

export interface ScanResult {
  id: string;
  batch_id: string;
  filename: string;
  document_type: string;
  extracted_text?: string;
  extracted_data: any;
  confidence?: number;
  confidence_score?: number; // Legacy support
  ocr_engine_used?: string;
  created_at: string;
  ocr_processing_time?: number;
  processing_time?: number; // Legacy support
  // Legacy support
  original_filename?: string;
  file_type?: string;
  status?: string;
  ai_data?: AIData;
  export_formats?: string[];
  // Next-Generation OCR enhancements
  nextgen_metrics?: NextGenOCRMetrics;
  processing_quality?: ProcessingQuality;
  document_structure?: any;
  extracted_entities?: any;
}

export const apiService = {
  // Upload documents
  async uploadDocuments(files: File[], documentTypes: string[]): Promise<Batch> {
    const formData = new FormData();
    
    files.forEach((file) => {
      formData.append('files', file);
    });
    
    documentTypes.forEach((type) => {
      formData.append('document_types', type);
    });
    
    const response = await api.post('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },

  // Get batch status
  async getBatchStatus(batchId: string): Promise<Batch> {
    const response = await api.get(`/api/batches/${batchId}`);
    return response.data;
  },

  // Get batch results
  async getBatchResults(batchId: string): Promise<ScanResult[]> {
    const response = await api.get(`/api/batches/${batchId}/results`);
    return response.data.results || [];
  },

  // Get all batches
  async getAllBatches(): Promise<Batch[]> {
    const response = await api.get('/api/batches');
    return response.data;
  },

  // Get all results
  async getAllResults(): Promise<ScanResult[]> {
    const response = await api.get('/api/results');
    return response.data;
  },

  // Export single result to Excel
  async exportResultExcel(resultId: string): Promise<Blob> {
    const response = await api.get(`/api/results/${resultId}/export/excel`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Export single result to PDF
  async exportResultPdf(resultId: string): Promise<Blob> {
    const response = await api.get(`/api/results/${resultId}/export/pdf`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Export batch to Excel
  async exportBatchExcel(batchId: string): Promise<Blob> {
    const response = await api.get(`/api/batches/${batchId}/export/excel`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Next-Generation OCR specific endpoints
  async getProcessingQuality(resultId: string): Promise<ProcessingQuality> {
    const response = await api.get(`/api/results/${resultId}/quality`);
    return response.data;
  },

  // Get OCR engine performance metrics
  async getOCRMetrics(resultId: string): Promise<NextGenOCRMetrics> {
    const response = await api.get(`/api/results/${resultId}/metrics`);
    return response.data;
  },

  // Get system health status
  async getSystemHealth(): Promise<any> {
    const response = await api.get('/api/health');
    return response.data;
  },

  // Real-time processing status via WebSocket
  createWebSocketConnection(batchId: string): WebSocket {
    // Determine WebSocket URL based on environment
    const getWsUrl = () => {
      if (import.meta.env.PROD) {
        // In production, use wss:// with domain
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}/ws/batch/${batchId}`;
      }
      // In development, use localhost
      return `ws://localhost:8000/ws/batch/${batchId}`;
    };
    
    const wsUrl = getWsUrl();
    return new WebSocket(wsUrl);
  },

  // Download file helper
  downloadFile(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  // Mock Google Drive save (replace with real implementation)
  async saveToGoogleDrive(resultId: string, format: 'excel' | 'pdf'): Promise<void> {
    // This would integrate with Google Drive API in production
    console.log(`Saving result ${resultId} to Google Drive as ${format}`);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // In production, this would:
    // 1. Get the file blob from export endpoint
    // 2. Upload to Google Drive using Google Drive API
    // 3. Return the Google Drive file ID/URL
  }
};

export default api;