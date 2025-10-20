import api from './api';

export interface ReconciliationProject {
  id: string;
  name: string;
  description?: string;
  period_start: string;
  period_end: string;
  status: string;
  total_invoices: number;
  total_transactions: number;
  matched_count: number;
  unmatched_invoices: number;
  unmatched_transactions: number;
  total_invoice_amount: number;
  total_transaction_amount: number;
  variance_amount: number;
  created_at: string;
  updated_at: string;
}

export interface TaxInvoice {
  id: string;
  project_id: string;
  invoice_number: string;
  invoice_date: string;
  invoice_type: string;
  vendor_name: string;
  vendor_npwp: string;
  dpp: number;
  ppn: number;
  total_amount: number;
  match_status: string;
  match_confidence?: number;
  ai_model_used?: string;
  extraction_confidence?: number;
}

export interface BankTransaction {
  id: string;
  project_id: string;
  bank_name: string;
  account_number: string;
  transaction_date: string;
  description: string;
  debit: number;
  credit: number;
  balance: number;
  match_status: string;
  match_confidence?: number;
  extracted_vendor_name?: string;
  extracted_invoice_number?: string;
  ai_model_used?: string;
  extraction_confidence?: number;
}

export interface ReconciliationMatch {
  id: string;
  project_id: string;
  invoice_id: string;
  transaction_id: string;
  match_type: string;
  match_confidence: number;
  amount_variance: number;
  date_variance_days: number;
  score_amount: number;
  score_date: number;
  score_vendor: number;
  score_reference: number;
  status: string;
}

class ReconciliationService {
  // Projects
  async getProjects(status?: string): Promise<ReconciliationProject[]> {
    const params = status ? { status } : {};
    const response = await api.get('/api/reconciliation/projects', { params });
    return response.data;
  }

  async getProject(id: string): Promise<ReconciliationProject> {
    const response = await api.get(`/api/reconciliation/projects/${id}`);
    return response.data;
  }

  async createProject(data: {
    name: string;
    description?: string;
    period_start: string;
    period_end: string;
  }): Promise<ReconciliationProject> {
    const response = await api.post('/api/reconciliation/projects', data);
    return response.data;
  }

  async deleteProject(id: string): Promise<void> {
    await api.delete(`/api/reconciliation/projects/${id}`);
  }

  // Import from batches
  async importInvoicesFromBatch(projectId: string, batchId: string): Promise<any> {
    const response = await api.post(
      `/api/reconciliation/projects/${projectId}/import/batch/invoices`,
      null,
      { params: { batch_id: batchId } }
    );
    return response.data;
  }

  async importTransactionsFromBatch(projectId: string, batchId: string): Promise<any> {
    const response = await api.post(
      `/api/reconciliation/projects/${projectId}/import/batch/transactions`,
      null,
      { params: { batch_id: batchId } }
    );
    return response.data;
  }

  // AI Extraction
  async extractVendors(projectId: string, batchSize: number = 50): Promise<any> {
    const response = await api.post(
      `/api/reconciliation/projects/${projectId}/ai/extract-vendors`,
      null,
      { params: { batch_size: batchSize } }
    );
    return response.data;
  }

  async extractInvoices(projectId: string, batchSize: number = 50): Promise<any> {
    const response = await api.post(
      `/api/reconciliation/projects/${projectId}/ai/extract-invoices`,
      null,
      { params: { batch_size: batchSize } }
    );
    return response.data;
  }

  // Auto-matching
  async autoMatch(projectId: string, minConfidence: number = 0.7): Promise<any> {
    const response = await api.post(
      '/api/reconciliation/auto-match',
      { project_id: projectId, min_confidence: minConfidence }
    );
    return response.data;
  }

  // Invoices
  async getInvoices(projectId: string, matchStatus?: string): Promise<TaxInvoice[]> {
    const params = matchStatus ? { match_status: matchStatus } : {};
    const response = await api.get(`/api/reconciliation/projects/${projectId}/invoices`, { params });
    return response.data;
  }

  // Transactions
  async getTransactions(projectId: string, matchStatus?: string): Promise<BankTransaction[]> {
    const params = matchStatus ? { match_status: matchStatus } : {};
    const response = await api.get(`/api/reconciliation/projects/${projectId}/transactions`, { params });
    return response.data;
  }

  // Matches
  async getMatches(projectId: string, status?: string): Promise<ReconciliationMatch[]> {
    const params = status ? { status } : {};
    const response = await api.get(`/api/reconciliation/projects/${projectId}/matches`, { params });
    return response.data;
  }

  async deleteMatch(matchId: string, reason?: string): Promise<void> {
    await api.delete(`/api/reconciliation/matches/${matchId}`, {
      params: { reason }
    });
  }

  async confirmMatch(matchId: string): Promise<ReconciliationMatch> {
    const response = await api.post(`/api/reconciliation/matches/${matchId}/confirm`, null);
    return response.data;
  }

  // Export
  async exportProject(projectId: string): Promise<Blob> {
    const response = await api.get(`/api/reconciliation/projects/${projectId}/export`, {
      responseType: 'blob'
    });
    return response.data;
  }

  // Get available batches for import
  async getAvailableBatches(): Promise<any[]> {
    const response = await api.get('/api/batches');
    return response.data;
  }
}

export default new ReconciliationService();
