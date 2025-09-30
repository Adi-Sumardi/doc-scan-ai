import React, { useState } from 'react';
import { useDocument } from '../context/DocumentContext';
import { 
  FileText, 
  Search, 
  Filter, 
  Download, 
  Eye,
  Calendar,
  CheckCircle,
  AlertCircle,
  X
} from 'lucide-react';
import StructuredDataViewer from '../components/StructuredDataViewer';

interface ViewModalProps {
  result: any;
  isOpen: boolean;
  onClose: () => void;
}

const ViewModal: React.FC<ViewModalProps> = ({ result, isOpen, onClose }) => {
  if (!isOpen || !result) return null;

  const documentTypeLabels: Record<string, string> = {
    faktur_pajak: 'Faktur Pajak',
    pph21: 'PPh 21',
    pph23: 'PPh 23', 
    rekening_koran: 'Rekening Koran',
    invoice: 'Invoice',
    batch: 'Batch Export'
  };

  const renderExtractedData = () => {
    const data = result.extracted_data;
    
    // Simplified and robust data rendering
    if (!data || typeof data !== 'object' || Object.keys(data).length === 0) {
      return (
        <div className="bg-red-50 p-4 rounded-lg border border-red-200 text-center">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
          <h4 className="text-lg font-semibold text-red-900 mb-2">No Data Extracted</h4>
          <p className="text-red-700">
            The AI could not extract structured data from this document. You can view the raw OCR text in the export files.
          </p>
        </div>
      );
    }
    
    // Universal pretty-JSON renderer
    return <StructuredDataViewer data={data} />;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h3 className="text-xl font-semibold text-gray-900">{result.original_filename}</h3>
            <p className="text-sm text-gray-600">
              {documentTypeLabels[result.document_type] || result.document_type} • 
              Confidence: {(result.confidence * 100).toFixed(1)}%
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          {renderExtractedData()}
        </div>
      </div>
    </div>
  );
};

const Documents = () => {
  const { scanResults, exportResult, loading } = useDocument();
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [selectedResult, setSelectedResult] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const documentTypeLabels: Record<string, string> = {
    faktur_pajak: 'Faktur Pajak',
    pph21: 'PPh 21',
    pph23: 'PPh 23', 
    rekening_koran: 'Rekening Koran',
    invoice: 'Invoice',
    batch: 'Batch Export'
  };

  const safeScanResults = Array.isArray(scanResults) ? scanResults : [];

  const filteredResults = safeScanResults.filter(result => {
    const filename = result.filename || result.original_filename || '';
    const docType = result.document_type || result.file_type || '';
    const matchesSearch = filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         docType.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterType === 'all' || docType === filterType;
    
    return matchesSearch && matchesFilter;
  });

  const handleDownload = async (result: any, format: 'excel' | 'pdf') => {
    await exportResult(result.id, format);
  };

  const handleViewDocument = (result: any) => {
    setSelectedResult(result);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedResult(null);
  };
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-green-600 bg-green-100';
    if (confidence >= 0.7) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg p-4 md:p-6 shadow-sm border">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-xl md:text-2xl lg:text-3xl font-bold text-gray-900">Documents</h1>
            <p className="text-sm md:text-base text-gray-600 mt-1">Manage your scanned documents and results</p>
          </div>
          <div className="flex items-center justify-end sm:justify-start">
            <span className="text-xs md:text-sm text-gray-600 bg-gray-100 px-3 py-1 rounded-full">{filteredResults.length} documents</span>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg p-4 md:p-6 shadow-sm border">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 flex-1">
            <div className="relative flex-1 sm:flex-initial sm:min-w-0 sm:w-64">
              <Search className="w-4 h-4 md:w-5 md:h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 md:pl-10 pr-4 py-2 text-sm md:text-base border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="relative flex-1 sm:flex-initial sm:min-w-0 sm:w-48">
              <Filter className="w-4 h-4 md:w-5 md:h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="w-full pl-9 md:pl-10 pr-8 py-2 text-sm md:text-base border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none bg-white"
              >
                <option value="all">All Types</option>
                <option value="faktur_pajak">Faktur Pajak</option>
                <option value="pph21">PPh 21</option>
                <option value="pph23">PPh 23</option>
                <option value="rekening_koran">Rekening Koran</option>
                <option value="invoice">Invoice</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Documents Grid */}
      {filteredResults.length === 0 ? (
        <div className="bg-white rounded-lg p-12 shadow-sm border text-center">
          <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No documents found</h3>
          <p className="text-gray-600">Upload some documents to see them here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-6">
          {filteredResults.map((result) => (
            <div key={result.id} className="bg-white rounded-lg shadow-sm border scan-card hover:shadow-md transition-shadow">
              <div className="p-4 md:p-6">
                <div className="flex items-start justify-between mb-3 md:mb-4">
                  <div className="flex items-center space-x-2 md:space-x-3 min-w-0 flex-1">
                    <FileText className="w-6 h-6 md:w-8 md:h-8 text-blue-600 flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <h3 className="font-semibold text-sm md:text-base text-gray-900 truncate" title={result.filename || result.original_filename}>
                        {result.filename || result.original_filename}
                      </h3>
                      <p className="text-xs md:text-sm text-gray-600 truncate" title={documentTypeLabels[result.document_type || result.file_type || 'other'] || result.document_type || result.file_type || 'Unknown'}>
                        {documentTypeLabels[result.document_type || result.file_type || 'other'] || result.document_type || result.file_type || 'Unknown'}
                      </p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium flex-shrink-0 ml-2 ${getConfidenceColor(result.confidence || result.confidence_score || 0)}`}>
                    {((result.confidence || result.confidence_score || 0) * 100).toFixed(1)}%
                  </span>
                </div>

                <div className="space-y-2 md:space-y-3 mb-3 md:mb-4">
                  <div className="flex items-center space-x-2 text-xs md:text-sm text-gray-600">
                    <Calendar className="w-3 h-3 md:w-4 md:h-4 flex-shrink-0" />
                    <span className="truncate">{new Date(result.created_at).toLocaleDateString()}</span>
                  </div>
                  
                  <div className="flex items-center space-x-2 text-xs md:text-sm text-green-600">
                    <CheckCircle className="w-3 h-3 md:w-4 md:h-4 flex-shrink-0" />
                    <span>Processing Complete</span>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-2">
                  <button
                    onClick={() => handleDownload(result, 'excel')}
                    disabled={loading}
                    className="flex-1 px-2 md:px-3 py-2 text-xs md:text-sm bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors font-medium"
                  >
                    <Download className="w-3 h-3 md:w-4 md:h-4 inline mr-1" />
                    Excel
                  </button>
                  <button
                    onClick={() => handleDownload(result, 'pdf')}
                    disabled={loading}
                    className="flex-1 px-2 md:px-3 py-2 text-xs md:text-sm bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition-colors font-medium"
                  >
                    <Download className="w-3 h-3 md:w-4 md:h-4 inline mr-1" />
                    PDF
                  </button>
                  <button 
                    onClick={() => handleViewDocument(result)}
                    className="px-2 md:px-3 py-2 text-xs md:text-sm bg-gray-50 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <Eye className="w-3 h-3 md:w-4 md:h-4 inline mr-1" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* View Modal */}
      <ViewModal 
        result={selectedResult}
        isOpen={isModalOpen}
        onClose={closeModal}
      />
    </div>
  );
};

export default Documents;