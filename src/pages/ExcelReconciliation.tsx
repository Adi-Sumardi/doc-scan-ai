import { useState, useEffect } from 'react';
import {
  FileSpreadsheet,
  Play,
  Download,
  Settings,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../services/api';
import * as XLSX from 'xlsx';

interface ExcelFile {
  filename: string;
  document_type: string;  // Changed from doc_type to match backend
  row_count: number;
  file_size: number;
  created_at: string;  // Changed from modified to match backend
}

interface MatchedItem {
  faktur: {
    source_type: string;
    source_file: string;
    source_row: number;
    date: string;
    amount: number;
    vendor_name: string;
    reference: string;
    raw_data?: any;
  };
  rekening: {
    source_type: string;
    source_file: string;
    source_row: number;
    date: string;
    amount: number;
    vendor_name: string;
    reference: string;
    raw_data?: any;
  };
  confidence: number;
  match_type: string;
  date_confidence?: number;
  amount_confidence?: number;
  vendor_similarity?: number;
}

interface UnmatchedItem {
  source_type: string;
  source_file: string;
  source_row: number;
  date: string;
  amount: number;
  vendor_name: string;
  reference: string;
  raw_data?: any;
}

interface MatchResult {
  success: boolean;
  match_id: string;
  matched_items: MatchedItem[];
  unmatched_items: UnmatchedItem[];
  summary: {
    total_faktur: number;
    total_rekening: number;
    matched_count: number;
    unmatched_faktur?: number;
    unmatched_rekening?: number;
    match_rate: number;
    total_matched_amount: number;
    total_unmatched_amount: number;
  };
}

const ExcelReconciliation = () => {
  const [fakturFiles, setFakturFiles] = useState<ExcelFile[]>([]);
  const [rekeningFiles, setRekeningFiles] = useState<ExcelFile[]>([]);
  const [selectedFaktur, setSelectedFaktur] = useState('');
  const [selectedRekening, setSelectedRekening] = useState('');
  const [loading, setLoading] = useState(false);
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);

  // Search/filter states
  const [fakturSearch, setFakturSearch] = useState('');
  const [rekeningSearch, setRekeningSearch] = useState('');

  // Show/hide dropdown states
  const [showFakturDropdown, setShowFakturDropdown] = useState(false);
  const [showRekeningDropdown, setShowRekeningDropdown] = useState(false);

  // Matching configuration
  const [dateTolerance, setDateTolerance] = useState(3);
  const [amountTolerance, setAmountTolerance] = useState(1.0);
  const [vendorSimilarity, setVendorSimilarity] = useState(0.80);
  const [minConfidence, setMinConfidence] = useState(0.70);
  const [showConfig, setShowConfig] = useState(false);

  useEffect(() => {
    loadExcelFiles();
  }, []);

  const loadExcelFiles = async () => {
    try {
      console.log('Loading Excel files from API...');
      const response = await api.get('/api/reconciliation-excel/files');
      console.log('API Response:', response.data);
      const files = response.data.files || [];
      console.log(`Total files received: ${files.length}`);

      // Filter by document type
      const faktur = files.filter((f: ExcelFile) => f.document_type === 'faktur_pajak');
      const rekening = files.filter((f: ExcelFile) => f.document_type === 'rekening_koran');

      console.log(`Faktur Pajak files: ${faktur.length}`);
      console.log(`Rekening Koran files: ${rekening.length}`);

      setFakturFiles(faktur);
      setRekeningFiles(rekening);

      // Auto-select first files
      if (faktur.length > 0) setSelectedFaktur(faktur[0].filename);
      if (rekening.length > 0) setSelectedRekening(rekening[0].filename);
    } catch (error: any) {
      toast.error('Failed to load Excel files');
      console.error(error);
    }
  };

  const handleMatch = async () => {
    if (!selectedFaktur || !selectedRekening) {
      toast.error('Please select both Faktur Pajak and Rekening Koran files');
      return;
    }

    try {
      setLoading(true);
      const response = await api.post('/api/reconciliation-excel/match', {
        faktur_file: selectedFaktur,
        rekening_file: selectedRekening,
        date_tolerance_days: dateTolerance,
        amount_tolerance_percent: amountTolerance,
        vendor_similarity_threshold: vendorSimilarity,
        min_confidence_score: minConfidence
      });

      setMatchResult(response.data);
      toast.success(`Matching complete! Found ${response.data.matched_items.length} matches`);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Matching failed');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.90) return 'text-green-600 bg-green-100';
    if (confidence >= 0.80) return 'text-blue-600 bg-blue-100';
    if (confidence >= 0.70) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  // Filtered file lists based on search
  const filteredFakturFiles = fakturFiles.filter(file =>
    file.filename.toLowerCase().includes(fakturSearch.toLowerCase())
  );

  const filteredRekeningFiles = rekeningFiles.filter(file =>
    file.filename.toLowerCase().includes(rekeningSearch.toLowerCase())
  );

  // Export to Excel with professional styling
  const handleExport = () => {
    if (!matchResult) return;

    // Helper function to format Rupiah
    const formatRupiah = (amount: number): string => {
      return `Rp ${amount.toLocaleString('id-ID')}`;
    };

    // Create workbook
    const wb = XLSX.utils.book_new();

    // ============ SUMMARY SHEET ============
    const summaryData = [
      ['LAPORAN REKONSILIASI FAKTUR PAJAK & REKENING KORAN'],
      [],
      ['Informasi Rekonsiliasi'],
      ['Match ID', matchResult.match_id],
      ['Tanggal Export', new Date().toLocaleDateString('id-ID', { year: 'numeric', month: 'long', day: 'numeric' })],
      [],
      ['Ringkasan Data'],
      ['Total Faktur Pajak', matchResult.summary.total_faktur],
      ['Total Rekening Koran', matchResult.summary.total_rekening],
      ['Jumlah Matched', matchResult.summary.matched_count],
      ['Jumlah Unmatched Faktur', matchResult.summary.unmatched_faktur || 0],
      ['Jumlah Unmatched Rekening', matchResult.summary.unmatched_rekening || 0],
      [],
      ['Statistik Rekonsiliasi'],
      ['Match Rate', `${(matchResult.summary.match_rate * 100).toFixed(1)}%`],
      ['Total Nominal Matched', formatRupiah(matchResult.summary.total_matched_amount)],
      ['Total Nominal Unmatched', formatRupiah(matchResult.summary.total_unmatched_amount)],
    ];

    const ws_summary = XLSX.utils.aoa_to_sheet(summaryData);

    // Set column widths for Summary sheet
    ws_summary['!cols'] = [
      { wch: 35 },
      { wch: 30 }
    ];

    // Apply styling to Summary sheet
    const summaryRange = XLSX.utils.decode_range(ws_summary['!ref'] || 'A1');
    for (let R = summaryRange.s.r; R <= summaryRange.e.r; ++R) {
      for (let C = summaryRange.s.c; C <= summaryRange.e.c; ++C) {
        const cellAddress = XLSX.utils.encode_cell({ r: R, c: C });
        if (!ws_summary[cellAddress]) continue;

        // Title row (row 0)
        if (R === 0) {
          ws_summary[cellAddress].s = {
            font: { bold: true, sz: 14, color: { rgb: "FFFFFF" } },
            fill: { fgColor: { rgb: "1F4788" } },
            alignment: { horizontal: "center", vertical: "center" }
          };
        }
        // Section headers (rows 2, 6, 13)
        else if (R === 2 || R === 6 || R === 13) {
          ws_summary[cellAddress].s = {
            font: { bold: true, sz: 11, color: { rgb: "FFFFFF" } },
            fill: { fgColor: { rgb: "4472C4" } },
            alignment: { horizontal: "left", vertical: "center" }
          };
        }
        // Data rows
        else if (C === 0 && ws_summary[cellAddress].v) {
          ws_summary[cellAddress].s = {
            font: { bold: true, sz: 10 },
            alignment: { horizontal: "left", vertical: "center" }
          };
        }
      }
    }

    XLSX.utils.book_append_sheet(wb, ws_summary, 'Ringkasan');

    // ============ MATCHED ITEMS SHEET ============
    const matchedData = [
      ['DATA TRANSAKSI YANG MATCHED'],
      [],
      ['Confidence', 'Seller (Penjual)', 'NPWP Seller', 'Buyer (Pembeli)', 'NPWP Buyer', 'Tanggal Faktur', 'Nominal Faktur', 'Tanggal Bank', 'Nominal Bank', 'Tipe Match', 'Selisih']
    ];

    matchResult.matched_items.forEach(item => {
      const difference = Math.abs(item.faktur.amount - item.rekening.amount);
      // Access buyer & seller data from raw_data if available
      const namaSeller = (item.faktur as any).nama_seller || item.faktur.vendor_name || '-';
      const npwpSeller = (item.faktur as any).npwp_seller || (item.faktur as any).npwp || '-';
      const namaBuyer = (item.faktur as any).nama_buyer || '-';
      const npwpBuyer = (item.faktur as any).npwp_buyer || '-';

      matchedData.push([
        `${(item.confidence * 100).toFixed(0)}%`,
        namaSeller,
        npwpSeller,
        namaBuyer,
        npwpBuyer,
        item.faktur.date,
        item.faktur.amount as any,
        item.rekening.date,
        item.rekening.amount as any,
        item.match_type === 'exact' ? 'Exact Match' : 'Fuzzy Match',
        difference as any
      ]);
    });

    const ws_matched = XLSX.utils.aoa_to_sheet(matchedData);

    // Set column widths for Matched sheet
    ws_matched['!cols'] = [
      { wch: 12 },  // Confidence
      { wch: 30 },  // Seller
      { wch: 20 },  // NPWP Seller
      { wch: 30 },  // Buyer
      { wch: 20 },  // NPWP Buyer
      { wch: 15 },  // Tanggal Faktur
      { wch: 18 },  // Nominal Faktur
      { wch: 15 },  // Tanggal Bank
      { wch: 18 },  // Nominal Bank
      { wch: 15 },  // Tipe Match
      { wch: 15 }   // Selisih
    ];

    // Apply styling to Matched sheet
    const matchedRange = XLSX.utils.decode_range(ws_matched['!ref'] || 'A1');
    for (let R = matchedRange.s.r; R <= matchedRange.e.r; ++R) {
      for (let C = matchedRange.s.c; C <= matchedRange.e.c; ++C) {
        const cellAddress = XLSX.utils.encode_cell({ r: R, c: C });
        if (!ws_matched[cellAddress]) continue;

        // Title row
        if (R === 0) {
          ws_matched[cellAddress].s = {
            font: { bold: true, sz: 14, color: { rgb: "FFFFFF" } },
            fill: { fgColor: { rgb: "1F4788" } },
            alignment: { horizontal: "center", vertical: "center" }
          };
        }
        // Header row (row 2)
        else if (R === 2) {
          ws_matched[cellAddress].s = {
            font: { bold: true, sz: 10, color: { rgb: "FFFFFF" } },
            fill: { fgColor: { rgb: "4472C4" } },
            alignment: { horizontal: "center", vertical: "center" },
            border: {
              top: { style: "thin", color: { rgb: "000000" } },
              bottom: { style: "thin", color: { rgb: "000000" } },
              left: { style: "thin", color: { rgb: "000000" } },
              right: { style: "thin", color: { rgb: "000000" } }
            }
          };
        }
        // Data rows - format currency columns (G, I, K - columns 6, 8, 10)
        else if (R > 2) {
          if (C === 6 || C === 8 || C === 10) {
            ws_matched[cellAddress].t = 'n';
            ws_matched[cellAddress].z = '"Rp "#,##0';
          }
          // Add borders to all data cells
          ws_matched[cellAddress].s = {
            border: {
              top: { style: "thin", color: { rgb: "D3D3D3" } },
              bottom: { style: "thin", color: { rgb: "D3D3D3" } },
              left: { style: "thin", color: { rgb: "D3D3D3" } },
              right: { style: "thin", color: { rgb: "D3D3D3" } }
            },
            alignment: { horizontal: (C === 1 || C === 3) ? "left" : "center", vertical: "center" }
          };
        }
      }
    }

    XLSX.utils.book_append_sheet(wb, ws_matched, 'Data Matched');

    // ============ UNMATCHED ITEMS SHEET ============
    const unmatchedData = [
      ['DATA TRANSAKSI YANG UNMATCHED'],
      [],
      ['Tipe', 'Vendor/Keterangan', 'Tanggal', 'Nominal', 'Referensi']
    ];

    matchResult.unmatched_items.forEach(item => {
      unmatchedData.push([
        item.source_type === 'faktur_pajak' ? 'FAKTUR PAJAK' : 'REKENING KORAN',
        item.vendor_name || 'N/A',
        item.date,
        item.amount as any,
        item.reference || '-'
      ]);
    });

    const ws_unmatched = XLSX.utils.aoa_to_sheet(unmatchedData);

    // Set column widths for Unmatched sheet
    ws_unmatched['!cols'] = [
      { wch: 18 },  // Tipe
      { wch: 35 },  // Vendor/Keterangan
      { wch: 15 },  // Tanggal
      { wch: 18 },  // Nominal
      { wch: 20 }   // Referensi
    ];

    // Apply styling to Unmatched sheet
    const unmatchedRange = XLSX.utils.decode_range(ws_unmatched['!ref'] || 'A1');
    for (let R = unmatchedRange.s.r; R <= unmatchedRange.e.r; ++R) {
      for (let C = unmatchedRange.s.c; C <= unmatchedRange.e.c; ++C) {
        const cellAddress = XLSX.utils.encode_cell({ r: R, c: C });
        if (!ws_unmatched[cellAddress]) continue;

        // Title row
        if (R === 0) {
          ws_unmatched[cellAddress].s = {
            font: { bold: true, sz: 14, color: { rgb: "FFFFFF" } },
            fill: { fgColor: { rgb: "1F4788" } },
            alignment: { horizontal: "center", vertical: "center" }
          };
        }
        // Header row (row 2)
        else if (R === 2) {
          ws_unmatched[cellAddress].s = {
            font: { bold: true, sz: 10, color: { rgb: "FFFFFF" } },
            fill: { fgColor: { rgb: "4472C4" } },
            alignment: { horizontal: "center", vertical: "center" },
            border: {
              top: { style: "thin", color: { rgb: "000000" } },
              bottom: { style: "thin", color: { rgb: "000000" } },
              left: { style: "thin", color: { rgb: "000000" } },
              right: { style: "thin", color: { rgb: "000000" } }
            }
          };
        }
        // Data rows - format currency column (D - column 3)
        else if (R > 2) {
          if (C === 3) {
            ws_unmatched[cellAddress].t = 'n';
            ws_unmatched[cellAddress].z = '"Rp "#,##0';
          }
          // Add borders and highlight unmatched rows
          ws_unmatched[cellAddress].s = {
            border: {
              top: { style: "thin", color: { rgb: "D3D3D3" } },
              bottom: { style: "thin", color: { rgb: "D3D3D3" } },
              left: { style: "thin", color: { rgb: "D3D3D3" } },
              right: { style: "thin", color: { rgb: "D3D3D3" } }
            },
            fill: { fgColor: { rgb: "FFF4E6" } },
            alignment: { horizontal: C === 1 ? "left" : "center", vertical: "center" }
          };
        }
      }
    }

    XLSX.utils.book_append_sheet(wb, ws_unmatched, 'Data Unmatched');

    // Generate filename with Indonesian date format
    const now = new Date();
    const dateStr = now.toLocaleDateString('id-ID').replace(/\//g, '-');
    const timeStr = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }).replace(':', '');
    const filename = `Rekonsiliasi_${dateStr}_${timeStr}.xlsx`;

    // Download with compression
    XLSX.writeFile(wb, filename, { cellStyles: true });
    toast.success(`Berhasil export: ${filename}`);
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
            <FileSpreadsheet className="w-7 h-7 text-blue-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Excel Reconciliation</h1>
            <p className="text-gray-600">Match Faktur Pajak with Rekening Koran directly from Excel files</p>
          </div>
        </div>
      </div>

      {/* File Selection */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Select Excel Files</h2>

        <div className="grid md:grid-cols-2 gap-4">
          {/* Faktur Pajak */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Faktur Pajak ({fakturFiles.length} files)
            </label>
            <input
              type="text"
              placeholder="Search files..."
              value={fakturSearch}
              onChange={(e) => {
                setFakturSearch(e.target.value);
                setShowFakturDropdown(true);
              }}
              onFocus={() => setShowFakturDropdown(true)}
              className="w-full px-3 py-2 border rounded-lg mb-2 text-sm"
            />

            {/* Custom Card-based Dropdown */}
            {(showFakturDropdown || fakturSearch) && (
              <div className="border rounded-lg bg-white max-h-64 overflow-y-auto p-2 space-y-2">
                {filteredFakturFiles.length > 0 ? (
                  filteredFakturFiles.map((file) => (
                    <div
                      key={file.filename}
                      onClick={() => {
                        setSelectedFaktur(file.filename);
                        setShowFakturDropdown(false);
                        setFakturSearch('');
                      }}
                      className={`p-3 rounded-lg cursor-pointer hover:bg-blue-50 transition-colors ${
                        selectedFaktur === file.filename ? 'bg-blue-100 border border-blue-300' : 'border border-gray-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-900 truncate">{file.filename}</p>
                          <p className="text-xs text-gray-500 mt-1">{file.row_count} rows</p>
                        </div>
                        {selectedFaktur === file.filename && (
                          <span className="ml-2 text-blue-600">✓</span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-3 text-sm text-gray-500 text-center">No files found</div>
                )}
              </div>
            )}

            {selectedFaktur && (
              <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-xs text-green-700 font-medium mb-1">✓ Selected:</p>
                <p className="text-sm text-gray-900 font-semibold break-words">{selectedFaktur}</p>
                <p className="text-xs text-green-600 mt-1">
                  {fakturFiles.find(f => f.filename === selectedFaktur)?.row_count} records
                </p>
              </div>
            )}
          </div>

          {/* Rekening Koran */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Rekening Koran ({rekeningFiles.length} files)
            </label>
            <input
              type="text"
              placeholder="Search files..."
              value={rekeningSearch}
              onChange={(e) => {
                setRekeningSearch(e.target.value);
                setShowRekeningDropdown(true);
              }}
              onFocus={() => setShowRekeningDropdown(true)}
              className="w-full px-3 py-2 border rounded-lg mb-2 text-sm"
            />

            {/* Custom Card-based Dropdown */}
            {(showRekeningDropdown || rekeningSearch) && (
              <div className="border rounded-lg bg-white max-h-64 overflow-y-auto p-2 space-y-2">
                {filteredRekeningFiles.length > 0 ? (
                  filteredRekeningFiles.map((file) => (
                    <div
                      key={file.filename}
                      onClick={() => {
                        setSelectedRekening(file.filename);
                        setShowRekeningDropdown(false);
                        setRekeningSearch('');
                      }}
                      className={`p-3 rounded-lg cursor-pointer hover:bg-purple-50 transition-colors ${
                        selectedRekening === file.filename ? 'bg-purple-100 border border-purple-300' : 'border border-gray-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-900 truncate">{file.filename}</p>
                          <p className="text-xs text-gray-500 mt-1">{file.row_count} rows</p>
                        </div>
                        {selectedRekening === file.filename && (
                          <span className="ml-2 text-purple-600">✓</span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-3 text-sm text-gray-500 text-center">No files found</div>
                )}
              </div>
            )}

            {selectedRekening && (
              <div className="mt-2 p-3 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-xs text-green-700 font-medium mb-1">✓ Selected:</p>
                <p className="text-sm text-gray-900 font-semibold break-words">{selectedRekening}</p>
                <p className="text-xs text-green-600 mt-1">
                  {rekeningFiles.find(f => f.filename === selectedRekening)?.row_count} transactions
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Matching Configuration */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <span className="text-green-600 font-bold text-lg">2</span>
            </div>
            <h2 className="text-xl font-semibold text-gray-800">Matching Configuration</h2>
          </div>
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="flex items-center space-x-2 text-blue-600 hover:text-blue-700"
          >
            <Settings className="w-5 h-5" />
            <span>{showConfig ? 'Hide' : 'Show'} Advanced Settings</span>
          </button>
        </div>

        {showConfig && (
          <div className="grid md:grid-cols-2 gap-6">
            {/* Date Tolerance */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Date Tolerance: ±{dateTolerance} days
              </label>
              <input
                type="range"
                min="1"
                max="7"
                step="1"
                value={dateTolerance}
                onChange={(e) => setDateTolerance(parseInt(e.target.value))}
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">
                Allow dates to differ by up to {dateTolerance} days
              </p>
            </div>

            {/* Amount Tolerance */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Amount Tolerance: ±{amountTolerance}%
              </label>
              <input
                type="range"
                min="0.5"
                max="5"
                step="0.5"
                value={amountTolerance}
                onChange={(e) => setAmountTolerance(parseFloat(e.target.value))}
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">
                Allow amounts to differ by up to {amountTolerance}%
              </p>
            </div>

            {/* Vendor Similarity */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Vendor Similarity: {(vendorSimilarity * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                min="0.6"
                max="0.95"
                step="0.05"
                value={vendorSimilarity}
                onChange={(e) => setVendorSimilarity(parseFloat(e.target.value))}
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">
                Minimum {(vendorSimilarity * 100).toFixed(0)}% similarity for vendor name matching
              </p>
            </div>

            {/* Min Confidence */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Min Confidence Score: {(minConfidence * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                min="0.5"
                max="0.9"
                step="0.05"
                value={minConfidence}
                onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">
                Only show matches with confidence ≥ {(minConfidence * 100).toFixed(0)}%
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Run Matching Button */}
      <div className="flex justify-center mb-6">
        <button
          onClick={handleMatch}
          disabled={loading || !selectedFaktur || !selectedRekening}
          className="flex items-center space-x-2 px-8 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-lg font-medium"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
              <span>Matching in progress...</span>
            </>
          ) : (
            <>
              <Play className="w-6 h-6" />
              <span>Run Matching</span>
            </>
          )}
        </button>
      </div>

      {/* Results Summary */}
      {matchResult && (
        <>
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">3. Matching Results</h2>
            <div className="grid md:grid-cols-4 gap-4">
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Total Faktur</p>
                <p className="text-2xl font-bold text-blue-600">{matchResult.summary.total_faktur}</p>
              </div>
              <div className="bg-purple-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Total Rekening</p>
                <p className="text-2xl font-bold text-purple-600">{matchResult.summary.total_rekening}</p>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Matched</p>
                <p className="text-2xl font-bold text-green-600">{matchResult.summary.matched_count}</p>
              </div>
              <div className="bg-yellow-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Match Rate</p>
                <p className="text-2xl font-bold text-yellow-600">{(matchResult.summary.match_rate * 100).toFixed(1)}%</p>
              </div>
            </div>

            <div className="mt-6 grid md:grid-cols-2 gap-4">
              <div className="border-l-4 border-green-500 bg-green-50 p-4 rounded">
                <p className="text-sm text-gray-600 mb-1">Total Matched Amount</p>
                <p className="text-xl font-bold text-green-700">{formatCurrency(matchResult.summary.total_matched_amount)}</p>
              </div>
              <div className="border-l-4 border-red-500 bg-red-50 p-4 rounded">
                <p className="text-sm text-gray-600 mb-1">Total Unmatched Amount</p>
                <p className="text-xl font-bold text-red-700">{formatCurrency(matchResult.summary.total_unmatched_amount)}</p>
              </div>
            </div>
          </div>

          {/* Matched Items Table */}
          {matchResult.matched_items.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center space-x-2">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <span>Matched Pairs ({matchResult.matched_items.length})</span>
                </h3>
                <button
                  onClick={handleExport}
                  className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  <span>Export to Excel</span>
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="bg-gradient-to-r from-green-50 to-green-100 border-b-2 border-green-200">
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        <div className="flex items-center space-x-1">
                          <span>Confidence</span>
                        </div>
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-blue-700 uppercase tracking-wider bg-blue-50/50">
                        Faktur Vendor
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-blue-700 uppercase tracking-wider bg-blue-50/50">
                        Faktur Date
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-blue-700 uppercase tracking-wider bg-blue-50/50">
                        Faktur Amount
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-purple-700 uppercase tracking-wider bg-purple-50/50">
                        Rekening Date
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-purple-700 uppercase tracking-wider bg-purple-50/50">
                        Rekening Amount
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Match Reason
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-100">
                    {matchResult.matched_items.map((item, idx) => (
                      <tr key={idx} className="hover:bg-green-50/30 transition-colors duration-150 border-l-4 border-transparent hover:border-green-500">
                        <td className="px-6 py-4">
                          <span className={`inline-flex px-3 py-1.5 rounded-full text-xs font-bold shadow-sm ${getConfidenceColor(item.confidence)}`}>
                            {(item.confidence * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm font-semibold text-gray-900">{item.faktur.vendor_name}</div>
                          <div className="text-xs text-gray-500 mt-0.5">Faktur Pajak</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm text-gray-700 font-medium">{item.faktur.date}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm font-bold text-blue-700">{formatCurrency(item.faktur.amount)}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm text-gray-700 font-medium">{item.rekening.date}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm font-bold text-purple-700">{formatCurrency(item.rekening.amount)}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-xs text-gray-600 max-w-xs">
                            Match: {item.match_type} | Date: {((item.date_confidence || 0) * 100).toFixed(0)}% | Amount: {((item.amount_confidence || 0) * 100).toFixed(0)}%
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Unmatched Items */}
          {matchResult.unmatched_items.length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center space-x-2">
                  <XCircle className="w-5 h-5 text-red-600" />
                  <span>Unmatched Items ({matchResult.unmatched_items.length})</span>
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="bg-gradient-to-r from-red-50 to-orange-50 border-b-2 border-red-200">
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Type
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Vendor / Description
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Date
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Amount
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Reference
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-bold text-red-700 uppercase tracking-wider">
                        Reason
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-100">
                    {matchResult.unmatched_items.map((item, idx) => {
                      const isFaktur = item.source_type === 'faktur_pajak';

                      return (
                        <tr key={idx} className="hover:bg-red-50/30 transition-colors duration-150 border-l-4 border-transparent hover:border-red-400">
                          <td className="px-6 py-4">
                            <span className={`inline-flex px-3 py-1.5 rounded-full text-xs font-bold shadow-sm ${
                              isFaktur
                                ? 'bg-blue-100 text-blue-800 border border-blue-200'
                                : 'bg-purple-100 text-purple-800 border border-purple-200'
                            }`}>
                              {item.source_type?.replace('_', ' ').toUpperCase() || 'UNKNOWN'}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm font-semibold text-gray-900">{item.vendor_name || 'N/A'}</div>
                            <div className="text-xs text-gray-500 mt-0.5">{isFaktur ? 'Faktur Pajak' : 'Rekening Koran'}</div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-700 font-medium">{item.date || 'N/A'}</div>
                          </td>
                          <td className="px-6 py-4">
                            <div className={`text-sm font-bold ${isFaktur ? 'text-blue-700' : 'text-purple-700'}`}>
                              {formatCurrency(item.amount || 0)}
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-xs text-gray-600 max-w-xs truncate" title={item.reference || 'N/A'}>
                              {item.reference || 'N/A'}
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-start space-x-2">
                              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                              <div className="text-xs text-red-700 font-medium">
                                No matching {isFaktur ? 'bank transaction' : 'faktur'}
                              </div>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!matchResult && !loading && (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-700 mb-2">Ready to Match</h3>
          <p className="text-gray-500">
            Select your Faktur Pajak and Rekening Koran files, then click "Run Matching" to start.
          </p>
        </div>
      )}
    </div>
  );
};

export default ExcelReconciliation;
