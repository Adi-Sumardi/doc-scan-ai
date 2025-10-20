import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Scale,
  ArrowLeft,
  Download,
  RefreshCw,
  FileText,
  Building2,
  Link as LinkIcon,
  Brain,
  Upload as UploadIcon,
  PlayCircle,
  CheckCircle2,
  XCircle,
  AlertCircle
} from 'lucide-react';
import reconciliationService, {
  ReconciliationProject,
  TaxInvoice,
  BankTransaction,
  ReconciliationMatch
} from '../services/reconciliationService';
import { useDocument } from '../context/DocumentContext';
import { apiService } from '../services/api';
import toast from 'react-hot-toast';

const ReconciliationDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { uploadDocuments } = useDocument();

  const [project, setProject] = useState<ReconciliationProject | null>(null);
  const [invoices, setInvoices] = useState<TaxInvoice[]>([]);
  const [transactions, setTransactions] = useState<BankTransaction[]>([]);
  const [matches, setMatches] = useState<ReconciliationMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'invoices' | 'transactions' | 'matches'>('overview');
  const [showImportModal, setShowImportModal] = useState(false);
  const [batches, setBatches] = useState<any[]>([]);
  const [selectedBatch, setSelectedBatch] = useState('');
  const [importType, setImportType] = useState<'invoices' | 'transactions'>('invoices');
  const [processing, setProcessing] = useState(false);
  const [importMode, setImportMode] = useState<'batch' | 'upload'>('batch');
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    try {
      setLoading(true);

      // Load project data first (fastest, needed for header)
      const projectData = await reconciliationService.getProject(id!);
      setProject(projectData);
      setLoading(false); // ✅ Unlock UI immediately after project loads

      // Load rest of data in background (non-blocking)
      const [invoicesData, transactionsData, matchesData] = await Promise.all([
        reconciliationService.getInvoices(id!),
        reconciliationService.getTransactions(id!),
        reconciliationService.getMatches(id!)
      ]);

      setInvoices(invoicesData);
      setTransactions(transactionsData);
      setMatches(matchesData);
    } catch (error: any) {
      toast.error('Failed to load project data');
      console.error(error);
      setLoading(false);
    }
  };

  const loadBatches = async () => {
    try {
      const data = await reconciliationService.getAvailableBatches();
      console.log('Loaded batches:', data);
      setBatches(data);
    } catch (error) {
      console.error('Failed to load batches:', error);
      toast.error('Failed to load batches');
    }
  };

  const handleImport = async () => {
    // Validate based on import mode
    if (importMode === 'batch' && !selectedBatch) {
      toast.error('Please select a batch');
      return;
    }

    if (importMode === 'upload' && uploadFiles.length === 0) {
      toast.error('Please select files to upload');
      return;
    }

    try {
      setProcessing(true);

      if (importMode === 'batch') {
        // Import from existing batch
        if (importType === 'invoices') {
          const result = await reconciliationService.importInvoicesFromBatch(id!, selectedBatch);
          toast.success(`Imported ${result.imported} invoices`);
        } else {
          const result = await reconciliationService.importTransactionsFromBatch(id!, selectedBatch);
          toast.success(`Imported ${result.imported} transactions`);
        }
      } else {
        // Upload new files and process
        const documentType = importType === 'invoices' ? 'faktur_pajak' : 'rekening_koran';
        const documentTypes = uploadFiles.map(() => documentType);

        // Show uploading toast
        const uploadToast = toast.loading('Uploading files...');

        // Upload files using DocumentContext
        const batch = await uploadDocuments(uploadFiles, documentTypes);
        const newBatchId = batch.id;

        // Update toast - upload complete, now processing
        toast.loading('Processing files...', { id: uploadToast });

        // Wait for processing to complete (check batch status)
        let attempts = 0;
        const maxAttempts = 60; // 60 seconds max (increased for larger files)

        while (attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, 1000));
          const batchStatus = await apiService.getBatchStatus(newBatchId);

          // Update progress in toast
          if (batchStatus.progress_percentage) {
            toast.loading(`Processing files... ${Math.round(batchStatus.progress_percentage)}%`, { id: uploadToast });
          }

          if (batchStatus.status === 'completed') {
            toast.success('Files processed successfully!', { id: uploadToast });
            break;
          } else if (batchStatus.status === 'failed') {
            toast.error('Batch processing failed', { id: uploadToast });
            throw new Error('Batch processing failed');
          }
          attempts++;
        }

        // Check if timed out
        if (attempts >= maxAttempts) {
          toast.error('Processing timeout - files may still be processing', { id: uploadToast });
          throw new Error('Processing timeout');
        }

        // Import from the newly created batch
        if (importType === 'invoices') {
          const result = await reconciliationService.importInvoicesFromBatch(id!, newBatchId);
          toast.success(`Imported ${result.imported} invoices from uploaded files`);
        } else {
          const result = await reconciliationService.importTransactionsFromBatch(id!, newBatchId);
          toast.success(`Imported ${result.imported} transactions from uploaded files`);
        }
      }

      setShowImportModal(false);
      setSelectedBatch('');
      setUploadFiles([]);
      loadData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || error.message || 'Import failed');
    } finally {
      setProcessing(false);
    }
  };

  const handleAIExtraction = async (type: 'vendors' | 'invoices') => {
    if (!confirm(`Run AI extraction for ${type}? This may take a few minutes.`)) return;

    try {
      setProcessing(true);
      const result = type === 'vendors'
        ? await reconciliationService.extractVendors(id!)
        : await reconciliationService.extractInvoices(id!);

      toast.success(`Extracted ${result.extracted} ${type} successfully`);
      loadData();
    } catch (error: any) {
      toast.error(`AI extraction failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setProcessing(false);
    }
  };

  const handleAutoMatch = async () => {
    if (!confirm('Run auto-matching? This will match invoices with transactions based on AI analysis.')) return;

    try {
      setProcessing(true);
      const result = await reconciliationService.autoMatch(id!);
      toast.success(`Auto-matched ${result.matches_found} pairs (${result.high_confidence_matches} high confidence)`);
      loadData();
    } catch (error: any) {
      toast.error(`Auto-matching failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setProcessing(false);
    }
  };

  const handleExport = async () => {
    try {
      setProcessing(true);
      const blob = await reconciliationService.exportProject(id!);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reconciliation_${project?.name}_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Excel report downloaded');
    } catch (error) {
      toast.error('Export failed');
    } finally {
      setProcessing(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      minimumFractionDigits: 0
    }).format(value);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('id-ID');
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-green-600 bg-green-50';
    if (confidence >= 0.7) return 'text-blue-600 bg-blue-50';
    if (confidence >= 0.5) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  // Only block UI if project data hasn't loaded yet
  // Once project loads, rest of data (invoices/transactions/matches) loads in background
  if (!project) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading project...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/reconciliation')}
          className="flex items-center space-x-2 text-gray-600 hover:text-gray-800 mb-4"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to Projects</span>
        </button>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center space-x-4">
              <div className="w-16 h-16 bg-blue-100 rounded-lg flex items-center justify-center">
                <Scale className="w-10 h-10 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-800">{project.name}</h1>
                <p className="text-gray-600">{project.description}</p>
                <p className="text-sm text-gray-500 mt-1">
                  Period: {formatDate(project.period_start)} - {formatDate(project.period_end)}
                </p>
              </div>
            </div>
            <button
              onClick={handleExport}
              disabled={processing}
              className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              <Download className="w-5 h-5" />
              <span>Export Excel</span>
            </button>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-sm text-blue-600 mb-1">Invoices</p>
              <p className="text-2xl font-bold text-blue-900">{project.total_invoices}</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-4">
              <p className="text-sm text-purple-600 mb-1">Transactions</p>
              <p className="text-2xl font-bold text-purple-900">{project.total_transactions}</p>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <p className="text-sm text-green-600 mb-1">Matched</p>
              <p className="text-2xl font-bold text-green-900">{project.matched_count}</p>
            </div>
            <div className="bg-orange-50 rounded-lg p-4">
              <p className="text-sm text-orange-600 mb-1">Unmatched</p>
              <p className="text-2xl font-bold text-orange-900">{project.unmatched_invoices}</p>
            </div>
            <div className="bg-red-50 rounded-lg p-4">
              <p className="text-sm text-red-600 mb-1">Variance</p>
              <p className="text-xl font-bold text-red-900">{formatCurrency(project.variance_amount)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button
            onClick={() => {
              setImportType('invoices');
              setShowImportModal(true);
              loadBatches();
            }}
            className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all"
          >
            <FileText className="w-8 h-8 text-blue-600 mb-2" />
            <span className="text-sm font-medium text-gray-700">Import Invoices</span>
          </button>

          <button
            onClick={() => {
              setImportType('transactions');
              setShowImportModal(true);
              loadBatches();
            }}
            className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-purple-500 hover:bg-purple-50 transition-all"
          >
            <Building2 className="w-8 h-8 text-purple-600 mb-2" />
            <span className="text-sm font-medium text-gray-700">Import Transactions</span>
          </button>

          <button
            onClick={() => handleAIExtraction('vendors')}
            disabled={processing}
            className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-500 hover:bg-green-50 transition-all disabled:opacity-50"
          >
            <Brain className="w-8 h-8 text-green-600 mb-2" />
            <span className="text-sm font-medium text-gray-700">AI Extract Vendors</span>
          </button>

          <button
            onClick={handleAutoMatch}
            disabled={processing}
            className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-orange-500 hover:bg-orange-50 transition-all disabled:opacity-50"
          >
            <PlayCircle className="w-8 h-8 text-orange-600 mb-2" />
            <span className="text-sm font-medium text-gray-700">Auto Match</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            {[
              { key: 'overview', label: 'Overview' },
              { key: 'invoices', label: `Invoices (${invoices.length})` },
              { key: 'transactions', label: `Transactions (${transactions.length})` },
              { key: 'matches', label: `Matches (${matches.length})` }
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Project Summary</h3>
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-medium text-gray-700 mb-3">Financial Summary</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Total Invoice Amount:</span>
                        <span className="font-semibold">{formatCurrency(project.total_invoice_amount)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Total Transaction Amount:</span>
                        <span className="font-semibold">{formatCurrency(project.total_transaction_amount)}</span>
                      </div>
                      <div className="flex justify-between pt-2 border-t">
                        <span className="text-gray-600">Variance:</span>
                        <span className="font-semibold text-red-600">{formatCurrency(project.variance_amount)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-medium text-gray-700 mb-3">Matching Progress</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Matched Pairs:</span>
                        <span className="font-semibold text-green-600">{project.matched_count}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Unmatched Invoices:</span>
                        <span className="font-semibold text-orange-600">{project.unmatched_invoices}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Unmatched Transactions:</span>
                        <span className="font-semibold text-orange-600">{project.unmatched_transactions}</span>
                      </div>
                      <div className="flex justify-between pt-2 border-t">
                        <span className="text-gray-600">Completion Rate:</span>
                        <span className="font-semibold text-blue-600">
                          {project.total_invoices > 0
                            ? `${Math.round((project.matched_count / project.total_invoices) * 100)}%`
                            : '0%'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Invoices Tab */}
          {activeTab === 'invoices' && (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Invoice Number</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Vendor</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {invoices.map(invoice => (
                    <tr key={invoice.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {invoice.invoice_number}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(invoice.invoice_date)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {invoice.vendor_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatCurrency(invoice.total_amount)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          invoice.match_status === 'auto_matched' ? 'bg-green-100 text-green-700' :
                          invoice.match_status === 'manual_matched' ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {invoice.match_status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {invoice.match_confidence && (
                          <span className={`px-2 py-1 text-xs rounded ${getConfidenceColor(invoice.match_confidence)}`}>
                            {Math.round(invoice.match_confidence * 100)}%
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {invoices.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                  No invoices imported yet. Click "Import Invoices" to get started.
                </div>
              )}
            </div>
          )}

          {/* Transactions Tab */}
          {activeTab === 'transactions' && (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Debit</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Credit</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Extracted Vendor</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {transactions.map(txn => (
                    <tr key={txn.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(txn.transaction_date)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                        {txn.description}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {txn.debit > 0 ? formatCurrency(txn.debit) : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {txn.credit > 0 ? formatCurrency(txn.credit) : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          txn.match_status === 'auto_matched' ? 'bg-green-100 text-green-700' :
                          txn.match_status === 'manual_matched' ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {txn.match_status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {txn.extracted_vendor_name || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {transactions.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                  No transactions imported yet. Click "Import Transactions" to get started.
                </div>
              )}
            </div>
          )}

          {/* Matches Tab */}
          {activeTab === 'matches' && (
            <div className="space-y-4">
              {matches.map(match => (
                <div key={match.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-3">
                    <span className={`px-3 py-1 text-sm rounded-full ${
                      match.match_type === 'auto' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
                    }`}>
                      {match.match_type === 'auto' ? 'Auto Matched' : 'Manual Matched'}
                    </span>
                    <span className={`px-3 py-1 text-sm rounded ${getConfidenceColor(match.match_confidence)}`}>
                      Confidence: {Math.round(match.match_confidence * 100)}%
                    </span>
                  </div>

                  <div className="grid md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500 mb-1">Amount Variance</p>
                      <p className="font-semibold">{formatCurrency(match.amount_variance)}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 mb-1">Date Variance</p>
                      <p className="font-semibold">{match.date_variance_days} days</p>
                    </div>
                    <div>
                      <p className="text-gray-500 mb-1">Amount Score</p>
                      <p className="font-semibold">{Math.round(match.score_amount * 100)}%</p>
                    </div>
                    <div>
                      <p className="text-gray-500 mb-1">Date Score</p>
                      <p className="font-semibold">{Math.round(match.score_date * 100)}%</p>
                    </div>
                  </div>
                </div>
              ))}
              {matches.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                  No matches found. Run "Auto Match" to start matching invoices with transactions.
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-2 sm:p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-4 sm:p-6 max-h-[95vh] sm:max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl sm:text-2xl font-bold text-gray-800 mb-4 sm:mb-6">
              Import {importType === 'invoices' ? 'Tax Invoices' : 'Bank Transactions'}
            </h2>

            {/* Mode Selection */}
            <div className="mb-4 sm:mb-6">
              <div className="flex space-x-2 bg-gray-100 p-1 rounded-lg">
                <button
                  onClick={() => setImportMode('batch')}
                  className={`flex-1 py-2 px-2 sm:px-4 rounded-md text-sm sm:text-base font-medium transition-all ${
                    importMode === 'batch'
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-800'
                  }`}
                >
                  <span className="hidden sm:inline">From Existing Batch</span>
                  <span className="sm:hidden">Existing</span>
                </button>
                <button
                  onClick={() => setImportMode('upload')}
                  className={`flex-1 py-2 px-2 sm:px-4 rounded-md text-sm sm:text-base font-medium transition-all ${
                    importMode === 'upload'
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-800'
                  }`}
                >
                  <span className="hidden sm:inline">Upload New Files</span>
                  <span className="sm:hidden">Upload</span>
                </button>
              </div>
            </div>

            <div className="space-y-4">
              {importMode === 'batch' ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select Batch to Import
                  </label>
                  <div className="space-y-2 max-h-80 overflow-y-auto border border-gray-200 rounded-lg p-2">
                    {batches.length === 0 ? (
                      <p className="text-center text-gray-500 py-8">No batches available</p>
                    ) : (
                      (() => {
                        // Debug: Log all batches first
                        console.log('All batches for filtering:', batches);

                        const filteredBatches = batches.filter(batch => {
                          // Only show completed batches (but be flexible)
                          const isCompleted = batch.status === 'completed' || batch.status === 'processed';
                          if (!isCompleted) {
                            console.log(`Batch ${batch.id} skipped - status: ${batch.status}`);
                            return false;
                          }

                          // If no files array, skip
                          if (!batch.files || !Array.isArray(batch.files)) {
                            console.log(`Batch ${batch.id} has no files array`, batch);
                            return false;
                          }

                          // Filter by document type (check if any file matches)
                          if (importType === 'invoices') {
                            // Check for faktur pajak (various formats)
                            const hasInvoices = batch.files.some((f: any) => {
                              const fileType = f.type || f.document_type || '';
                              const match = fileType.toLowerCase().includes('faktur') ||
                                           fileType.toLowerCase().includes('pajak');
                              console.log(`File type check (invoice): "${fileType}" -> ${match}`);
                              return match;
                            });
                            console.log(`Batch ${batch.id} has invoices:`, hasInvoices);
                            return hasInvoices;
                          } else {
                            // Check for rekening koran
                            const hasTransactions = batch.files.some((f: any) => {
                              const fileType = f.type || f.document_type || '';
                              const match = fileType.toLowerCase().includes('rekening') ||
                                           fileType.toLowerCase().includes('koran');
                              console.log(`File type check (transaction): "${fileType}" -> ${match}`);
                              return match;
                            });
                            console.log(`Batch ${batch.id} has transactions:`, hasTransactions);
                            return hasTransactions;
                          }
                        });

                        console.log('Filtered batches:', filteredBatches.length, 'of', batches.length);

                        if (filteredBatches.length === 0) {
                          return (
                            <div className="text-center py-8">
                              <p className="text-gray-500 mb-2">
                                No completed batches with {importType === 'invoices' ? 'tax invoices' : 'bank transactions'} found
                              </p>
                              <p className="text-xs text-gray-400">
                                (Total batches: {batches.length}, check browser console for details)
                              </p>
                            </div>
                          );
                        }

                        return filteredBatches.map(batch => (
                          <label
                            key={batch.id}
                            className={`flex items-start p-4 border-2 rounded-lg cursor-pointer transition-all ${
                              selectedBatch === batch.id
                                ? 'border-blue-500 bg-blue-50'
                                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                            }`}
                          >
                            <input
                              type="radio"
                              name="batch"
                              value={batch.id}
                              checked={selectedBatch === batch.id}
                              onChange={(e) => setSelectedBatch(e.target.value)}
                              className="mt-1 mr-3"
                            />
                            <div className="flex-1">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-semibold text-gray-800">
                                  {batch.created_at ? new Date(batch.created_at).toLocaleString('id-ID', {
                                    day: '2-digit',
                                    month: 'short',
                                    year: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                  }) : 'Unknown date'}
                                </span>
                                <span className={`px-2 py-1 text-xs rounded-full ${
                                  batch.status === 'completed' ? 'bg-green-100 text-green-700' :
                                  batch.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-gray-100 text-gray-700'
                                }`}>
                                  {batch.status}
                                </span>
                              </div>
                              <div className="text-sm text-gray-600">
                                {batch.total_files} file(s) | {batch.processed_files}/{batch.total_files} processed
                              </div>
                              {batch.id && (
                                <div className="text-xs text-gray-400 mt-1">
                                  ID: {batch.id.substring(0, 8)}...
                                </div>
                              )}
                            </div>
                          </label>
                        ));
                      })()
                    )}
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Upload {importType === 'invoices' ? 'Tax Invoice' : 'Bank Statement'} Files
                  </label>
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-500 transition-colors">
                    <UploadIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <input
                      type="file"
                      multiple
                      accept=".pdf,.xlsx,.xls"
                      onChange={(e) => {
                        if (e.target.files) {
                          setUploadFiles(Array.from(e.target.files));
                        }
                      }}
                      className="hidden"
                      id="file-upload"
                    />
                    <label
                      htmlFor="file-upload"
                      className="cursor-pointer text-blue-600 hover:text-blue-700 font-medium"
                    >
                      Click to upload
                    </label>
                    <span className="text-gray-600"> or drag and drop</span>
                    <p className="text-xs text-gray-500 mt-2">
                      PDF, Excel files up to 10MB each
                    </p>
                    {uploadFiles.length > 0 && (
                      <div className="mt-4 space-y-2">
                        {uploadFiles.map((file, index) => (
                          <div key={index} className="flex items-center justify-between bg-gray-50 px-4 py-2 rounded">
                            <span className="text-sm text-gray-700">{file.name}</span>
                            <button
                              onClick={() => setUploadFiles(files => files.filter((_, i) => i !== index))}
                              className="text-red-600 hover:text-red-700"
                            >
                              ✕
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 mt-3">
                    💡 Files will be processed automatically after upload
                  </p>
                </div>
              )}

              <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3 pt-4 border-t border-gray-200">
                <button
                  type="button"
                  onClick={() => {
                    setShowImportModal(false);
                    setSelectedBatch('');
                    setUploadFiles([]);
                    setImportMode('batch');
                  }}
                  className="w-full sm:flex-1 px-4 py-2.5 sm:py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm sm:text-base"
                >
                  Cancel
                </button>
                <button
                  onClick={handleImport}
                  disabled={(importMode === 'batch' && !selectedBatch) || (importMode === 'upload' && uploadFiles.length === 0) || processing}
                  className="w-full sm:flex-1 px-4 py-2.5 sm:py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm sm:text-base"
                >
                  {processing ? 'Processing...' : importMode === 'batch' ? 'Import from Batch' : 'Upload & Import'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReconciliationDetail;
