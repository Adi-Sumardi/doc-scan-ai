import axios from 'axios';
import { getApiBaseUrl } from '../utils/config';

const API_BASE_URL = getApiBaseUrl();

const IS_DEV = import.meta.env.DEV;

// Axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes default timeout
});

// Request logging and JWT token interceptor
api.interceptors.request.use(
  (config) => {
    if (IS_DEV) {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);
    }

    // Add JWT token to requests if available
    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response logging & error handling with 401 auto-logout
api.interceptors.response.use(
  (response) => {
    if (IS_DEV) {
      console.log(`[API Response] ${response.status} ${response.config.url}`);
    }
    return response;
  },
  (error) => {
    // Handle 401 Unauthorized - auto logout and cleanup
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      sessionStorage.clear();

      if (!window.location.pathname.includes('/login') &&
          !window.location.pathname.includes('/register')) {
        const currentPath = window.location.pathname + window.location.search;
        if (currentPath !== '/' && currentPath !== '/login') {
          localStorage.setItem('redirectAfterLogin', currentPath);
        }
        setTimeout(() => { window.location.href = '/login'; }, 100);
      }
    }

    // Handle network errors
    if (error.message === 'Network Error') {
      error.message = 'Cannot connect to server. Please check your connection.';
    }

    // Handle timeout errors
    if (error.code === 'ECONNABORTED') {
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
  failed_files?: number;
  current_file?: string;
  eta_seconds?: number;
  error_message?: string;
  results?: any[];
}
export interface ScanResult {
  id: string; batch_id: string; filename: string; document_type: string; extracted_text?: string; extracted_data: any;
  confidence?: number; confidence_score?: number; ocr_engine_used?: string; created_at: string;
  ocr_processing_time?: number; processing_time?: number;
  original_filename?: string; file_type?: string; status?: string; ai_data?: AIData; export_formats?: string[];
  nextgen_metrics?: NextGenOCRMetrics; processing_quality?: ProcessingQuality; document_structure?: any; extracted_entities?: any;
  raw_ocr_result?: any;
}

// ==================== Reconciliation Chat Interfaces ====================

export interface ReconciliationSession {
  id: string;
  title: string;
  created_at: string;
  updated_at?: string;
}

export interface ReconciliationAttachment {
  name: string;
  detected_type?: string;
  row_count?: number;
  error?: string;
}

export interface ReconciliationMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  attachments?: ReconciliationAttachment[];
  results?: ReconciliationResults;
  created_at?: string;
}

export interface ReconciliationResults {
  files_detected?: Array<{ name: string; detected_type: string; row_count: number; error?: string }>;
  company_npwp?: string;
  reconciliation?: {
    status: string;
    error?: string;
    point_a_count?: number;
    point_b_count?: number;
    point_c_count?: number;
    point_e_count?: number;
    matches?: {
      point_a_vs_c?: ReconciliationMatch[];
      point_b_vs_e?: ReconciliationMatch[];
    };
    mismatches?: {
      point_a_unmatched?: Record<string, unknown>[];
      point_c_unmatched?: Record<string, unknown>[];
      point_b_unmatched?: Record<string, unknown>[];
      point_e_unmatched?: Record<string, unknown>[];
    };
    summary?: ReconciliationSummary;
  };
}

export interface ReconciliationMatch {
  id?: string;
  match_type?: string;
  match_confidence?: number;
  details?: {
    nomor_faktur?: string;
    vendor_name?: string;
    amount?: number;
    [key: string]: unknown;
  };
}

export interface ReconciliationSummary {
  match_rate?: number;
  total_auto_matched?: number;
  total_suggested?: number;
  total_unmatched?: number;
  match_rate_a_vs_c?: number;
  match_rate_b_vs_e?: number;
  [key: string]: unknown;
}

export interface SendMessageResponse {
  user_message: ReconciliationMessage;
  assistant_message: ReconciliationMessage;
}

export interface SessionDetailResponse {
  id: string;
  title: string;
  created_at: string;
  messages: ReconciliationMessage[];
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
    const response = await api.get(`/api/batches/${batchId}`, { timeout: 600000 });
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
    const response = await api.get(`/api/batches?${params.toString()}`);
    return response.data;
  },

  getAllResults: async (batchIds?: string[]): Promise<ScanResult[]> => {
    const params = new URLSearchParams();
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

  updateResult: async (resultId: string, updatedData: any): Promise<any> => {
    const response = await api.patch(`/api/results/${resultId}`, updatedData);
    return response.data;
  },

  getResultFile: (resultId: string): string => {
    return `${API_BASE_URL}/api/results/${resultId}/file`;
  },

  // ==================== Reconciliation Chat ====================
  reconciliation: {
    getSessions: async (): Promise<ReconciliationSession[]> => {
      const response = await api.get('/api/reconciliation-ppn/sessions');
      return response.data;
    },
    createSession: async (): Promise<ReconciliationSession> => {
      const response = await api.post('/api/reconciliation-ppn/sessions');
      return response.data;
    },
    getSession: async (sessionId: string, signal?: AbortSignal): Promise<SessionDetailResponse> => {
      const response = await api.get(`/api/reconciliation-ppn/sessions/${sessionId}`, { signal });
      return response.data;
    },
    deleteSession: async (sessionId: string): Promise<void> => {
      await api.delete(`/api/reconciliation-ppn/sessions/${sessionId}`);
    },
    sendMessage: async (sessionId: string, formData: FormData): Promise<SendMessageResponse> => {
      const response = await api.post(
        `/api/reconciliation-ppn/sessions/${sessionId}/chat`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 600000 }
      );
      return response.data;
    },
    exportResults: async (sessionId: string, messageId: string): Promise<Blob> => {
      const response = await api.post(
        `/api/reconciliation-ppn/sessions/${sessionId}/export`,
        { message_id: messageId },
        { responseType: 'blob' }
      );
      return response.data;
    },
  },
};

export default api;
