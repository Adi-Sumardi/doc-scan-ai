import React, { createContext, useContext, useState, ReactNode, useRef } from 'react';
import { apiService, Batch as ApiBatch, ScanResult as ApiScanResult } from '../services/api';
import toast from 'react-hot-toast';

// Use API types
export type DocumentFile = ApiBatch['files'][0];
export type Batch = ApiBatch;
export type ScanResult = ApiScanResult;

interface DocumentContextType {
  batches: Batch[];
  scanResults: ScanResult[];
  uploadDocuments: (files: File[], documentTypes: string[]) => Promise<Batch>;
  refreshBatch: (batchId: string) => Promise<void>;
  refreshAllData: () => Promise<void>;
  getBatch: (batchId: string) => Batch | undefined;
  getScanResultsByBatch: (batchId: string) => ScanResult[];
  exportResult: (resultId: string, format: 'excel' | 'pdf') => Promise<void>;
  exportBatch: (batchId: string, format: 'excel' | 'pdf') => Promise<void>;
  saveToGoogleDrive: (resultId: string, format: 'excel' | 'pdf') => Promise<void>;
  updateResult: (resultId: string, updatedData: any) => Promise<void>;
  loading: boolean;
}

const DocumentContext = createContext<DocumentContextType | undefined>(undefined);

