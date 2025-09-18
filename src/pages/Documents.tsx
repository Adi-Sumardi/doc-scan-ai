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
    
    // Check if this is a processing failure
    if (!data || Object.keys(data).length === 0) {
      return (
        <div className="bg-red-50 p-4 rounded-lg border border-red-200 text-center">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
          <h4 className="text-lg font-semibold text-red-900 mb-2">Processing Failed</h4>
          <p className="text-red-700">
            No data could be extracted from this document
          </p>
        </div>
      );
    }
    
    // Check if this is a fallback result
    const isProcessingFailed = (
        (typeof data === 'object' && data !== null) &&
        (
            (data.masukan && data.masukan.nomor_faktur === 'Processing failed') ||
            (data.masa_pajak === 'Processing failed') ||
            (data.nomor_rekening === 'Processing failed') ||
            (data.nomor_invoice === 'Processing failed') ||
            data.error
        )
    );
    
    if (isProcessingFailed) {
        return (
            <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                <div className="flex items-center mb-3">
                    <AlertCircle className="w-6 h-6 text-yellow-600 mr-2" />
                    <h4 className="text-lg font-semibold text-yellow-900">Processing Issue</h4>
                </div>
                <p className="text-yellow-800 mb-3">
                    The document was processed but some data extraction failed. This could be due to:
                </p>
                <ul className="text-yellow-700 text-sm list-disc list-inside space-y-1">
                    <li>Poor image quality or resolution</li>
                    <li>Handwritten or unclear text</li>
                    <li>Non-standard document format</li>
                    <li>OCR library limitations</li>
                </ul>
                <div className="mt-4 p-3 bg-yellow-100 rounded border">
                    <p className="text-sm text-yellow-800">
                        <strong>Suggestion:</strong> Try uploading a clearer image or PDF version of the document.
                    </p>
                </div>
            </div>
        );
    }
    
    if (result.document_type === 'faktur_pajak') {
      return (
        <div className="space-y-6">
          {/* A. Faktur Pajak Keluaran */}
          <div className="bg-green-50 p-4 rounded-lg border border-green-200">
            <h4 className="text-lg font-semibold text-green-900 mb-3">A. Faktur Pajak Keluaran</h4>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <label className="font-medium text-green-700">Nama Lawan Transaksi</label>
                <p className="text-green-900">{data.keluaran?.nama_lawan_transaksi || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-green-700">No Seri FP</label>
                <p className="text-green-900">{data.keluaran?.no_seri_fp || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-green-700">NPWP</label>
                <p className="text-green-900">{data.keluaran?.npwp || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-green-700">Alamat</label>
                <p className="text-green-900">{data.keluaran?.alamat || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-green-700">DPP</label>
                <p className="text-green-900">Rp {data.keluaran?.dpp?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="font-medium text-green-700">PPN</label>
                <p className="text-green-900">Rp {data.keluaran?.ppn?.toLocaleString() || '0'}</p>
              </div>
            </div>
          </div>

          {/* B. Faktur Pajak Masukan */}
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <h4 className="text-lg font-semibold text-blue-900 mb-3">B. Faktur Pajak Masukan</h4>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <label className="font-medium text-blue-700">Nama Lawan Transaksi</label>
                <p className="text-blue-900">{data.masukan?.nama_lawan_transaksi || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-blue-700">No Seri FP</label>
                <p className="text-blue-900">{data.masukan?.no_seri_fp || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-blue-700">NPWP</label>
                <p className="text-blue-900">{data.masukan?.npwp || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-blue-700">Email</label>
                <p className="text-blue-900">{data.masukan?.email || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-blue-700">Alamat</label>
                <p className="text-blue-900">{data.masukan?.alamat || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-blue-700">DPP</label>
                <p className="text-blue-900">Rp {data.masukan?.dpp?.toLocaleString() || '0'}</p>
              </div>
              <div>
                <label className="font-medium text-blue-700">PPN</label>
                <p className="text-blue-900">Rp {data.masukan?.ppn?.toLocaleString() || '0'}</p>
              </div>
            </div>
          </div>
        </div>
      );
    }

    if (result.document_type === 'pph21') {
      return (
        <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
          <h4 className="text-lg font-semibold text-yellow-900 mb-3">PPh 21 Data</h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <label className="font-medium text-yellow-700">Nomor</label>
              <p className="text-yellow-900">{data.nomor || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-yellow-700">Masa Pajak</label>
              <p className="text-yellow-900">{data.masa_pajak || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-yellow-700">Sifat Pemotongan</label>
              <p className="text-yellow-900">{data.sifat_pemotongan || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-yellow-700">Status Bukti Pemotongan</label>
              <p className="text-yellow-900">{data.status_bukti_pemotongan || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-yellow-700">Jenis PPh</label>
              <p className="text-yellow-900">{data.jenis_pph || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-yellow-700">Kode Objek Pajak</label>
              <p className="text-yellow-900">{data.kode_objek_pajak || 'N/A'}</p>
            </div>
            <div className="col-span-2">
              <label className="font-medium text-yellow-700">Objek Pajak</label>
              <p className="text-yellow-900">{data.objek_pajak || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-yellow-700">Penghasilan Bruto</label>
              <p className="text-yellow-900">Rp {data.penghasilan_bruto?.toLocaleString() || '0'}</p>
            </div>
            <div>
              <label className="font-medium text-yellow-700">DPP</label>
              <p className="text-yellow-900">Rp {data.dpp?.toLocaleString() || '0'}</p>
            </div>
            <div>
              <label className="font-medium text-yellow-700">Tarif</label>
              <p className="text-yellow-900">{data.tarif || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-yellow-700">PPh</label>
              <p className="text-lg font-bold text-yellow-900">Rp {data.pph?.toLocaleString() || '0'}</p>
            </div>
          </div>
          
          {/* Identitas Penerima Penghasilan */}
          <div className="mt-3">
            <h5 className="font-semibold text-yellow-900 mb-2">Identitas Penerima Penghasilan</h5>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <label className="font-medium text-yellow-700">NPWP/NIK</label>
                <p className="text-yellow-900">{data.identitas_penerima_penghasilan?.npwp_nik || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-yellow-700">Nama</label>
                <p className="text-yellow-900">{data.identitas_penerima_penghasilan?.nama || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-yellow-700">NITKU</label>
                <p className="text-yellow-900">{data.identitas_penerima_penghasilan?.nitku || 'N/A'}</p>
              </div>
            </div>
          </div>
          
          {/* Identitas Pemotong */}
          <div className="mt-3">
            <h5 className="font-semibold text-yellow-900 mb-2">Identitas Pemotong</h5>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <label className="font-medium text-yellow-700">NPWP/NIK</label>
                <p className="text-yellow-900">{data.identitas_pemotong?.npwp_nik || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-yellow-700">Nama Pemotong</label>
                <p className="text-yellow-900">{data.identitas_pemotong?.nama_pemotong || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-yellow-700">Tanggal Pemotongan</label>
                <p className="text-yellow-900">{data.identitas_pemotong?.tanggal_pemotongan || 'N/A'}</p>
              </div>
            </div>
          </div>
        </div>
      );
    }

    if (result.document_type === 'pph23') {
      return (
        <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
          <h4 className="text-lg font-semibold text-orange-900 mb-3">PPh 23 Data</h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <label className="font-medium text-orange-700">Nomor</label>
              <p className="text-orange-900">{data.nomor || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-orange-700">Masa Pajak</label>
              <p className="text-orange-900">{data.masa_pajak || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-orange-700">Sifat Pemotongan</label>
              <p className="text-orange-900">{data.sifat_pemotongan || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-orange-700">Status Bukti Pemotongan</label>
              <p className="text-orange-900">{data.status_bukti_pemotongan || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-orange-700">Jenis PPh</label>
              <p className="text-orange-900">{data.jenis_pph || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-orange-700">Kode Objek Pajak</label>
              <p className="text-orange-900">{data.kode_objek_pajak || 'N/A'}</p>
            </div>
            <div className="col-span-2">
              <label className="font-medium text-orange-700">Objek Pajak</label>
              <p className="text-orange-900">{data.objek_pajak || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-orange-700">DPP</label>
              <p className="text-orange-900">
                Rp {typeof data.dpp === 'number' && data.dpp > 0 
                  ? data.dpp.toLocaleString() 
                  : '0'}
              </p>
            </div>
            <div>
              <label className="font-medium text-orange-700">Tarif</label>
              <p className="text-orange-900">{data.tarif || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-orange-700">PPh</label>
              <p className="text-lg font-bold text-orange-900">
                Rp {typeof data.pph === 'number' && data.pph > 0 
                  ? data.pph.toLocaleString() 
                  : '0'}
              </p>
            </div>
          </div>
          
          {/* Identitas Penerima Penghasilan */}
          <div className="mt-3">
            <h5 className="font-semibold text-orange-900 mb-2">Identitas Penerima Penghasilan</h5>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <label className="font-medium text-orange-700">NPWP/NIK</label>
                <p className="text-orange-900">{data.identitas_penerima_penghasilan?.npwp_nik || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-orange-700">Nama</label>
                <p className="text-orange-900">{data.identitas_penerima_penghasilan?.nama || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-orange-700">NITKU</label>
                <p className="text-orange-900">{data.identitas_penerima_penghasilan?.nitku || 'N/A'}</p>
              </div>
            </div>
          </div>
          
          {/* Identitas Pemotong */}
          <div className="mt-3">
            <h5 className="font-semibold text-orange-900 mb-2">Identitas Pemotong</h5>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <label className="font-medium text-orange-700">NPWP/NIK</label>
                <p className="text-orange-900">{data.identitas_pemotong?.npwp_nik || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-orange-700">Nama Pemotong</label>
                <p className="text-orange-900">{data.identitas_pemotong?.nama_pemotong || 'N/A'}</p>
              </div>
              <div>
                <label className="font-medium text-orange-700">Tanggal Pemotongan</label>
                <p className="text-orange-900">{data.identitas_pemotong?.tanggal_pemotongan || 'N/A'}</p>
              </div>
            </div>
          </div>
        </div>
      );
    }

    if (result.document_type === 'rekening_koran') {
      return (
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
          <h4 className="text-lg font-semibold text-blue-900 mb-3">Rekening Koran</h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <label className="font-medium text-blue-700">Tanggal</label>
              <p className="text-blue-900">{data.tanggal || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-blue-700">Nilai Uang Masuk</label>
              <p className="text-blue-900">Rp {data.nilai_uang_masuk?.toLocaleString() || '0'}</p>
            </div>
            <div>
              <label className="font-medium text-blue-700">Nilai Uang Keluar</label>
              <p className="text-blue-900">Rp {data.nilai_uang_keluar?.toLocaleString() || '0'}</p>
            </div>
            <div>
              <label className="font-medium text-blue-700">Saldo</label>
              <p className="text-blue-900">Rp {data.saldo?.toLocaleString() || '0'}</p>
            </div>
            <div>
              <label className="font-medium text-blue-700">Sumber Uang Masuk</label>
              <p className="text-blue-900">{data.sumber_uang_masuk || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-blue-700">Tujuan Uang Keluar</label>
              <p className="text-blue-900">{data.tujuan_uang_keluar || 'N/A'}</p>
            </div>
            <div className="col-span-2">
              <label className="font-medium text-blue-700">Keterangan</label>
              <p className="text-blue-900">{data.keterangan || 'N/A'}</p>
            </div>
          </div>
        </div>
      );
    }

    if (result.document_type === 'invoice') {
      return (
        <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
          <h4 className="text-lg font-semibold text-purple-900 mb-3">Invoice</h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <label className="font-medium text-purple-700">PO</label>
              <p className="text-purple-900">{data.po || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-purple-700">Tanggal PO</label>
              <p className="text-purple-900">{data.tanggal_po || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-purple-700">Tanggal Invoice</label>
              <p className="text-purple-900">{data.tanggal_invoice || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-purple-700">Tanggal</label>
              <p className="text-purple-900">{data.tanggal || 'N/A'}</p>
            </div>
            <div className="col-span-2">
              <label className="font-medium text-purple-700">Keterangan</label>
              <p className="text-purple-900">{data.keterangan || 'N/A'}</p>
            </div>
            <div>
              <label className="font-medium text-purple-700">Nilai</label>
              <p className="text-lg font-bold text-purple-900">Rp {data.nilai?.toLocaleString() || '0'}</p>
            </div>
          </div>
        </div>
      );
    }

    // Default rendering for other document types or unrecognized structure
    return (
      <div className="bg-gray-50 p-4 rounded-lg">
        <pre className="text-sm text-gray-700 whitespace-pre-wrap overflow-auto max-h-96">
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    );
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

  const filteredResults = scanResults.filter(result => {
    const matchesSearch = result.original_filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         result.document_type.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterType === 'all' || result.document_type === filterType;
    
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
      <div className="bg-white rounded-lg p-6 shadow-sm border">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Documents</h1>
            <p className="text-gray-600 mt-1">Manage your scanned documents and results</p>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">{filteredResults.length} documents</span>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg p-6 shadow-sm border">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <Search className="w-5 h-5 absolute left-3 top-3 text-gray-400" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="relative">
              <Filter className="w-5 h-5 absolute left-3 top-3 text-gray-400" />
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="pl-10 pr-8 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none bg-white"
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredResults.map((result) => (
            <div key={result.id} className="bg-white rounded-lg shadow-sm border scan-card">
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <FileText className="w-8 h-8 text-blue-600" />
                    <div>
                      <h3 className="font-semibold text-gray-900 truncate">
                        {result.original_filename}
                      </h3>
                      <p className="text-sm text-gray-600">
                        {documentTypeLabels[result.document_type] || result.document_type}
                      </p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(result.confidence)}`}>
                    {(result.confidence * 100).toFixed(1)}%
                  </span>
                </div>

                <div className="space-y-3 mb-4">
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <Calendar className="w-4 h-4" />
                    <span>{new Date(result.created_at).toLocaleDateString()}</span>
                  </div>
                  
                  <div className="flex items-center space-x-2 text-sm text-green-600">
                    <CheckCircle className="w-4 h-4" />
                    <span>Processing Complete</span>
                  </div>
                </div>

                <div className="flex space-x-2">
                  <button
                    onClick={() => handleDownload(result, 'excel')}
                    disabled={loading}
                    className="flex-1 px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors"
                  >
                    <Download className="w-4 h-4 inline mr-1" />
                    Excel
                  </button>
                  <button
                    onClick={() => handleDownload(result, 'pdf')}
                    disabled={loading}
                    className="flex-1 px-3 py-2 text-sm bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition-colors"
                  >
                    <Download className="w-4 h-4 inline mr-1" />
                    PDF
                  </button>
                  <button 
                    onClick={() => handleViewDocument(result)}
                    className="px-3 py-2 text-sm bg-gray-50 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <Eye className="w-4 h-4" />
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