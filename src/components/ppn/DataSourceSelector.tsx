import { useState, useEffect } from 'react';
import { FileSpreadsheet, Upload, Check, Calendar, FileText, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import toast from 'react-hot-toast';

interface ExcelFile {
  id: string;
  filename: string;
  document_type: string;
  row_count: number;
  created_at: string;
  date_range?: {
    start: string;
    end: string;
  };
}

interface DataSourceSelectorProps {
  companyNpwp: string;
  onDataSelected: (sources: SelectedDataSources) => void;
}

export interface SelectedDataSources {
  point_a_b_source: {
    type: 'scanned' | 'upload';
    file_id?: string;
    uploaded_file?: File;
  } | null;
  point_c_source: {
    type: 'scanned' | 'upload';
    file_id?: string;
    uploaded_file?: File;
  } | null;
  point_e_source: {
    type: 'scanned' | 'upload';
    file_id?: string;
    uploaded_file?: File;
  } | null;
}

const DataSourceSelector = ({ companyNpwp, onDataSelected }: DataSourceSelectorProps) => {
  const [fakturPajakFiles, setFakturPajakFiles] = useState<ExcelFile[]>([]);
  const [buktiPotongFiles, setBuktiPotongFiles] = useState<ExcelFile[]>([]);
  const [rekeningKoranFiles, setRekeningKoranFiles] = useState<ExcelFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [showAllFiles, setShowAllFiles] = useState(false);
  const INITIAL_LOAD_LIMIT = 5; // Load only 5 files initially for fast display

  // Toggle states for showing/hiding scanned files lists
  const [showFakturPajakList, setShowFakturPajakList] = useState(false);
  const [showBuktiPotongList, setShowBuktiPotongList] = useState(false);
  const [showRekeningKoranList, setShowRekeningKoranList] = useState(false);

  const [selectedSources, setSelectedSources] = useState<SelectedDataSources>({
    point_a_b_source: null,
    point_c_source: null,
    point_e_source: null,
  });

  useEffect(() => {
    // Only fetch files once on mount
    fetchAvailableFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty dependency array = runs once on mount

  useEffect(() => {
    // Debounce data selection callback to avoid excessive calls
    const timer = setTimeout(() => {
      onDataSelected(selectedSources);
    }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSources]);

  const fetchAvailableFiles = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/reconciliation-excel/files', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch files');
      }

      const data = await response.json();
      const files: ExcelFile[] = data.files || [];

      // Categorize files by type
      const fakturFiles = files.filter(f => f.document_type === 'faktur_pajak');
      const buktiFiles = files.filter(f => f.document_type === 'pph23');
      const rekeningFiles = files.filter(f => f.document_type === 'rekening_koran');

      // Show only recent files initially (sorted by created_at desc, take first 5)
      setFakturPajakFiles(fakturFiles.slice(0, INITIAL_LOAD_LIMIT));
      setBuktiPotongFiles(buktiFiles.slice(0, INITIAL_LOAD_LIMIT));
      setRekeningKoranFiles(rekeningFiles.slice(0, INITIAL_LOAD_LIMIT));

      // Load remaining files in background after initial display
      setTimeout(() => {
        if (fakturFiles.length > INITIAL_LOAD_LIMIT ||
            buktiFiles.length > INITIAL_LOAD_LIMIT ||
            rekeningFiles.length > INITIAL_LOAD_LIMIT) {
          // Store full lists in state for lazy expansion
          setFakturPajakFiles(fakturFiles);
          setBuktiPotongFiles(buktiFiles);
          setRekeningKoranFiles(rekeningFiles);
          setShowAllFiles(true);
        }
      }, 100); // Load rest after 100ms

    } catch (error) {
      console.error('Failed to fetch files:', error);
      toast.error('Failed to load available files');
      setFakturPajakFiles([]);
      setBuktiPotongFiles([]);
      setRekeningKoranFiles([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSelect = (point: 'point_a_b_source' | 'point_c_source' | 'point_e_source', fileId: string) => {
    setSelectedSources(prev => ({
      ...prev,
      [point]: {
        type: 'scanned',
        file_id: fileId
      }
    }));
  };

  const handleFileUpload = (point: 'point_a_b_source' | 'point_c_source' | 'point_e_source', file: File) => {
    setSelectedSources(prev => ({
      ...prev,
      [point]: {
        type: 'upload',
        uploaded_file: file
      }
    }));
    toast.success(`File ${file.name} selected for upload`);
  };

  const renderFileCard = (file: ExcelFile, point: 'point_a_b_source' | 'point_c_source' | 'point_e_source') => {
    const currentSelection = selectedSources[point];
    const isSelected = currentSelection?.type === 'scanned' && currentSelection?.file_id === file.id;

    return (
      <div
        key={file.id}
        onClick={() => handleFileSelect(point, file.id)}
        className={`border rounded-lg p-3 sm:p-4 cursor-pointer transition-all ${
          isSelected
            ? 'border-blue-500 bg-blue-50 shadow-md'
            : 'border-gray-200 hover:border-blue-300 hover:shadow-sm'
        }`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-start gap-2 mb-2">
              <FileSpreadsheet className={`w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0 mt-0.5 ${isSelected ? 'text-blue-600' : 'text-gray-600'}`} />
              <h4 className={`text-sm sm:text-base font-medium break-words overflow-wrap-anywhere ${isSelected ? 'text-blue-900' : 'text-gray-900'}`}>
                {file.filename}
              </h4>
            </div>
            <div className="space-y-1 text-xs sm:text-sm text-gray-600 ml-6 sm:ml-7">
              <div className="flex items-center gap-2">
                <FileText className="w-3 h-3 sm:w-4 sm:h-4 flex-shrink-0" />
                <span>{file.row_count} rows</span>
              </div>
              {file.date_range && (
                <div className="flex items-center gap-2">
                  <Calendar className="w-3 h-3 sm:w-4 sm:h-4 flex-shrink-0" />
                  <span className="break-words">{file.date_range.start} to {file.date_range.end}</span>
                </div>
              )}
            </div>
          </div>
          {isSelected && (
            <div className="flex-shrink-0">
              <div className="w-5 h-5 sm:w-6 sm:h-6 bg-blue-600 rounded-full flex items-center justify-center">
                <Check className="w-3 h-3 sm:w-4 sm:h-4 text-white" />
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderUploadSection = (
    point: 'point_a_b_source' | 'point_c_source' | 'point_e_source',
    acceptedFormats: string,
    description: string
  ) => {
    const uploadedFile = selectedSources[point]?.type === 'upload' ? selectedSources[point]?.uploaded_file : null;

    return (
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 hover:border-blue-400 transition-colors">
        <input
          type="file"
          id={`upload-${point}`}
          accept={acceptedFormats}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              handleFileUpload(point, file);
            }
          }}
          className="hidden"
        />
        <label htmlFor={`upload-${point}`} className="cursor-pointer block text-center">
          <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 mb-1">
            {uploadedFile ? uploadedFile.name : 'Click to upload or drag and drop'}
          </p>
          <p className="text-xs text-gray-500">{description}</p>
          {uploadedFile && (
            <div className="mt-3 inline-flex items-center gap-2 px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
              <Check className="w-3 h-3" />
              File selected
            </div>
          )}
        </label>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading available files...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 sm:p-4 flex items-start gap-2 sm:gap-3">
        <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="text-xs sm:text-sm text-blue-900">
          <p className="font-semibold mb-1">Company NPWP: {companyNpwp}</p>
          <p>Faktur Pajak will be automatically split into Point A (when you're the seller) and Point B (when you're the buyer) based on NPWP matching.</p>
        </div>
      </div>

      {/* Point A & B: Faktur Pajak */}
      <div>
        <div className="mb-3 sm:mb-4">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600" />
            <span className="break-words">Point A & B: Faktur Pajak Keluaran & Masukan</span>
          </h3>
          <p className="text-xs sm:text-sm text-gray-600 mt-1">
            One file will be split into Point A (Faktur Keluaran) and Point B (Faktur Masukan)
          </p>
        </div>

        {fakturPajakFiles.length > 0 && (
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2 sm:mb-3">
              <h4 className="text-xs sm:text-sm font-medium text-gray-700">Select from scanned files:</h4>
              <button
                onClick={() => setShowFakturPajakList(!showFakturPajakList)}
                className="flex items-center gap-2 px-3 py-1.5 text-xs sm:text-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
              >
                {showFakturPajakList ? (
                  <>
                    <ChevronUp className="w-4 h-4" />
                    Hide Files ({fakturPajakFiles.length})
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4" />
                    Show Files ({fakturPajakFiles.length})
                  </>
                )}
              </button>
            </div>
            {showFakturPajakList && (
              <div className="space-y-2">
                {fakturPajakFiles.map(file => renderFileCard(file, 'point_a_b_source'))}
              </div>
            )}
          </div>
        )}

        <div>
          <h4 className="text-xs sm:text-sm font-medium text-gray-700 mb-2 sm:mb-3">Or upload new file:</h4>
          {renderUploadSection(
            'point_a_b_source',
            '.xlsx,.xls',
            'Excel file with buyer/seller information (11+ columns format)'
          )}
        </div>
      </div>

      {/* Point C: Bukti Potong */}
      <div>
        <div className="mb-3 sm:mb-4">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 sm:w-5 sm:h-5 text-green-600" />
            <span className="break-words">Point C: Bukti Potong Lawan Transaksi</span>
          </h3>
          <p className="text-xs sm:text-sm text-gray-600 mt-1">
            Withholding tax certificates from transaction counterparties
          </p>
        </div>

        {buktiPotongFiles.length > 0 && (
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2 sm:mb-3">
              <h4 className="text-xs sm:text-sm font-medium text-gray-700">Select from scanned files:</h4>
              <button
                onClick={() => setShowBuktiPotongList(!showBuktiPotongList)}
                className="flex items-center gap-2 px-3 py-1.5 text-xs sm:text-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
              >
                {showBuktiPotongList ? (
                  <>
                    <ChevronUp className="w-4 h-4" />
                    Hide Files ({buktiPotongFiles.length})
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4" />
                    Show Files ({buktiPotongFiles.length})
                  </>
                )}
              </button>
            </div>
            {showBuktiPotongList && (
              <div className="space-y-2">
                {buktiPotongFiles.map(file => renderFileCard(file, 'point_c_source'))}
              </div>
            )}
          </div>
        )}

        <div>
          <h4 className="text-xs sm:text-sm font-medium text-gray-700 mb-2 sm:mb-3">Or upload new file:</h4>
          {renderUploadSection(
            'point_c_source',
            '.xlsx,.xls',
            'Excel file with bukti potong data (PPh 23/26)'
          )}
        </div>
      </div>

      {/* Point E: Rekening Koran */}
      <div>
        <div className="mb-3 sm:mb-4">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 sm:w-5 sm:h-5 text-purple-600" />
            <span className="break-words">Point E: Rekening Koran (Bank Statement)</span>
          </h3>
          <p className="text-xs sm:text-sm text-gray-600 mt-1">
            Bank statement for payment reconciliation
          </p>
        </div>

        {rekeningKoranFiles.length > 0 && (
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2 sm:mb-3">
              <h4 className="text-xs sm:text-sm font-medium text-gray-700">Select from scanned files:</h4>
              <button
                onClick={() => setShowRekeningKoranList(!showRekeningKoranList)}
                className="flex items-center gap-2 px-3 py-1.5 text-xs sm:text-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
              >
                {showRekeningKoranList ? (
                  <>
                    <ChevronUp className="w-4 h-4" />
                    Hide Files ({rekeningKoranFiles.length})
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4" />
                    Show Files ({rekeningKoranFiles.length})
                  </>
                )}
              </button>
            </div>
            {showRekeningKoranList && (
              <div className="space-y-2">
                {rekeningKoranFiles.map(file => renderFileCard(file, 'point_e_source'))}
              </div>
            )}
          </div>
        )}

        <div>
          <h4 className="text-xs sm:text-sm font-medium text-gray-700 mb-2 sm:mb-3">Or upload new file:</h4>
          {renderUploadSection(
            'point_e_source',
            '.xlsx,.xls',
            'Excel file with bank transaction data'
          )}
        </div>
      </div>
    </div>
  );
};

export default DataSourceSelector;
