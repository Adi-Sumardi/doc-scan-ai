import React, { useState, useEffect, useRef } from 'react';
import {
  Brain,
  FileText,
  CheckCircle,
  AlertCircle,
  Loader2,
  Clock,
  Zap
} from 'lucide-react';
import { apiService } from '../services/api';

interface ImprovedScanAnimationProps {
  batchId: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
  className?: string;
}

interface FileProgress {
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
  message?: string;
}

interface BatchStatus {
  status: 'pending' | 'processing' | 'completed' | 'error';
  total_files: number;
  processed_files: number;
  failed_files: number;
  current_file?: string;
  eta_seconds?: number;
  error_message?: string;
}

const ImprovedScanAnimation: React.FC<ImprovedScanAnimationProps> = ({
  batchId,
  onComplete,
  onError,
  className = ''
}) => {
  const [batchStatus, setBatchStatus] = useState<BatchStatus>({
    status: 'pending',
    total_files: 0,
    processed_files: 0,
    failed_files: 0
  });
  const [fileProgress, setFileProgress] = useState<FileProgress[]>([]);
  const [overallProgress, setOverallProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Initializing...');
  const [showSuccess, setShowSuccess] = useState(false);
  const [showError, setShowError] = useState(false);
  const [isFadingOut, setIsFadingOut] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);

  // Log every render with current state values
  console.log('🔄 [ImprovedScanAnimation] RENDER:', {
    batchId,
    batchStatus,
    fileProgress: fileProgress.length,
    overallProgress,
    statusMessage,
    elapsedTime
  });

  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const hasCompletedRef = useRef(false);

  // Mount/Cleanup handler
  useEffect(() => {
    console.log('🚀 [ImprovedScanAnimation] Component MOUNTED');

    return () => {
      console.log('💀 [ImprovedScanAnimation] Component UNMOUNTING');
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, []);

  // Elapsed time counter - runs regardless of status
  useEffect(() => {
    timerIntervalRef.current = setInterval(() => {
      setElapsedTime((prev) => {
        const elapsed = prev + 1;
        console.log('⏰ [ImprovedScanAnimation] Timer update:', elapsed, 'seconds');
        return elapsed;
      });
    }, 1000);

    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, []); // Timer runs independently

  // Poll backend for batch status
  useEffect(() => {
    const pollBatchStatus = async () => {
      try {
        const batch = await apiService.getBatchStatus(batchId);

        console.log('📊 [ImprovedScanAnimation] Received batch data:', JSON.stringify(batch, null, 2));

        // Update batch status
        const newStatus: BatchStatus = {
          status: batch.status,
          total_files: batch.total_files || 0,
          processed_files: batch.processed_files || 0,
          failed_files: batch.failed_files || 0,
          current_file: batch.current_file,
          eta_seconds: batch.eta_seconds,
          error_message: batch.error_message
        };

        console.log('📊 [ImprovedScanAnimation] Parsed batch status:', JSON.stringify(newStatus, null, 2));
        console.log('📊 [ImprovedScanAnimation] About to setBatchStatus...');

        setBatchStatus(prevStatus => {
          console.log('✅ [ImprovedScanAnimation] setBatchStatus EXECUTING. Old:', prevStatus, 'New:', newStatus);
          return newStatus;
        });

        // Calculate overall progress
        if (newStatus.total_files > 0) {
          const progress = (newStatus.processed_files / newStatus.total_files) * 100;
          console.log('📊 [ImprovedScanAnimation] Setting overall progress:', progress);
          setOverallProgress(prevProgress => {
            console.log('✅ [ImprovedScanAnimation] setOverallProgress EXECUTING. Old:', prevProgress, 'New:', Math.min(progress, 100));
            return Math.min(progress, 100);
          });
        }

        // Update status message
        if (batch.status === 'processing') {
          if (batch.current_file) {
            setStatusMessage(`Processing: ${batch.current_file}`);
          } else {
            setStatusMessage(`Processing ${batch.processed_files + 1}/${batch.total_files} files...`);
          }
        } else if (batch.status === 'completed') {
          setStatusMessage('All documents processed successfully!');
        } else if (batch.status === 'error') {
          setStatusMessage(batch.error_message || 'Processing failed');
        }

        // Get file-level progress if available
        if (batch.results && Array.isArray(batch.results)) {
          console.log('📄 [ImprovedScanAnimation] Processing file list:', batch.results.length, 'files');
          const fileProgressData: FileProgress[] = batch.results.map((result: any) => ({
            filename: result.filename || result.original_filename || 'Unknown',
            status: result.status === 'completed' ? 'completed' :
                   result.status === 'error' ? 'error' :
                   result.status === 'processing' ? 'processing' : 'pending',
            progress: result.status === 'completed' ? 100 :
                     result.status === 'processing' ? 50 : 0,
            message: result.error_message
          }));
          console.log('📄 [ImprovedScanAnimation] File progress data:', fileProgressData);
          setFileProgress(fileProgressData);
        } else {
          console.warn('⚠️ [ImprovedScanAnimation] No results array in batch data');
        }

        // Handle completion
        if (batch.status === 'completed' && !hasCompletedRef.current) {
          console.log('🎉 [ImprovedScanAnimation] Batch COMPLETED! Triggering success sequence...');
          hasCompletedRef.current = true;
          setShowSuccess(true);
          setOverallProgress(100);

          // Clear polling
          if (pollingIntervalRef.current) {
            console.log('⏹️ [ImprovedScanAnimation] Stopping polling...');
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }

          // Show success for 1.5 seconds then fade out and call onComplete
          console.log('✨ [ImprovedScanAnimation] Starting success display...');
          setTimeout(() => {
            console.log('🌅 [ImprovedScanAnimation] Starting fade out...');
            setIsFadingOut(true);
            setTimeout(() => {
              console.log('✅ [ImprovedScanAnimation] Calling onComplete callback...');
              if (onComplete) {
                onComplete();
              }
            }, 500); // Reduced from 600ms to 500ms for faster transition
          }, 1500); // Reduced from 2000ms to 1500ms
        }

        // Handle error
        if (batch.status === 'error' && !hasCompletedRef.current) {
          hasCompletedRef.current = true;
          setShowError(true);

          // Clear polling
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }

          if (onError) {
            onError(batch.error_message || 'Processing failed');
          }
        }

      } catch (error: any) {
        console.error('Failed to poll batch status:', error);

        // Handle 404 - batch not found
        if (error.response?.status === 404) {
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          setShowError(true);
          setStatusMessage('Batch not found');
          if (onError) onError('Batch not found');
        }
      }
    };

    // Initial poll
    console.log('🚀 [ImprovedScanAnimation] Starting initial poll...');
    pollBatchStatus();

    // Poll every 500ms for faster updates (more responsive)
    pollingIntervalRef.current = setInterval(pollBatchStatus, 500);
    console.log('⏱️ [ImprovedScanAnimation] Polling interval set to 500ms');

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [batchId, onComplete, onError]);

  // Format time (seconds to mm:ss)
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div
      className={`bg-gradient-to-br from-gray-50 to-blue-50 rounded-lg p-8 shadow-xl border border-gray-200 relative overflow-hidden ${className}`}
      style={{
        opacity: isFadingOut ? 0 : 1,
        transform: isFadingOut ? 'scale(0.95)' : 'scale(1)',
        transition: 'opacity 0.6s ease-out, transform 0.6s ease-out'
      }}
    >
      {/* Simplified Background - Only 10 particles */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-30">
        {Array.from({ length: 10 }).map((_, i) => (
          <div
            key={i}
            className="absolute rounded-full bg-blue-400"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              width: `${4 + Math.random() * 4}px`,
              height: `${4 + Math.random() * 4}px`,
              animation: `floatUpDown ${4 + i * 0.5}s ease-in-out infinite`,
              animationDelay: `${i * 0.2}s`,
              filter: 'blur(1px)'
            }}
          />
        ))}
      </div>

      {/* Success Confetti */}
      {showSuccess && (
        <div className="absolute inset-0 pointer-events-none z-50">
          {Array.from({ length: 30 }).map((_, i) => (
            <div
              key={`confetti-${i}`}
              className="absolute w-2 h-2 rounded-full animate-confetti"
              style={{
                left: `${Math.random() * 100}%`,
                top: '-10px',
                backgroundColor: ['#10B981', '#3B82F6', '#8B5CF6', '#F59E0B'][i % 4],
                animationDelay: `${Math.random() * 0.3}s`,
                animationDuration: `${Math.random() * 1.5 + 1}s`
              }}
            />
          ))}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6 relative z-10">
        <div className="flex items-center space-x-3">
          <div className="relative">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center shadow-lg transition-all duration-300 ${
                showSuccess ? 'bg-gradient-to-r from-green-500 to-emerald-500' :
                showError ? 'bg-gradient-to-r from-red-500 to-pink-500' :
                'bg-gradient-to-r from-purple-500 to-blue-500'
              }`}
              style={{
                animation: showError ? 'shake 0.5s ease-in-out' :
                          showSuccess ? 'bounce-once 0.6s ease-out' :
                          'pulse 2s ease-in-out infinite'
              }}
            >
              {showSuccess ? (
                <CheckCircle className="w-6 h-6 text-white" />
              ) : showError ? (
                <AlertCircle className="w-6 h-6 text-white" />
              ) : (
                <Brain className="w-6 h-6 text-white" />
              )}
            </div>
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-800">
              {showSuccess ? 'Processing Complete!' :
               showError ? 'Processing Failed' :
               'AI Document Scanner'}
            </h3>
            <p className="text-sm text-gray-600">
              {batchStatus.total_files > 0 ?
                `${batchStatus.processed_files} of ${batchStatus.total_files} files` :
                'Preparing...'}
            </p>
          </div>
        </div>

        {/* Timer and ETA */}
        <div className="text-right">
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
            <Clock className="w-4 h-4" />
            <span>{formatTime(elapsedTime)}</span>
          </div>
          {batchStatus.eta_seconds && batchStatus.eta_seconds > 0 && (
            <div className="flex items-center gap-2 text-xs text-blue-600">
              <Zap className="w-3 h-3" />
              <span>ETA: {formatTime(batchStatus.eta_seconds)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Overall Progress */}
      <div className="mb-6 relative z-10">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">Overall Progress</span>
          <span className="text-sm font-bold text-blue-600">{Math.round(overallProgress)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden shadow-inner">
          <div
            className={`h-3 rounded-full transition-all duration-500 relative overflow-hidden ${
              showSuccess ? 'bg-gradient-to-r from-green-500 to-emerald-500' :
              showError ? 'bg-gradient-to-r from-red-500 to-pink-500' :
              'bg-gradient-to-r from-purple-500 via-blue-500 to-indigo-500'
            }`}
            style={{ width: `${overallProgress}%` }}
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer" />
          </div>
        </div>
      </div>

      {/* Status Message */}
      <div className="text-center mb-6 relative z-10">
        <p className="text-base font-medium text-gray-800 flex items-center justify-center gap-2">
          {!showSuccess && !showError && (
            <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
          )}
          {statusMessage}
        </p>
      </div>

      {/* File Progress List */}
      {fileProgress.length > 0 && (
        <div className="relative z-10 max-h-64 overflow-y-auto space-y-2 bg-white/50 rounded-lg p-4">
          {fileProgress.map((file, index) => (
            <div
              key={index}
              className={`flex items-center gap-3 p-3 rounded-lg transition-all duration-300 ${
                file.status === 'completed' ? 'bg-green-50 border border-green-200' :
                file.status === 'error' ? 'bg-red-50 border border-red-200' :
                file.status === 'processing' ? 'bg-blue-50 border border-blue-200' :
                'bg-gray-50 border border-gray-200'
              }`}
              style={{
                animation: file.status === 'processing' ? 'pulse 2s ease-in-out infinite' : 'none'
              }}
            >
              {/* Icon */}
              <div className="flex-shrink-0">
                {file.status === 'completed' ? (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                ) : file.status === 'error' ? (
                  <AlertCircle className="w-5 h-5 text-red-600" />
                ) : file.status === 'processing' ? (
                  <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                ) : (
                  <FileText className="w-5 h-5 text-gray-400" />
                )}
              </div>

              {/* Filename and Progress */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">
                  {file.filename}
                </p>
                {file.message && (
                  <p className="text-xs text-gray-500 truncate">{file.message}</p>
                )}
              </div>

              {/* Status Badge */}
              <div className="flex-shrink-0">
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                  file.status === 'completed' ? 'bg-green-100 text-green-700' :
                  file.status === 'error' ? 'bg-red-100 text-red-700' :
                  file.status === 'processing' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {file.status === 'completed' ? 'Done' :
                   file.status === 'error' ? 'Failed' :
                   file.status === 'processing' ? 'Processing' :
                   'Pending'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Success Message */}
      {showSuccess && (
        <div className="mt-4 text-center relative z-10 animate-fade-in-up">
          <p className="text-green-600 font-medium">
            Successfully processed {batchStatus.processed_files} document(s)!
          </p>
        </div>
      )}

      {/* Error Message */}
      {showError && (
        <div className="mt-4 text-center relative z-10 animate-shake">
          <p className="text-red-600 font-medium">
            {batchStatus.error_message || 'Processing failed. Please try again.'}
          </p>
          {batchStatus.failed_files > 0 && (
            <p className="text-sm text-gray-600 mt-1">
              {batchStatus.failed_files} file(s) failed to process
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default ImprovedScanAnimation;