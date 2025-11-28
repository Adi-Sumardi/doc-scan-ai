import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDocument } from '../context/DocumentContext';
import OCRMetricsDisplay from '../components/OCRMetricsDisplay';
import ImprovedScanAnimation from '../components/ImprovedScanAnimation';
import DocumentPreview from '../components/DocumentPreview';
import EditableOCRResult from '../components/EditableOCRResult';
import { 
  ArrowLeft, 
  Download, 
  FileText, 
  CheckCircle, 
  Clock,
  AlertCircle,
  Brain,
  Database,
  Share2,
  Edit3,
  Save,
  X,
  Maximize2
} from 'lucide-react';

const ScanResults = () => {
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { getBatch, getScanResultsByBatch, exportResult, exportBatch, saveToGoogleDrive, refreshBatch, updateResult, loading } = useDocument();
  const [activeTab, setActiveTab] = useState(0);
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState<any>(null);
  const [showAnimation, setShowAnimation] = useState(false);

  const batch = getBatch(batchId!);
  const resultsForBatch = getScanResultsByBatch(batchId!);
  const scanResults = Array.isArray(resultsForBatch) ? resultsForBatch : [];
  
  // Check if just uploaded from location state
  const justUploaded = location.state?.justUploaded;

  // Debug info for development only
  if (import.meta.env.DEV) {
    console.log('🔍 ScanResults - Batch Data:', batch);
    console.log('🔍 ScanResults - Scan Results:', scanResults);
    console.log('🔍 ScanResults - Just Uploaded:', justUploaded);
    console.log('🔍 ScanResults - Show Animation:', showAnimation);
  }

  // Determine if we should show animation on mount
  useEffect(() => {
    if (batchId) {
      console.log('🔄 ScanResults - Initial load, refreshing batch...');
      refreshBatch(batchId);
      
      // Show animation if just uploaded or if batch is processing
      if (justUploaded) {
        console.log('✅ ScanResults - Just uploaded, showing animation');
        setShowAnimation(true);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId]); // Only re-run if batchId changes
  
  // Update animation state based on batch status
  useEffect(() => {
    if (batch) {
      console.log('📊 ScanResults - Batch status changed:', batch.status);
      
      // Show animation if batch is pending or processing
      if (batch.status === 'pending' || batch.status === 'processing') {
        setShowAnimation(true);
      } else if (batch.status === 'completed' && scanResults.length > 0) {
        // Hide animation when completed AND results are loaded
        console.log('✅ ScanResults - Completed with results, hiding animation');
        setShowAnimation(false);
      }
    }
  }, [batch?.status, scanResults.length]);

  // Poll for results when batch is completed but no results yet (handles delay between completion and results)
  useEffect(() => {
    if (batch?.status === 'completed' && scanResults.length === 0) {
      console.log('⏳ Batch completed but results not yet available. Polling for results...');
      const pollInterval = setInterval(() => {
        refreshBatch(batchId!);
      }, 2000); // Poll every 2 seconds

      // Stop polling after 30 seconds (results should be available by then)
      const stopPollingTimeout = setTimeout(() => {
        clearInterval(pollInterval);
        console.log('⚠️ Stopped polling for results after 30 seconds');
      }, 30000);

      return () => {
        clearInterval(pollInterval);
        clearTimeout(stopPollingTimeout);
      };
    }
  }, [batch?.status, scanResults.length, batchId, refreshBatch]);

  // Reset activeTab if results change to prevent out-of-bounds access
  useEffect(() => {
    if (resultsForBatch.length > 0 && activeTab >= resultsForBatch.length) {
      setActiveTab(0);
    }
  }, [resultsForBatch, activeTab]);

  if (!batch) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Batch not found</h3>
          <p className="text-gray-600">The requested batch could not be found.</p>
        </div>
      </div>
    );
  }

  const handleDownload = async (format: 'excel' | 'pdf', result?: any) => {
    if (result) {
      await exportResult(result.id, format);
    } else {
      await exportBatch(batchId!, format);
    }
  };

  const handleGoogleDriveShare = async (format: 'excel' | 'pdf', result?: any) => {
    if (result) {
      await saveToGoogleDrive(result.id, format);
    }
  };

  const handleSaveEdit = async () => {
    try {
      if (!editedData || scanResults.length === 0) return;
      
      const currentResult = scanResults[activeTab];
      await updateResult(currentResult.id, editedData);
      
      setIsEditing(false);
      setEditedData(null);
      
      // Refresh batch to get updated data from backend
      await refreshBatch(batchId!);
    } catch (error) {
      console.error('Save edit failed:', error);
      // Error toast already shown in updateResult
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedData(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg p-4 md:p-6 shadow-sm border">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center space-x-3 md:space-x-4">
            <button
              onClick={() => navigate(-1)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="min-w-0">
              <h1 className="text-xl md:text-2xl lg:text-3xl font-bold text-gray-900 truncate">Scan Results</h1>
              <p className="text-sm md:text-base text-gray-600 mt-1 truncate">Batch #{batchId?.slice(-8)} - {batch.total_files} files</p>
            </div>
          </div>
          <div className="flex items-center justify-end sm:justify-start">
            {batch.status === 'completed' ? (
              <div className="flex items-center space-x-2 text-green-600">
                <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5" />
                <span className="font-medium text-sm sm:text-base">Completed</span>
              </div>
            ) : batch.status === 'processing' ? (
              <div className="flex items-center space-x-2 text-yellow-600">
                <Clock className="w-4 h-4 sm:w-5 sm:h-5 processing-animation" />
                <span className="font-medium text-sm sm:text-base">Processing...</span>
              </div>
            ) : (
              <div className="flex items-center space-x-2 text-red-600">
                <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5" />
                <span className="font-medium text-sm sm:text-base">Error</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Real-time Scan Animation - Show when processing or just uploaded */}
      {(showAnimation && (batch.status === 'pending' || batch.status === 'processing')) ? (
        <ImprovedScanAnimation
          batchId={batchId!}
          onComplete={() => {
            console.log('✅ ScanResults - Animation onComplete triggered');
            refreshBatch(batchId!);
            // Animation will auto-hide when batch completes and results load
          }}
          onError={(error) => {
            console.error('❌ ScanResults - Processing error:', error);
            setShowAnimation(false);
            toast.error('Processing failed: ' + error);
          }}
          className="mb-6"
        />
      ) : batch.status === 'completed' && scanResults.length > 0 ? (
        <div
          className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-4 md:p-6 border border-green-200"
          style={{
            animation: 'fadeInUp 0.8s ease-out, scaleIn 0.8s ease-out'
          }}
        >
          <div className="flex items-center space-x-3 mb-4">
            <CheckCircle className="w-5 h-5 md:w-6 md:h-6 text-green-600 flex-shrink-0" />
            <h3 className="text-base md:text-lg font-semibold text-green-900">AI DocScan Processing Complete</h3>
          </div>
          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-green-700">
                {batch.processed_files} of {batch.total_files} files processed
              </span>
              <span className="text-sm text-green-600">100% Complete</span>
            </div>
            <div className="w-full bg-green-100 rounded-full h-3">
              <div className="bg-gradient-to-r from-green-500 to-blue-500 h-3 rounded-full" style={{ width: '100%' }} />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center space-x-2">
              <Brain className="w-5 h-5 text-green-600" />
              <span className="text-sm text-green-700">High Accuracy Achieved</span>
            </div>
            <div className="flex items-center space-x-2">
              <Database className="w-5 h-5 text-blue-600" />
              <span className="text-sm text-blue-700">Data Extracted</span>
            </div>
            <div className="flex items-center space-x-2">
              <FileText className="w-5 h-5 text-purple-600" />
              <span className="text-sm text-purple-700">Ready for Export</span>
            </div>
          </div>
        </div>
      ) : null}

      {/* Results */}
      {scanResults.length > 0 && (
        <div
          className="bg-white rounded-lg shadow-sm border"
          style={{
            animation: 'fadeInUp 1s ease-out 0.3s both'
          }}
        >
          <div className="p-6 border-b">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Extracted Data</h3>
              <div className="flex flex-col sm:flex-row gap-2">
                <button
                  onClick={() => handleDownload('excel')}
                  disabled={loading}
                  className="px-3 md:px-4 py-2 success-gradient text-white rounded-lg hover:shadow-lg transition-all duration-200 text-sm md:text-base"
                >
                  <Download className="w-4 h-4 inline mr-1 md:mr-2" />
                  <span className="hidden sm:inline">Download All</span> (Excel)
                </button>
                <button
                  onClick={() => handleDownload('pdf')}
                  disabled={loading}
                  className="px-3 md:px-4 py-2 error-gradient text-white rounded-lg hover:shadow-lg transition-all duration-200 text-sm md:text-base"
                >
                  <Download className="w-4 h-4 inline mr-1 md:mr-2" />
                  <span className="hidden sm:inline">Download All</span> (PDF)
                </button>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b">
            <nav className="flex overflow-x-auto px-4 md:px-6 -mb-px">
              <div className="flex space-x-4 md:space-x-8 min-w-max">
                {scanResults.map((result, index) => (
                  <button
                    key={result.id}
                    onClick={() => setActiveTab(index)}
                    className={`py-3 md:py-4 text-xs md:text-sm font-medium border-b-2 whitespace-nowrap flex-shrink-0 ${
                      activeTab === index
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    <span className="max-w-[120px] md:max-w-none truncate block">{result.filename}</span>
                  </button>
                ))}
              </div>
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {/* Batch Summary */}
            <div className="mb-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-3 md:p-4 border border-blue-200">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold text-blue-600">{scanResults.length}</div>
                  <div className="text-sm text-blue-700">Files Processed</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-600">
                    {[...new Set(scanResults.map(r => r.document_type || r.file_type))].length}
                  </div>
                  <div className="text-sm text-green-700">Document Types</div>
                </div>
              </div>
            </div>

            {/* Add a guard to prevent crashing if the active tab is out of bounds */}
            {scanResults.length > 0 && scanResults[activeTab] ? (
              <div className="space-y-6">
                {/* File Info & Actions */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <FileText className="w-6 h-6 text-blue-600" />
                    <div>
                      <h4 className="font-medium text-gray-900">{scanResults[activeTab]?.filename || 'Unknown'}</h4>
                      <p className="text-sm text-gray-600">Confidence: {((scanResults[activeTab]?.confidence ?? scanResults[activeTab]?.confidence_score ?? 0) * 100).toFixed(1)}%</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {isEditing ? (
                      <>
                        <button
                          onClick={handleSaveEdit}
                          className="px-2 md:px-3 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors text-xs md:text-sm font-medium"
                        >
                          <Save className="w-3 h-3 md:w-4 md:h-4 inline mr-1" />
                          Save
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="px-2 md:px-3 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors text-xs md:text-sm font-medium"
                        >
                          <X className="w-3 h-3 md:w-4 md:h-4 inline mr-1" />
                          Cancel
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => {
                            setIsEditing(true);
                            setEditedData(scanResults[activeTab].extracted_data);
                          }}
                          className="px-2 md:px-3 py-2 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 transition-colors text-xs md:text-sm font-medium"
                        >
                          <Edit3 className="w-3 h-3 md:w-4 md:h-4 inline mr-1" />
                          Edit
                        </button>
                        <button
                          onClick={() => handleDownload('excel', scanResults[activeTab])}
                          disabled={loading}
                          className="px-2 md:px-3 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors text-xs md:text-sm"
                        >
                          <Download className="w-3 h-3 md:w-4 md:h-4 inline mr-1" />
                          Excel
                        </button>
                        <button
                          onClick={() => handleDownload('pdf', scanResults[activeTab])}
                          disabled={loading}
                          className="px-2 md:px-3 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors text-xs md:text-sm"
                        >
                          <Download className="w-3 h-3 md:w-4 md:h-4 inline mr-1" />
                          PDF
                        </button>
                        <button
                          onClick={() => handleGoogleDriveShare('excel', scanResults[activeTab])}
                          disabled={loading}
                          className="px-2 md:px-3 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors text-xs md:text-sm"
                        >
                          <Share2 className="w-3 h-3 md:w-4 md:h-4 inline mr-1" />
                          <span className="hidden sm:inline">Save to</span> Drive
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Next-Generation OCR Metrics */}
                {scanResults[activeTab].nextgen_metrics && (
                  <OCRMetricsDisplay 
                    metrics={scanResults[activeTab].nextgen_metrics}
                    quality={scanResults[activeTab].processing_quality}
                    className="mb-6"
                  />
                )}

                {/* Split View */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Left: Document Preview */}
                  <div className="bg-gray-50 rounded-lg border p-4">
                    <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                      <Maximize2 className="w-5 h-5 mr-2 text-blue-600" />
                      Document Preview
                    </h4>
                    <DocumentPreview
                      resultId={scanResults[activeTab].id}
                      fileName={scanResults[activeTab].filename}
                      fileType={scanResults[activeTab].file_type || 'pdf'}
                    />
                  </div>

                  {/* Right: Editable OCR Result */}
                  <div className="bg-white rounded-lg border p-4">
                    <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                      <FileText className="w-5 h-5 mr-2 text-green-600" />
                      Extracted Data {isEditing && <span className="text-sm text-orange-600 ml-2">(Editing Mode)</span>}
                    </h4>
                    <EditableOCRResult
                      result={scanResults[activeTab]}
                      isEditing={isEditing}
                      onToggleEdit={() => setIsEditing(!isEditing)}
                      onSave={handleSaveEdit}
                    />
                  </div>
                </div>

              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>Select a file to view its details.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Loading Results Animation (when batch completed but results not yet loaded) */}
      {batch.status === 'completed' && scanResults.length === 0 && (
        <div className="bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 rounded-lg p-12 shadow-lg border border-blue-200">
          <div className="text-center">
            {/* Animated Brain Icon */}
            <div className="mb-6 relative inline-block">
              <div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-purple-400 rounded-full blur-xl opacity-50 animate-pulse" />
              <Brain className="w-20 h-20 text-blue-600 mx-auto relative animate-bounce" />
            </div>

            {/* Processing Title */}
            <h3 className="text-2xl font-bold text-gray-900 mb-3 animate-fade-in">
              Processing Smart Mapper AI
            </h3>

            {/* Subtitle */}
            <p className="text-gray-700 mb-6 text-lg animate-fade-in-delayed">
              Finalizing extracted data and preparing results...
            </p>

            {/* Loading Bar */}
            <div className="max-w-md mx-auto mb-6">
              <div className="w-full bg-blue-100 rounded-full h-3 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 rounded-full animate-loading-bar"
                  style={{
                    animation: 'loading-bar 2s ease-in-out infinite'
                  }}
                />
              </div>
            </div>

            {/* Status Steps */}
            <div className="flex justify-center space-x-8 text-sm">
              <div className="flex items-center space-x-2 text-green-600">
                <CheckCircle className="w-5 h-5" />
                <span>OCR Complete</span>
              </div>
              <div className="flex items-center space-x-2 text-blue-600">
                <Clock className="w-5 h-5 animate-spin" />
                <span>Loading Results</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ScanResults;