export const DocumentProvider = ({ children }: { children: ReactNode }) => {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [scanResults, setScanResults] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(false);
  const notifiedBatchesRef = useRef<Set<string>>(new Set());
  const pollingIntervalsRef = useRef<NodeJS.Timeout[]>([]);

  // Load initial data
  React.useEffect(() => {
    refreshAllData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cleanup polling intervals on unmount to prevent memory leaks
  React.useEffect(() => {
    return () => {
      pollingIntervalsRef.current.forEach(clearInterval);
    };
  }, []);

  const handleBatchCompletion = (batchId: string) => {
    if (!notifiedBatchesRef.current.has(batchId)) {
      toast.success(`Batch #${batchId.slice(-8)} processed successfully!`);
      notifiedBatchesRef.current.add(batchId);
    }
  };

  // Helper to consistently update results for a batch
  const updateResultsForBatch = (batchId: string, results: ScanResult[]) => {
    setScanResults(prev => [...results, ...prev.filter(r => r.batch_id !== batchId)]);
  };

  const uploadDocuments = async (files: File[], documentTypes: string[]): Promise<Batch> => {
    try {
      setLoading(true);
      const batch = await apiService.uploadDocuments(files, documentTypes);
      
      setBatches(prev => [batch, ...prev]);
      
      // Start polling for updates
      pollBatchStatus(batch.id);
      
      toast.success(`Batch ${batch.id.slice(-8)} created with ${files.length} files`);
      return batch;
    } catch (error) {
      console.error('Upload error:', error);
      toast.error('Failed to upload documents');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const pollBatchStatus = async (batchId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const updatedBatch = await apiService.getBatchStatus(batchId);

        setBatches(prev => prev.map(batch =>
          batch.id === batchId ? updatedBatch : batch
        ));

        if (updatedBatch.status === 'completed') {
          clearInterval(pollInterval);
          removePollingInterval(pollInterval);

          // Retry mechanism to ensure all results are loaded
          let attempts = 0;
          const maxAttempts = 5;
          const attemptLoad = async () => {
            const results = await apiService.getBatchResults(batchId);
            if (Array.isArray(results) && results.length >= updatedBatch.total_files) {
              updateResultsForBatch(batchId, results);
              handleBatchCompletion(batchId);
            } else if (attempts < maxAttempts) {
              attempts++;
              setTimeout(attemptLoad, 2000); // Wait 2 seconds and retry
            } else {
              toast.error(`Polling failed for batch ${batchId.slice(-8)}. Please refresh the page.`, {
                duration: 6000,
              });
            }
          };

          await attemptLoad();
        }
        else if (updatedBatch.status === 'error' || updatedBatch.status === 'failed') {
          clearInterval(pollInterval);
          removePollingInterval(pollInterval);
          // Fix: Only remove results for the failed batch, not all results.
          setScanResults(prev => prev.filter(r => r.batch_id !== batchId));
        }
      } catch (error) {
        console.error('Polling error:', error);
        clearInterval(pollInterval);
        removePollingInterval(pollInterval);
      }
    }, 2000); // Poll every 2 seconds
    pollingIntervalsRef.current.push(pollInterval);

    // Stop polling after 5 minutes as a safety measure
    setTimeout(() => {
      clearInterval(pollInterval);
      removePollingInterval(pollInterval);
    }, 300000);
  };

  // Helper function to remove interval from tracking array
  const removePollingInterval = (interval: NodeJS.Timeout) => {
    pollingIntervalsRef.current = pollingIntervalsRef.current.filter(i => i !== interval);
  };

  const refreshBatch = async (batchId: string) => {
    try {
      const updatedBatch = await apiService.getBatchStatus(batchId);
      setBatches(prev => prev.map(batch => 
        batch.id === batchId ? updatedBatch : batch
      ));
      
      if (updatedBatch.status === 'completed') {
        const results = await apiService.getBatchResults(batchId);
        updateResultsForBatch(batchId, results);
        handleBatchCompletion(batchId);
      }
    } catch (error) {
      console.error('Refresh batch error:', error);
      toast.error('Failed to refresh batch status');
    }
  };

  const refreshAllData = async () => {
    try {
      setLoading(true);
      // Use Promise.allSettled to handle partial failures gracefully
      const [batchesPromise, resultsPromise] = await Promise.allSettled([
        apiService.getAllBatches(),
        apiService.getAllResults()
      ]);
      
      if (batchesPromise.status === 'fulfilled' && Array.isArray(batchesPromise.value)) {
        setBatches(batchesPromise.value);
      }

      if (resultsPromise.status === 'fulfilled' && Array.isArray(resultsPromise.value)) {
        setScanResults(resultsPromise.value);
      }
    } catch (error) {
      console.error('Refresh all data error:', error);
      // Handle network errors gracefully
      if (error instanceof Error && error.message === 'Network Error') {
        console.warn('Backend server is not accessible. Using offline mode.');
        // Set empty data - no dummy data in production
        setBatches([]);
        setScanResults([]);
      }
      toast.error('Failed to load data from server');
    } finally {
      setLoading(false);
    }
  };

  const getBatch = (batchId: string): Batch | undefined => {
    if (!Array.isArray(batches)) return undefined;
    return batches.find(batch => batch.id === batchId);
  };

  const getScanResultsByBatch = (batchId: string): ScanResult[] => {
    if (!Array.isArray(scanResults)) return [];
    return scanResults.filter(result => result.batch_id === batchId) || [];
  };

  const exportResult = async (resultId: string, format: 'excel' | 'pdf') => {
    try {
      setLoading(true);
      let blob: Blob;
      let filename: string;
      
      const result = scanResults.find(r => r.id === resultId);
      const baseFilename = result?.original_filename?.split('.')[0] || result?.filename?.split('.')[0] || 'document';
      
      if (format === 'excel') {
        blob = await apiService.exportResultExcel(resultId);
        filename = `${baseFilename}_extracted.xlsx`;
      } else {
        blob = await apiService.exportResultPdf(resultId);
        filename = `${baseFilename}_extracted.pdf`;
      }
      
      apiService.downloadFile(blob, filename);
      toast.success(`${format.toUpperCase()} download started`);
    } catch (error) {
      console.error('Export error:', error);
      toast.error(`Failed to export ${format.toUpperCase()}`);
    } finally {
      setLoading(false);
    }
  };

  const exportBatch = async (batchId: string, format: 'excel' | 'pdf') => {
    try {
      setLoading(true);
      const blob = await apiService.exportBatch(batchId, format);
      const filename = `batch_${batchId.slice(-8)}_results.${format === 'excel' ? 'xlsx' : 'pdf'}`;
      
      apiService.downloadFile(blob, filename);
      toast.success(`Batch ${format.toUpperCase()} download started`);
    } catch (error) {
      console.error('Batch export error:', error);
      toast.error('Failed to export batch');
    } finally {
      setLoading(false);
    }
  };

  const saveToGoogleDrive = async (resultId: string, format: 'excel' | 'pdf') => {
    try {
      // Validation
      if (!resultId) {
        throw new Error('Result ID is required');
      }
      if (!['excel', 'pdf'].includes(format)) {
        throw new Error('Invalid format. Must be excel or pdf');
      }

      setLoading(true);
      await apiService.saveToGoogleDrive(resultId, format);
      toast.success(`✅ Successfully saved to Google Drive as ${format.toUpperCase()}`);
    } catch (error: any) {
      console.error('Google Drive save error:', error);
      
      // Provide detailed error messages
      let errorMessage = 'Failed to save to Google Drive';
      
      if (error.message) {
        errorMessage = error.message;
      } else if (error.response?.data?.detail) {
        errorMessage = `Google Drive Error: ${error.response.data.detail}`;
      } else if (error.response?.status === 401) {
        errorMessage = 'Authentication required. Please login again.';
      } else if (error.response?.status === 403) {
        errorMessage = 'Permission denied. Check Google Drive access rights.';
      } else if (error.response?.status === 404) {
        errorMessage = 'Document not found. Please refresh and try again.';
      } else if (error.response?.status >= 500) {
        errorMessage = 'Server error. Please try again later.';
      }
      
      toast.error(errorMessage);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const updateResult = async (resultId: string, updatedData: any) => {
    try {
      // Validation: Check if resultId is valid
      if (!resultId || typeof resultId !== 'string') {
        throw new Error('Invalid result ID');
      }

      // Validation: Check if updatedData is provided and is an object
      if (!updatedData || typeof updatedData !== 'object' || Array.isArray(updatedData)) {
        throw new Error('Invalid data format. Expected an object.');
      }

      // Validation: Check if updatedData is not empty
      if (Object.keys(updatedData).length === 0) {
        throw new Error('No data to update. Please make changes first.');
      }

      // Validation: Sanitize data - remove null/undefined values
      const sanitizedData = Object.entries(updatedData).reduce((acc, [key, value]) => {
        if (value !== null && value !== undefined) {
          acc[key] = value;
        }
        return acc;
      }, {} as Record<string, any>);

      if (Object.keys(sanitizedData).length === 0) {
        throw new Error('All provided values are null or undefined.');
      }

      setLoading(true);
      const response = await apiService.updateResult(resultId, sanitizedData);
      
      // Update local state with new data
      setScanResults(prev => prev.map(result => 
        result.id === resultId 
          ? { 
              ...result, 
              extracted_data: { ...result.extracted_data, ...sanitizedData },
              updated_at: response.updated_at 
            }
          : result
      ));
      
      toast.success('✅ Result updated successfully!');
    } catch (error: any) {
      console.error('Update result error:', error);
      const errorMessage = error.message || error.response?.data?.detail || 'Failed to update result';
      toast.error(errorMessage);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  return (
    <DocumentContext.Provider value={{
      batches,
      scanResults,
      uploadDocuments,
      refreshBatch,
      refreshAllData,
      getBatch,
      getScanResultsByBatch,
      exportResult,
      exportBatch,
      saveToGoogleDrive,
      updateResult,
      loading
    }}>
      {children}
    </DocumentContext.Provider>
  );
};

export const useDocument = () => {
  const context = useContext(DocumentContext);
  if (!context) {
    throw new Error('useDocument must be used within a DocumentProvider');
  }
  return context;
};