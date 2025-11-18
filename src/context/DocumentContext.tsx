import React, { createContext, useContext, useState, ReactNode, useRef } from 'react';
import { apiService, Batch as ApiBatch, ScanResult as ApiScanResult } from '../services/api';
import toast from 'react-hot-toast';
import { useAuth } from './AuthContext';

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
  deleteBatch: (batchId: string) => Promise<void>;
  loading: boolean;
}

const DocumentContext = createContext<DocumentContextType | undefined>(undefined);

export const DocumentProvider = ({ children }: { children: ReactNode }) => {
  const { isLoading: authLoading, isAuthenticated } = useAuth();
  const [batches, setBatches] = useState<Batch[]>([]);
  const [scanResults, setScanResults] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(false);
  const notifiedBatchesRef = useRef<Set<string>>(new Set());

  // ✅ FIX: Better tracking using Map instead of arrays
  // Maps batch ID to cleanup function for proper cancellation
  const pollingCleanupRef = useRef<Map<string, () => void>>(new Map());
  const loadingBatchesRef = useRef<Set<string>>(new Set());
  const isMountedRef = useRef(true); // Track mount status

  // Load initial data ONLY after auth is ready (LAZY LOAD - only recent batches)
  React.useEffect(() => {
    // Wait for auth to finish loading
    if (!authLoading && isAuthenticated) {
      console.log('🔄 Auth ready, lazy loading recent batches...');
      // Defer to next tick to avoid state update during render
      setTimeout(() => {
        // OPTIMIZATION: Only load recent 10 batches initially (fast!)
        // Full data loads in background (non-blocking)
        loadRecentBatchesOnly();
      }, 0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isAuthenticated]);

  // Debug: Log batches state changes (wrapped to avoid render warnings)
  React.useEffect(() => {
    // Use setTimeout to avoid state update warnings during render
    const timer = setTimeout(() => {
      console.log('📊 Batches state updated. Total:', batches.length);
      if (batches.length > 0) {
        console.log('First batch:', batches[0]);
        console.log('Last batch:', batches[batches.length - 1]);
      }
    }, 0);

    return () => clearTimeout(timer);
  }, [batches]);

  // ✅ FIX: Enhanced cleanup on unmount to prevent memory leaks
  React.useEffect(() => {
    isMountedRef.current = true;

    return () => {
      console.log('🧹 DocumentContext unmounting - cleaning up all polling...');
      isMountedRef.current = false;

      // ✅ FIX: Call all cleanup functions to properly cancel polling
      pollingCleanupRef.current.forEach((cleanup, batchId) => {
        console.log(`🧹 Cleaning up polling for batch ${batchId.slice(-8)}`);
        try {
          cleanup();
        } catch (error) {
          console.error(`Error cleaning up batch ${batchId}:`, error);
        }
      });
      pollingCleanupRef.current.clear();
      loadingBatchesRef.current.clear();
      console.log('✅ All polling cleaned up');
    };
  }, []);

  const handleBatchCompletion = (batchId: string) => {
    if (!notifiedBatchesRef.current.has(batchId)) {
      setTimeout(() => {
        toast.success(`Batch #${batchId.slice(-8)} processed successfully!`);
      }, 0);
      notifiedBatchesRef.current.add(batchId);
    }
  };

  // ✅ FIX: Helper to consistently update results for a batch with deduplication
  const updateResultsForBatch = (batchId: string, results: ScanResult[]) => {
    setScanResults(prev => {
      // Remove old results for this batch
      const filtered = prev.filter(r => r.batch_id !== batchId);

      // ✅ FIX: Deduplicate new results by ID (prevent duplicates if called twice)
      const newResultsMap = new Map<string, ScanResult>();
      results.forEach(result => {
        newResultsMap.set(result.id, result);
      });
      const deduplicatedResults = Array.from(newResultsMap.values());

      // Add deduplicated new results at the beginning
      return [...deduplicatedResults, ...filtered];
    });
  };

  const uploadDocuments = async (files: File[], documentTypes: string[]): Promise<Batch> => {
    try {
      // ✅ FIX: DON'T set loading=true - this blocks UI!
      // Background data loading should not interfere with upload
      console.log('📤 Starting upload...');
      const batch = await apiService.uploadDocuments(files, documentTypes);

      // Update batches - add new batch at the beginning
      setBatches(prev => {
        console.log('📝 Adding new batch to state. Prev length:', prev.length);
        const newBatches = [batch, ...prev];
        console.log('📝 New batches length:', newBatches.length);
        return newBatches;
      });

      // Start polling for updates
      pollBatchStatus(batch.id);

      setTimeout(() => {
        toast.success(`Batch ${batch.id.slice(-8)} created with ${files.length} files`);
      }, 0);
      return batch;
    } catch (error: any) {
      console.error('Upload error:', error);

      // Extract error message properly from the response
      let errorMessage = 'Failed to upload documents';

      if (error.response?.data) {
        const errorData = error.response.data;

        // Handle complex error object from backend validation
        if (errorData.message) {
          errorMessage = errorData.message;
        } else if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (errorData.validation_summary) {
          // Handle validation summary with failed files
          const failedCount = errorData.failed_files?.length || 0;
          errorMessage = `${failedCount} file(s) failed validation. ${errorData.validation_summary}`;
        }
      } else if (error.message) {
        errorMessage = error.message;
      }

      setTimeout(() => {
        toast.error(errorMessage);
      }, 0);
      throw error;
    }
    // ✅ FIX: No finally block setting loading=false
    // Upload should never block UI with loading state
  };

  const pollBatchStatus = async (batchId: string) => {
    console.log(`🚀 Starting polling for batch ${batchId.slice(-8)}`);

    // ✅ FIX: Stop existing polling for this batch if any
    const existingCleanup = pollingCleanupRef.current.get(batchId);
    if (existingCleanup) {
      console.log(`⚠️ Stopping existing poll for batch ${batchId.slice(-8)}`);
      existingCleanup();
    }

    // ✅ FIX: Create cancellation flag for this specific poll
    let cancelled = false;

    const pollInterval = setInterval(async () => {
      // ✅ FIX: Check both mounted status and cancellation flag
      if (!isMountedRef.current || cancelled) {
        console.log(`⚠️ Stopping polling for batch ${batchId.slice(-8)} (unmounted=${!isMountedRef.current}, cancelled=${cancelled})`);
        clearInterval(pollInterval);
        return;
      }

      console.log(`🔄 Polling batch ${batchId.slice(-8)}...`);

      try {
        const updatedBatch = await apiService.getBatchStatus(batchId);
        console.log(`📡 Batch ${batchId.slice(-8)} status:`, updatedBatch.status);

        // ✅ FIX: Check again after async operation
        if (!isMountedRef.current || cancelled) {
          clearInterval(pollInterval);
          return;
        }

        // Update batch status
        setBatches(prev => {
          console.log(`🔄 Polling update for batch ${batchId.slice(-8)}. Current batches:`, prev.length);
          const updated = prev.map(batch =>
            batch.id === batchId ? updatedBatch : batch
          );
          console.log(`🔄 After polling update, batches:`, updated.length);
          return updated;
        });

        if (updatedBatch.status === 'completed') {
          console.log(`✅ Batch ${batchId.slice(-8)} completed, loading results...`);
          clearInterval(pollInterval);
          pollingCleanupRef.current.delete(batchId);

          // ✅ FIX: Prevent duplicate result loading
          if (loadingBatchesRef.current.has(batchId)) {
            console.log(`⚠️ Already loading results for ${batchId.slice(-8)}, skipping...`);
            return;
          }

          loadingBatchesRef.current.add(batchId);

          // ✅ FIX: Simplified result loading with timeout
          const loadTimeout = setTimeout(() => {
            loadingBatchesRef.current.delete(batchId);
            console.error(`⏱️ Results loading timeout for ${batchId.slice(-8)}`);
          }, 30000); // 30 second max

          try {
            const results = await apiService.getBatchResults(batchId);

            // Final check before state update
            if (!isMountedRef.current || cancelled) {
              clearTimeout(loadTimeout);
              loadingBatchesRef.current.delete(batchId);
              return;
            }

            if (Array.isArray(results) && results.length > 0) {
              updateResultsForBatch(batchId, results);
              handleBatchCompletion(batchId);
              console.log(`✅ Loaded ${results.length} results for batch ${batchId.slice(-8)}`);
            } else {
              console.warn(`⚠️ No results returned for batch ${batchId.slice(-8)}`);
              setTimeout(() => {
                toast.error(`No results found for batch ${batchId.slice(-8)}. Please refresh.`, {
                  duration: 6000,
                });
              }, 0);
            }
          } catch (error) {
            console.error(`❌ Failed to load results for ${batchId.slice(-8)}:`, error);
          } finally {
            clearTimeout(loadTimeout);
            loadingBatchesRef.current.delete(batchId);
          }
        }
        else if (updatedBatch.status === 'error') {
          console.log(`❌ Batch ${batchId.slice(-8)} failed`);
          clearInterval(pollInterval);
          pollingCleanupRef.current.delete(batchId);

          if (isMountedRef.current && !cancelled) {
            setScanResults(prev => prev.filter(r => r.batch_id !== batchId));
          }
        }
      } catch (error) {
        console.error(`❌ Polling error for batch ${batchId.slice(-8)}:`, error);
        clearInterval(pollInterval);
        pollingCleanupRef.current.delete(batchId);
      }
    }, 5000); // Poll every 5 seconds (reduced from 2s to reduce server load)

    // ✅ FIX: Safety timeout (10 minutes for large rekening koran files)
    const stopTimeout = setTimeout(() => {
      console.log(`⏱️ Safety timeout for batch ${batchId.slice(-8)}`);
      cancelled = true;
      clearInterval(pollInterval);
      pollingCleanupRef.current.delete(batchId);
    }, 600000); // 10 minutes (increased from 5 for large files)

    // ✅ FIX: Register cleanup function that cancels everything
    const cleanup = () => {
      cancelled = true;
      clearInterval(pollInterval);
      clearTimeout(stopTimeout);
      pollingCleanupRef.current.delete(batchId);
    };

    pollingCleanupRef.current.set(batchId, cleanup);
    console.log(`✅ Polling registered for ${batchId.slice(-8)}. Active polls: ${pollingCleanupRef.current.size}`);
  };

  const refreshBatch = async (batchId: string) => {
    try {
      const updatedBatch = await apiService.getBatchStatus(batchId);
      setBatches(prev => {
        const batchExists = prev.some(batch => batch.id === batchId);
        if (batchExists) {
          // Update existing batch
          return prev.map(batch =>
            batch.id === batchId ? updatedBatch : batch
          );
        } else {
          // Add new batch if it doesn't exist (e.g., from ZIP upload navigation)
          return [...prev, updatedBatch];
        }
      });

      if (updatedBatch.status === 'completed') {
        const results = await apiService.getBatchResults(batchId);
        updateResultsForBatch(batchId, results);
        handleBatchCompletion(batchId);
      }
    } catch (error) {
      console.error('Refresh batch error:', error);
      setTimeout(() => {
        toast.error('Failed to refresh batch status');
      }, 0);
    }
  };

  const loadRecentBatchesOnly = async () => {
    try {
      // ✅ CRITICAL FIX: Set loading=false IMMEDIATELY - NO BLOCKING!
      // UI must be ready instantly, data loads in background
      setLoading(false);
      console.log('✅ UI ready IMMEDIATELY - upload button enabled (data loading in background)');

      // 🔄 Background data load - does NOT block UI
      setTimeout(async () => {
        try {
          console.log('🔄 Loading recent batches in background (non-blocking)...');

          // ✅ Load only 5 most recent batches first (ultra fast!)
          const recentBatches = await apiService.getAllBatches(5, 0);
          console.log(`✅ Loaded ${recentBatches.length} recent batches (background)`);
          setBatches(recentBatches);

          // Load results for recent batches only
          const recentResults = await apiService.getAllResults();
          const recentBatchIds = new Set(recentBatches.map(b => b.id));

          // ✅ FIX: Ensure recentResults is an array before filtering
          const resultsArray = Array.isArray(recentResults) ? recentResults : [];
          const filteredResults = resultsArray.filter(r => recentBatchIds.has(r.batch_id));
          setScanResults(filteredResults);

          console.log(`✅ Loaded ${filteredResults.length} scan results (background)`);

          console.log('⚡ Background data load complete');

          // Load remaining batches if there are more (even more background)
          if (recentBatches.length === 5) {
            setTimeout(async () => {
              try {
                console.log('🔄 Loading remaining batches (deep background)...');
                const allBatches = await apiService.getAllBatches();
                const remainingCount = allBatches.length - recentBatches.length;

                if (remainingCount > 0) {
                  console.log(`⚡ Loaded ${allBatches.length} total batches`);

                  // ✅ FIX: Merge with existing batches to preserve newly uploaded ones
                  setBatches(prev => {
                    // Create a map of existing batches by ID
                    const existingMap = new Map(prev.map(b => [b.id, b]));

                    // Merge: keep existing batches, add new ones from API
                    const merged = [...prev]; // Start with existing (includes new uploads)

                    allBatches.forEach(apiBatch => {
                      if (!existingMap.has(apiBatch.id)) {
                        // Only add if not already in state
                        merged.push(apiBatch);
                      }
                    });

                    console.log(`✅ Merged batches: ${prev.length} existing + ${merged.length - prev.length} new = ${merged.length} total`);
                    return merged;
                  });
                }
              } catch (bgError) {
                console.error('Deep background load failed (non-critical):', bgError);
              }
            }, 3000); // Load after 3 seconds (deep background)
          }
        } catch (error) {
          console.error('Background batch load error (non-critical):', error);
        }
      }, 100); // Start background load after 100ms (immediate but non-blocking)
    } catch (error) {
      console.error('Load initialization error:', error);
      setLoading(false);
    }
  };

  const refreshAllData = async () => {
    try {
      setLoading(true);

      // ✅ FIX: Clear all polling with proper cleanup functions
      console.log('🧹 Clearing all polling before refresh');
      pollingCleanupRef.current.forEach((cleanup, batchId) => {
        console.log(`🧹 Stopping poll for batch ${batchId.slice(-8)}`);
        cleanup();
      });
      pollingCleanupRef.current.clear();
      loadingBatchesRef.current.clear();

      // Use Promise.allSettled to handle partial failures gracefully
      const [batchesPromise, resultsPromise] = await Promise.allSettled([
        apiService.getAllBatches(),
        apiService.getAllResults()
      ]);

      if (batchesPromise.status === 'fulfilled' && Array.isArray(batchesPromise.value)) {
        console.log(`✅ Loaded ${batchesPromise.value.length} batches`);
        console.log('Batches data:', batchesPromise.value);
        setBatches(batchesPromise.value);

        // Debug: Log state after update
        setTimeout(() => {
          console.log('🔍 Batches state after update check');
        }, 100);
      } else if (batchesPromise.status === 'rejected') {
        console.error('❌ Failed to load batches:', batchesPromise.reason);
      }

      if (resultsPromise.status === 'fulfilled' && Array.isArray(resultsPromise.value)) {
        console.log(`✅ Loaded ${resultsPromise.value.length} results`);
        setScanResults(resultsPromise.value);
      } else if (resultsPromise.status === 'rejected') {
        console.error('❌ Failed to load results:', resultsPromise.reason);
      }

      // Only show error toast if both failed
      // Defer toast to avoid state update during render warning
      if (batchesPromise.status === 'rejected' && resultsPromise.status === 'rejected') {
        setTimeout(() => {
          toast.error('Failed to load data from server');
        }, 0);
      }
    } catch (error) {
      console.error('Refresh all data error:', error);
      // Defer toast to avoid state update during render warning
      setTimeout(() => {
        toast.error('Failed to load data from server');
      }, 0);
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
      setTimeout(() => {
        toast.success(`${format.toUpperCase()} download started`);
      }, 0);
    } catch (error) {
      console.error('Export error:', error);
      setTimeout(() => {
        toast.error(`Failed to export ${format.toUpperCase()}`);
      }, 0);
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
      setTimeout(() => {
        toast.success(`Batch ${format.toUpperCase()} download started`);
      }, 0);
    } catch (error) {
      console.error('Batch export error:', error);
      setTimeout(() => {
        toast.error('Failed to export batch');
      }, 0);
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
      setTimeout(() => {
        toast.success(`✅ Successfully saved to Google Drive as ${format.toUpperCase()}`);
      }, 0);
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

      setTimeout(() => {
        toast.error(errorMessage);
      }, 0);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const updateResult = async (resultId: string, updatedData: any): Promise<void> => {
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

      // Update local state with new data only if mounted
      if (isMountedRef.current) {
        setScanResults(prev => prev.map(result =>
          result.id === resultId
            ? {
                ...result,
                extracted_data: { ...result.extracted_data, ...sanitizedData },
                updated_at: response.updated_at
              }
            : result
        ));

        setTimeout(() => {
          toast.success('✅ Result updated successfully!');
        }, 0);
      }
    } catch (error: any) {
      console.error('Update result error:', error);
      const errorMessage = error.message || error.response?.data?.detail || 'Failed to update result';
      if (isMountedRef.current) {
        setTimeout(() => {
          toast.error(errorMessage);
        }, 0);
      }
      // Don't re-throw - handle error gracefully
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  };

  const deleteBatch = async (batchId: string): Promise<void> => {
    try {
      setLoading(true);

      // Call API to delete batch
      await apiService.deleteBatch(batchId);

      // Remove batch from local state
      setBatches(prev => prev.filter(batch => batch.id !== batchId));

      // Remove all results associated with this batch
      setScanResults(prev => prev.filter(result => result.batch_id !== batchId));

      console.log(`✅ Batch #${batchId.slice(-8)} deleted successfully`);
    } catch (error: any) {
      console.error('Delete batch error:', error);

      // Check if it's a 405 Method Not Allowed error
      if (error.response?.status === 405) {
        const errorMsg = 'Backend endpoint DELETE /api/batches/{batchId} belum tersedia. Hubungi administrator.';
        setTimeout(() => {
          toast.error(errorMsg);
        }, 0);
        throw new Error(errorMsg);
      }

      const errorMessage = error.response?.data?.detail || error.message || 'Gagal menghapus batch';
      setTimeout(() => {
        toast.error(errorMessage);
      }, 0);
      throw new Error(errorMessage);
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
      deleteBatch,
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