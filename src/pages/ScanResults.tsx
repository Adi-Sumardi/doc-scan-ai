import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDocument } from '../context/DocumentContext';
import OCRMetricsDisplay from '../components/OCRMetricsDisplay';
import RealtimeOCRProcessing from '../components/RealtimeOCRProcessing';
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
  Maximize2,
  Columns
} from 'lucide-react';

const ScanResults = () => {
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const { getBatch, getScanResultsByBatch, exportResult, exportBatch, saveToGoogleDrive, refreshBatch, updateResult, loading } = useDocument();
  const [activeTab, setActiveTab] = useState(0);
  const [viewMode, setViewMode] = useState<'split' | 'list'>('split');
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState<any>(null);

  const batch = getBatch(batchId!);
  const resultsForBatch = getScanResultsByBatch(batchId!);
  const scanResults = Array.isArray(resultsForBatch) ? resultsForBatch : [];

  // Debug info for development
  console.log('Batch Data:', batch);
  console.log('Scan Results:', scanResults);

  // Automatically refresh batch data when the component mounts
  useEffect(() => {
    if (batchId) {
      refreshBatch(batchId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId]); // Only re-run if batchId changes

  // Reset activeTab if results change to prevent out-of-bounds access
  useEffect(() => {
    if (activeTab >= resultsForBatch.length) {
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

  const toggleViewMode = () => {
    setViewMode(prev => prev === 'split' ? 'list' : 'split');
  };

  const renderRawScanData = (result: any) => {
    const extractedData = result.extracted_data || {};
    const confidence = result.confidence || result.confidence_score || 0;
    
    return (
      <div className="space-y-6">
        {/* Raw OCR Text - Primary Focus */}
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 md:p-6">
          <h4 className="text-base md:text-lg font-semibold text-red-900 mb-3 md:mb-4 flex items-center">
            <FileText className="w-4 h-4 md:w-5 md:h-5 mr-2 flex-shrink-0" />
            📄 RAW OCR TEXT (PURE SCAN RESULTS)
          </h4>
          <div className="bg-white border rounded-lg p-4">
            <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed max-h-96 overflow-y-auto">
              {extractedData?.raw_text || 'No raw OCR text available'}
            </pre>
          </div>
          <div className="mt-3 md:mt-4 grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 text-xs md:text-sm">
            <div className="bg-white rounded-lg p-2 md:p-3 border">
              <div className="text-gray-600 text-xs md:text-sm">Characters</div>
              <div className="font-semibold text-blue-600 text-sm md:text-base">
                {extractedData?.extracted_content?.character_count || extractedData?.raw_text?.length || 0}
              </div>
            </div>
            <div className="bg-white rounded-lg p-2 md:p-3 border">
              <div className="text-gray-600 text-xs md:text-sm">Lines</div>
              <div className="font-semibold text-green-600 text-sm md:text-base">
                {extractedData?.extracted_content?.line_count || extractedData?.text_lines?.length || 0}
              </div>
            </div>
            <div className="bg-white rounded-lg p-2 md:p-3 border">
              <div className="text-gray-600 text-xs md:text-sm">Confidence</div>
              <div className="font-semibold text-purple-600 text-sm md:text-base">
                {(confidence * 100).toFixed(1)}%
              </div>
            </div>
            <div className="bg-white rounded-lg p-2 md:p-3 border">
              <div className="text-gray-600 text-xs md:text-sm">Document Type</div>
              <div className="font-semibold text-orange-600 text-sm md:text-base capitalize">
                {result.document_type || 'Unknown'}
              </div>
            </div>
          </div>
        </div>

        {/* Text Lines */}
        {extractedData?.text_lines && extractedData.text_lines.length > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 md:p-6">
            <h4 className="text-base md:text-lg font-semibold text-green-900 mb-3 md:mb-4">
              Extracted Lines ({extractedData.text_lines.length})
            </h4>
            <div className="bg-white border rounded-lg p-3 md:p-4 max-h-64 md:max-h-96 overflow-y-auto">
              {extractedData.text_lines.map((line: string, index: number) => (
                <div key={index} className="flex items-start space-x-3 py-2 border-b border-gray-100 last:border-b-0">
                  <span className="text-xs text-gray-500 w-8 flex-shrink-0 mt-1">{index + 1}</span>
                  <span className="text-sm text-gray-800 font-mono">{line || '(empty line)'}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Processing Information */}
        {extractedData?.processing_info && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 md:p-6">
            <h4 className="text-base md:text-lg font-semibold text-gray-900 mb-3 md:mb-4">
              Processing Information
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
              {Object.entries(extractedData.processing_info).map(([key, value]: [string, any]) => (
                <div key={key} className="bg-white rounded-lg p-4 border">
                  <div className="text-gray-600 text-sm capitalize">{key.replace(/_/g, ' ')}</div>
                  <div className="font-semibold text-gray-900 mt-1">
                    {String(value)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Document Metadata */}
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 md:p-6">
          <h4 className="text-base md:text-lg font-semibold text-purple-900 mb-3 md:mb-4">
            Document Information
          </h4>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 md:gap-4">
            <div className="bg-white rounded-lg p-4 border">
              <div className="text-gray-600 text-sm">Document Type</div>
              <div className="font-semibold text-purple-600 mt-1">
                {extractedData?.document_type || result.document_type || 'Unknown'}
              </div>
            </div>
            <div className="bg-white rounded-lg p-4 border">
              <div className="text-gray-600 text-sm">Scan Timestamp</div>
              <div className="font-semibold text-purple-600 mt-1">
                {extractedData?.extracted_content?.scan_timestamp || new Date(result.created_at).toLocaleString()}
              </div>
            </div>
            <div className="bg-white rounded-lg p-4 border">
              <div className="text-gray-600 text-sm">OCR Engine</div>
              <div className="font-semibold text-purple-600 mt-1">
                {result.ocr_engine_used || 'Standard OCR'}
              </div>
            </div>
            <div className="bg-white rounded-lg p-4 border">
              <div className="text-gray-600 text-sm">Processing Time</div>
              <div className="font-semibold text-purple-600 mt-1">
                {result.ocr_processing_time ? `${result.ocr_processing_time.toFixed(2)}s` : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
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

      {/* Real-time OCR Processing */}
      {batch.status === 'processing' ? (
        <RealtimeOCRProcessing 
          batchId={batchId!}
          onComplete={() => refreshBatch(batchId!)}
          className="mb-6"
        />
      ) : (
        <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-4 md:p-6 border border-green-200">
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
      )}

      {/* Results */}
      {scanResults.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-6 border-b">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Extracted Data</h3>
              <div className="flex flex-col sm:flex-row gap-2">
                <button
                  onClick={toggleViewMode}
                  className="px-3 md:px-4 py-2 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 transition-all duration-200 text-sm md:text-base font-medium"
                >
                  {viewMode === 'split' ? (
                    <>
                      <FileText className="w-4 h-4 inline mr-1 md:mr-2" />
                      List View
                    </>
                  ) : (
                    <>
                      <Columns className="w-4 h-4 inline mr-1 md:mr-2" />
                      Split View
                    </>
                  )}
                </button>
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
                <div>
                  <div className="text-2xl font-bold text-purple-600">
                    {(scanResults.reduce((sum, r) => sum + ((r.confidence || r.confidence_score || 0)), 0) / scanResults.length * 100).toFixed(1)}%
                  </div>
                  <div className="text-sm text-purple-700">Average Confidence</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-orange-600">Raw OCR</div>
                  <div className="text-sm text-orange-700">No Regex Processing</div>
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
                      <h4 className="font-medium text-gray-900">{scanResults[activeTab]?.filename}</h4>
                      <p className="text-sm text-gray-600">Confidence: {((scanResults[activeTab]?.confidence || scanResults[activeTab]?.confidence_score || 0) * 100).toFixed(1)}%</p>
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

                {/* Split View or List View */}
                {viewMode === 'split' ? (
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
                ) : (
                  /* List View - Raw Scan Data */
                  renderRawScanData(scanResults[activeTab])
                )}

                {/* Raw JSON Data (Optional) */}
                <div className="mt-8">
                  <details className="bg-gray-50 rounded-lg border">
                    <summary className="p-4 cursor-pointer font-medium text-gray-700 hover:bg-gray-100 rounded-lg">
                      � Complete Raw Data (Developer View)
                    </summary>
                    <div className="p-4 pt-0">
                      <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-xs overflow-auto max-h-96">
                        <pre>{JSON.stringify(scanResults[activeTab], null, 2)}</pre>
                      </div>
                    </div>
                  </details>
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

      {/* No Results */}
      {batch.status === 'completed' && scanResults.length === 0 && (
        <div className="bg-white rounded-lg p-12 shadow-sm border text-center">
          <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No scan results available</h3>
          <p className="text-gray-600">The processing completed but no results were generated.</p>
        </div>
      )}
    </div>
  );
};

export default ScanResults;