// Types untuk AI Data Formatter
export interface DocumentResult {
  id: string;
  batch_id: string;
  document_type: string;
  original_filename: string;
  extracted_data: any;
  confidence: number;
  created_at: string;
  status?: string;
}

export interface APIResponse {
  batch_id: string;
  files: Array<{
    filename: string;
    status: string;
  }>;
}

export interface BatchResponse {
  id: string;
  created_at: string;
  status: 'processing' | 'completed' | 'failed';
  total_files: number;
  completed_files: number;
}