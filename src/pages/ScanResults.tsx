import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDocument } from '../context/DocumentContext';
import AIDataDisplay from '../components/AIDataDisplay';
import { AIDataFormatter } from '../utils/aiDataFormatter';
import { 
  ArrowLeft, 
  Download, 
  FileText, 
  CheckCircle, 
  Clock,
  AlertCircle,
  Brain,
  Database,
  Share2
} from 'lucide-react';

const ScanResults = () => {
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();
  const { getBatch, getScanResultsByBatch, exportResult, exportBatch, saveToGoogleDrive, refreshBatch, loading } = useDocument();
  const [activeTab, setActiveTab] = useState(0);

  const batch = getBatch(batchId!);
  const scanResults = getScanResultsByBatch(batchId!);

  // SUPER DEBUG: Log batch and scan results
  console.log('🔍 SUPER DEBUG - Batch Data:', batch);
  console.log('🔍 SUPER DEBUG - All Scan Results:', scanResults);
  console.log('🔍 SUPER DEBUG - Active Tab:', activeTab);
  console.log('🔍 SUPER DEBUG - Current Active Result:', scanResults[activeTab]);

  // Refresh batch data periodically if still processing
  useEffect(() => {
    if (!batch) return;
    
    if (batch.status === 'processing') {
      const interval = setInterval(() => {
        refreshBatch(batchId!);
      }, 3000);
      
      return () => clearInterval(interval);
    }
  }, [batch?.status, batchId, refreshBatch]);

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
      await exportBatch(batchId!, 'excel');
    }
  };

  const handleGoogleDriveShare = async (format: 'excel' | 'pdf', result?: any) => {
    if (result) {
      await saveToGoogleDrive(result.id, format);
    }
  };

  const renderDebugInfo = (result: any) => {
    return (
      <div className="bg-gray-900 text-green-400 p-6 rounded-lg font-mono text-xs overflow-auto max-h-96">
        <div className="mb-4">
          <h5 className="text-green-300 font-bold mb-2">🔍 SUPER DETAILED DEBUG INFO</h5>
          <div className="grid grid-cols-2 gap-4 mb-4 text-yellow-300">
            <div>📄 File: {result.original_filename}</div>
            <div>🏷️ Type: {result.document_type}</div>
            <div>🎯 Confidence: {(result.confidence * 100).toFixed(2)}%</div>
            <div>📅 Processed: {new Date(result.created_at).toLocaleString()}</div>
          </div>
        </div>

        <div className="mb-4">
          <h6 className="text-cyan-300 font-bold mb-2">📊 FULL RESULT OBJECT STRUCTURE:</h6>
          <pre className="text-xs bg-gray-800 p-3 rounded overflow-x-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>

        <div className="mb-4">
          <h6 className="text-cyan-300 font-bold mb-2">🧠 EXTRACTED DATA ANALYSIS:</h6>
          {result.extracted_data && (
            <div className="space-y-2">
              <div>🔢 Total Fields: {Object.keys(result.extracted_data).length}</div>
              <div>📋 Field Names: {Object.keys(result.extracted_data).join(', ')}</div>
              
              {Object.entries(result.extracted_data).map(([key, value]: [string, any]) => (
                <div key={key} className="border-l-2 border-blue-400 pl-3 my-2">
                  <div className="text-blue-300 font-bold">{key}:</div>
                  <div className="text-gray-300 ml-2">
                    Type: {Array.isArray(value) ? 'Array' : typeof value} | 
                    Value: {typeof value === 'object' && value !== null 
                      ? `Object with ${Object.keys(value).length} properties`
                      : String(value)}
                  </div>
                  {typeof value === 'object' && value !== null && (
                    <pre className="text-xs bg-gray-800 p-2 rounded mt-1 overflow-x-auto">
                      {JSON.stringify(value, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="mb-4">
          <h6 className="text-cyan-300 font-bold mb-2">🔍 DATA TYPE ANALYSIS:</h6>
          {result.extracted_data && Object.entries(result.extracted_data).map(([key, value]: [string, any]) => (
            <div key={key} className="mb-2">
              <span className="text-yellow-300">{key}:</span>
              <span className="ml-2">
                {Array.isArray(value) && `Array[${value.length}]`}
                {typeof value === 'object' && value !== null && !Array.isArray(value) && `Object{${Object.keys(value).join(', ')}}`}
                {typeof value === 'string' && `String(${value.length} chars)`}
                {typeof value === 'number' && `Number(${value})`}
                {typeof value === 'boolean' && `Boolean(${value})`}
                {value === null && 'Null'}
                {value === undefined && 'Undefined'}
              </span>
            </div>
          ))}
        </div>

        <div className="mb-4">
          <h6 className="text-cyan-300 font-bold mb-2">🏗️ AI FORMATTER INPUT/OUTPUT:</h6>
          <div className="space-y-2">
            <div>
              <div className="text-yellow-300">📥 Input to AIDataFormatter:</div>
              <pre className="text-xs bg-gray-800 p-2 rounded overflow-x-auto">
                {JSON.stringify({
                  document_type: result.document_type,
                  confidence: result.confidence,
                  extracted_data: result.extracted_data,
                  original_filename: result.original_filename
                }, null, 2)}
              </pre>
            </div>
            <div>
              <div className="text-yellow-300">📤 Output from AIDataFormatter:</div>
              <pre className="text-xs bg-gray-800 p-2 rounded overflow-x-auto">
                {JSON.stringify(AIDataFormatter.formatDocumentData(result), null, 2)}
              </pre>
            </div>
          </div>
        </div>

        <div>
          <h6 className="text-cyan-300 font-bold mb-2">⚙️ PROCESSING METADATA:</h6>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>ID: {result.id}</div>
            <div>Status: {result.status}</div>
            <div>Processing Time: {result.processing_time || 'N/A'}ms</div>
            <div>File Size: {result.file_size || 'N/A'} bytes</div>
            <div>Created: {result.created_at}</div>
            <div>Updated: {result.updated_at}</div>
          </div>
        </div>
      </div>
    );
  };

  const renderExtractedData = (result: any) => {
    // SUPER DEBUG: Log all data to console
    console.log('🔍 SUPER DEBUG - Full Result Object:', result);
    console.log('📊 Document Type:', result.document_type);
    console.log('🎯 Confidence:', result.confidence);
    console.log('📄 Filename:', result.original_filename);
    console.log('🧠 Extracted Data:', result.extracted_data);
    console.log('⚙️ AI Formatted Data:', AIDataFormatter.formatDocumentData(result));
    
    try {
      // Use AI formatter to prepare data for display
      const aiFormattedData = AIDataFormatter.formatDocumentData(result);
      
      return <AIDataDisplay data={aiFormattedData} />;
    } catch (error) {
      console.error('AI formatting error:', error);
      
      // Fallback to raw data display
      const data = result.extracted_data;
      return (
        <div className="bg-gray-50 p-6 rounded-lg">
          <pre className="text-sm text-gray-700 whitespace-pre-wrap">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg p-6 shadow-sm border">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate(-1)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Scan Results</h1>
              <p className="text-gray-600 mt-1">Batch #{batchId?.slice(-8)} - {batch.total_files} files</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {batch.status === 'completed' ? (
              <div className="flex items-center space-x-2 text-green-600">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Completed</span>
              </div>
            ) : batch.status === 'processing' ? (
              <div className="flex items-center space-x-2 text-yellow-600">
                <Clock className="w-5 h-5 processing-animation" />
                <span className="font-medium">Processing...</span>
              </div>
            ) : (
              <div className="flex items-center space-x-2 text-red-600">
                <AlertCircle className="w-5 h-5" />
                <span className="font-medium">Error</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Processing Status */}
      <div className="bg-white rounded-lg p-6 shadow-sm border">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Processing Progress</h3>
          <span className="text-sm text-gray-600">{batch.processed_files}/{batch.total_files} completed</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
          <div 
            className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${(batch.processed_files / batch.total_files) * 100}%` }}
          ></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center space-x-2">
            <Brain className="w-5 h-5 text-blue-600" />
            <span className="text-sm text-blue-700">AI Analysis Complete</span>
          </div>
          <div className="flex items-center space-x-2">
            <Database className="w-5 h-5 text-green-600" />
            <span className="text-sm text-green-700">Data Extracted</span>
          </div>
          <div className="flex items-center space-x-2">
            <FileText className="w-5 h-5 text-purple-600" />
            <span className="text-sm text-purple-700">Ready for Export</span>
          </div>
        </div>
      </div>

      {/* Results */}
      {scanResults.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-6 border-b">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Extracted Data</h3>
              <div className="flex space-x-2">
                <button
                  onClick={() => handleDownload('excel')}
                  disabled={loading}
                  className="px-4 py-2 success-gradient text-white rounded-lg hover:shadow-lg transition-all duration-200"
                >
                  <Download className="w-4 h-4 inline mr-2" />
                  Download All (Excel)
                </button>
                <button
                  onClick={() => handleDownload('pdf')}
                  disabled={loading}
                  className="px-4 py-2 error-gradient text-white rounded-lg hover:shadow-lg transition-all duration-200"
                >
                  <Download className="w-4 h-4 inline mr-2" />
                  Download All (PDF)
                </button>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b">
            <nav className="flex space-x-8 px-6">
              {scanResults.map((result, index) => (
                <button
                  key={result.id}
                  onClick={() => setActiveTab(index)}
                  className={`py-4 text-sm font-medium border-b-2 ${
                    activeTab === index
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {result.original_filename}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {/* Global Debug for All Scan Results */}
            <div className="mb-6">
              <details className="bg-blue-50 rounded-lg border border-blue-200">
                <summary className="p-3 cursor-pointer font-medium text-blue-900 hover:bg-blue-100 rounded-lg">
                  🌍 Global Debug: All Scan Results ({scanResults.length} files)
                </summary>
                <div className="p-3 pt-0">
                  <div className="mb-4 flex space-x-2">
                    <button
                      onClick={async () => {
                        try {
                          const response = await fetch(`http://localhost:8000/api/debug/recalculate-confidence/${batchId}`, {
                            method: 'POST'
                          });
                          if (response.ok) {
                            const result = await response.json();
                            console.log('🔄 Recalculation result:', result);
                            alert(`✅ Recalculated confidence for ${result.updates.length} files`);
                            // Refresh the page to see new values
                            window.location.reload();
                          } else {
                            console.error('❌ Recalculation failed');
                            alert('❌ Failed to recalculate confidence');
                          }
                        } catch (error) {
                          console.error('❌ Error:', error);
                          alert('❌ Error recalculating confidence');
                        }
                      }}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                    >
                      🔄 Recalculate Confidence
                    </button>
                    <button
                      onClick={async () => {
                        if (confirm('⚠️ This will clear ALL storage. Are you sure?')) {
                          try {
                            const response = await fetch('http://localhost:8000/api/debug/clear-storage', {
                              method: 'DELETE'
                            });
                            if (response.ok) {
                              const result = await response.json();
                              console.log('🧹 Clear storage result:', result);
                              alert(`✅ Cleared ${result.cleared.batches} batches and ${result.cleared.results} results`);
                              // Navigate back to home
                              navigate('/');
                            } else {
                              alert('❌ Failed to clear storage');
                            }
                          } catch (error) {
                            console.error('❌ Error:', error);
                            alert('❌ Error clearing storage');
                          }
                        }
                      }}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                    >
                      🧹 Clear Storage
                    </button>
                  </div>
                  <div className="bg-blue-900 text-green-400 p-4 rounded-lg font-mono text-xs overflow-auto max-h-64">
                    <div className="text-cyan-300 font-bold mb-2">📊 BATCH OVERVIEW:</div>
                    <div className="mb-2">Total Files: {scanResults.length}</div>
                    <div className="mb-2">Document Types: {[...new Set(scanResults.map(r => r.document_type))].join(', ')}</div>
                    <div className="mb-4">Average Confidence: {(scanResults.reduce((sum, r) => sum + r.confidence, 0) / scanResults.length * 100).toFixed(2)}%</div>
                    
                    <div className="text-cyan-300 font-bold mb-2">📋 ALL SCAN RESULTS:</div>
                    <pre className="text-xs bg-gray-800 p-3 rounded overflow-x-auto">
                      {JSON.stringify(scanResults, null, 2)}
                    </pre>
                  </div>
                </div>
              </details>
            </div>

            {scanResults[activeTab] && (
              <div className="space-y-6">
                {/* File Info */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <FileText className="w-6 h-6 text-blue-600" />
                    <div>
                      <h4 className="font-medium text-gray-900">{scanResults[activeTab].original_filename}</h4>
                      <p className="text-sm text-gray-600">Confidence: {(scanResults[activeTab].confidence * 100).toFixed(1)}%</p>
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleDownload('excel', scanResults[activeTab])}
                      disabled={loading}
                      className="px-3 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
                    >
                      <Download className="w-4 h-4 inline mr-1" />
                      Excel
                    </button>
                    <button
                      onClick={() => handleDownload('pdf', scanResults[activeTab])}
                      disabled={loading}
                      className="px-3 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
                    >
                      <Download className="w-4 h-4 inline mr-1" />
                      PDF
                    </button>
                    <button
                      onClick={() => handleGoogleDriveShare('excel', scanResults[activeTab])}
                      disabled={loading}
                      className="px-3 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
                    >
                      <Share2 className="w-4 h-4 inline mr-1" />
                      Save to Drive
                    </button>
                  </div>
                </div>

                {/* Extracted Data */}
                {renderExtractedData(scanResults[activeTab])}

                {/* Debug Information */}
                <div className="mt-8">
                  <details className="bg-gray-100 rounded-lg">
                    <summary className="p-4 cursor-pointer font-medium text-gray-900 hover:bg-gray-200 rounded-lg">
                      🔍 Debug Information (Click to expand)
                    </summary>
                    <div className="p-4 pt-0">
                      {renderDebugInfo(scanResults[activeTab])}
                    </div>
                  </details>
                </div>
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