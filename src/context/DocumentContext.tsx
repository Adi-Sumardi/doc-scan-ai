import React, { createContext, useContext, useState, ReactNode } from 'react';
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
  exportBatch: (batchId: string, format: 'excel') => Promise<void>;
  saveToGoogleDrive: (resultId: string, format: 'excel' | 'pdf') => Promise<void>;
  loading: boolean;
}

const DocumentContext = createContext<DocumentContextType | undefined>(undefined);

export const DocumentProvider = ({ children }: { children: ReactNode }) => {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [scanResults, setScanResults] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(false);

  // Load initial data
  React.useEffect(() => {
    refreshAllData();
  }, []);

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
          
          // Load results
          const results = await apiService.getBatchResults(batchId);
          setScanResults(prev => [...results, ...prev.filter(r => r.batch_id !== batchId)]);
          
          toast.success('All documents have been processed successfully!');
        } else if (updatedBatch.status === 'error') {
          clearInterval(pollInterval);
         setScanResults([]);
        }
      } catch (error) {
        console.error('Polling error:', error);
        clearInterval(pollInterval);
      }
    }, 2000); // Poll every 2 seconds
    
    // Stop polling after 5 minutes
    setTimeout(() => clearInterval(pollInterval), 300000);
  };

  const refreshBatch = async (batchId: string) => {
    try {
      const updatedBatch = await apiService.getBatchStatus(batchId);
      setBatches(prev => prev.map(batch => 
        batch.id === batchId ? updatedBatch : batch
      ));
      
      if (updatedBatch.status === 'completed') {
        const results = await apiService.getBatchResults(batchId);
        setScanResults(prev => [...results, ...prev.filter(r => r.batch_id !== batchId)]);
      }
    } catch (error) {
      console.error('Refresh batch error:', error);
      toast.error('Failed to refresh batch status');
    }
  };

  const refreshAllData = async () => {
    try {
      setLoading(true);
      const [batchesData, resultsData] = await Promise.all([
        apiService.getAllBatches(),
        apiService.getAllResults()
      ]);
      
      setBatches(batchesData);
      setScanResults(resultsData);
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

  const getBatch = (batchId: string) => {
    return batches.find(batch => batch.id === batchId);
  };

  const getScanResultsByBatch = (batchId: string) => {
    return scanResults.filter(result => result.batch_id === batchId);
  };

  const exportResult = async (resultId: string, format: 'excel' | 'pdf') => {
    try {
      setLoading(true);
      let blob: Blob;
      let filename: string;
      
      const result = scanResults.find(r => r.id === resultId);
      const baseFilename = result?.original_filename.split('.')[0] || 'document';
      
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

  const exportBatch = async (batchId: string, format: 'excel') => {
    try {
      setLoading(true);
      const blob = await apiService.exportBatchExcel(batchId);
      const filename = `batch_${batchId.slice(-8)}_results.${format === 'excel' ? 'xlsx' : 'pdf'}`;
      
      apiService.downloadFile(blob, filename);
      toast.success('Batch Excel download started');
    } catch (error) {
      console.error('Batch export error:', error);
      toast.error('Failed to export batch');
    } finally {
      setLoading(false);
    }
  };

  const saveToGoogleDrive = async (resultId: string, format: 'excel' | 'pdf') => {
    try {
      setLoading(true);
      await apiService.saveToGoogleDrive(resultId, format);
      toast.success(`Saved to Google Drive as ${format.toUpperCase()}`);
    } catch (error) {
      console.error('Google Drive save error:', error);
      toast.error('Failed to save to Google Drive');
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