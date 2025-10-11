import { useState } from 'react';
import { useDocument } from '../context/DocumentContext';
import {
  FileText,
  Search,
  Filter,
  Download,
  Calendar,
  CheckCircle
} from 'lucide-react';

const Documents = () => {
  const { scanResults, exportResult, loading } = useDocument();
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');

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
                <div className="flex items-start mb-3 md:mb-4">
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

                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => handleDownload(result, 'excel')}
                    disabled={loading}
                    className="px-2 md:px-3 py-2 text-xs md:text-sm bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label={`Download ${result.original_filename} as Excel`}
                  >
                    <Download className="w-3 h-3 md:w-4 md:h-4 inline mr-1" />
                    Excel
                  </button>
                  <button
                    onClick={() => handleDownload(result, 'pdf')}
                    disabled={loading}
                    className="px-2 md:px-3 py-2 text-xs md:text-sm bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label={`Download ${result.original_filename} as PDF`}
                  >
                    <Download className="w-3 h-3 md:w-4 md:h-4 inline mr-1" />
                    PDF
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Documents;