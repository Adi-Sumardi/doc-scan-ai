import { useState } from 'react';
import { CheckCircle, XCircle, Download, Search, ChevronDown, ChevronUp } from 'lucide-react';
import { useParams } from 'react-router-dom';
import toast from 'react-hot-toast';

interface Match {
  id: string;
  point_a_id?: string;
  point_b_id?: string;
  point_c_id?: string;
  point_e_id?: string;
  match_type: string;
  match_confidence: number;
  details: {
    nomor_faktur?: string;
    tanggal?: string;
    vendor_name?: string;
    amount?: number;
    date_confidence?: number;
    amount_confidence?: number;
  };
}

interface ReconciliationResultsProps {
  results: {
    project_id: string;
    status: string;
    point_a_count: number;
    point_b_count: number;
    point_c_count: number;
    point_e_count: number;
    matches: {
      point_a_vs_c: Match[];
      point_b_vs_e: Match[];
    };
    mismatches: {
      point_a_unmatched: any[];
      point_c_unmatched: any[];
      point_b_unmatched: any[];
      point_e_unmatched: any[];
    };
    summary: {
      total_matched: number;
      total_unmatched: number;
      match_rate: number;
    };
  };
}

const ReconciliationResults = ({ results }: ReconciliationResultsProps) => {
  const { projectId } = useParams<{ projectId: string }>();
  const [activeTab, setActiveTab] = useState<'matched' | 'unmatched' | 'summary'>('summary');
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isExporting, setIsExporting] = useState(false);

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const getMatchTypeColor = (type: string) => {
    switch (type) {
      case 'exact':
        return 'bg-green-100 text-green-800';
      case 'fuzzy':
        return 'bg-yellow-100 text-yellow-800';
      case 'partial':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.95) return 'text-green-600';
    if (confidence >= 0.80) return 'text-blue-600';
    if (confidence >= 0.70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const handleExport = async () => {
    if (!projectId) {
      toast.error('Project ID not found');
      return;
    }

    setIsExporting(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/reconciliation-ppn/reconciliation/${projectId}/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(results)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to export results');
      }

      // Get filename from Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'PPN_Reconciliation_Results.xlsx';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Download file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success('Reconciliation results exported successfully!');
    } catch (error: any) {
      console.error('Failed to export results:', error);
      toast.error(error.message || 'Failed to export results');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-3 sm:p-4 border border-blue-200">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs sm:text-sm font-medium text-blue-900">Match Rate</p>
            <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600" />
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-blue-900">{formatPercentage(results.summary.match_rate / 100)}</p>
          <p className="text-xs text-blue-600 mt-1">
            {results.summary.total_matched} matched
          </p>
        </div>

        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-3 sm:p-4 border border-green-200">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs sm:text-sm font-medium text-green-900">Point A vs C</p>
            <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5 text-green-600" />
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-green-900">{results.matches.point_a_vs_c.length}</p>
          <p className="text-xs text-green-600 mt-1">
            {results.mismatches.point_a_unmatched.length} unmatched
          </p>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-3 sm:p-4 border border-purple-200">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs sm:text-sm font-medium text-purple-900">Point B vs E</p>
            <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5 text-purple-600" />
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-purple-900">{results.matches.point_b_vs_e.length}</p>
          <p className="text-xs text-purple-600 mt-1">
            {results.mismatches.point_b_unmatched.length} unmatched
          </p>
        </div>

        <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-xl p-3 sm:p-4 border border-red-200 col-span-2 lg:col-span-1">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs sm:text-sm font-medium text-red-900">Unmatched Total</p>
            <XCircle className="w-4 h-4 sm:w-5 sm:h-5 text-red-600" />
          </div>
          <p className="text-2xl sm:text-3xl font-bold text-red-900">{results.summary.total_unmatched}</p>
          <p className="text-xs text-red-600 mt-1">Requires review</p>
        </div>
      </div>

      {/* Tabs & Actions */}
      <div className="bg-white rounded-xl shadow-md border border-gray-200">
        <div className="p-3 sm:p-4 border-b border-gray-200">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
            <div className="flex items-center gap-1 sm:gap-2 overflow-x-auto">
              <button
                onClick={() => setActiveTab('summary')}
                className={`px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                  activeTab === 'summary'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Summary
              </button>
              <button
                onClick={() => setActiveTab('matched')}
                className={`px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                  activeTab === 'matched'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Matched ({results.summary.total_matched})
              </button>
              <button
                onClick={() => setActiveTab('unmatched')}
                className={`px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                  activeTab === 'unmatched'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Unmatched ({results.summary.total_unmatched})
              </button>
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
              <div className="relative flex-1 sm:flex-initial">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <button
                onClick={handleExport}
                disabled={isExporting}
                className="flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-green-600"
              >
                {isExporting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span className="text-sm">Exporting...</span>
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
                    <span className="text-sm">Export Excel</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Tab Content */}
        <div className="p-4 sm:p-6">
          {activeTab === 'summary' && (
            <div className="space-y-4 sm:space-y-6">
              <div>
                <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-4">Reconciliation Summary</h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                  {/* Point A vs C Summary */}
                  <div className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-semibold text-gray-900 mb-3">Point A vs C (Faktur Keluaran vs Bukti Potong)</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Total Point A:</span>
                        <span className="font-medium">{results.point_a_count}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Total Point C:</span>
                        <span className="font-medium">{results.point_c_count}</span>
                      </div>
                      <div className="flex justify-between text-green-600">
                        <span>Matched:</span>
                        <span className="font-medium">{results.matches.point_a_vs_c.length}</span>
                      </div>
                      <div className="flex justify-between text-red-600">
                        <span>Unmatched A:</span>
                        <span className="font-medium">{results.mismatches.point_a_unmatched.length}</span>
                      </div>
                      <div className="flex justify-between text-red-600">
                        <span>Unmatched C:</span>
                        <span className="font-medium">{results.mismatches.point_c_unmatched.length}</span>
                      </div>
                      <div className="pt-2 border-t border-gray-200 flex justify-between font-semibold">
                        <span>Match Rate:</span>
                        <span className={results.matches.point_a_vs_c.length / results.point_a_count >= 0.8 ? 'text-green-600' : 'text-yellow-600'}>
                          {formatPercentage((results.matches.point_a_vs_c.length / results.point_a_count) || 0)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Point B vs E Summary */}
                  <div className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-semibold text-gray-900 mb-3">Point B vs E (Faktur Masukan vs Rekening Koran)</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Total Point B:</span>
                        <span className="font-medium">{results.point_b_count}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Total Point E:</span>
                        <span className="font-medium">{results.point_e_count}</span>
                      </div>
                      <div className="flex justify-between text-green-600">
                        <span>Matched:</span>
                        <span className="font-medium">{results.matches.point_b_vs_e.length}</span>
                      </div>
                      <div className="flex justify-between text-red-600">
                        <span>Unmatched B:</span>
                        <span className="font-medium">{results.mismatches.point_b_unmatched.length}</span>
                      </div>
                      <div className="flex justify-between text-red-600">
                        <span>Unmatched E:</span>
                        <span className="font-medium">{results.mismatches.point_e_unmatched.length}</span>
                      </div>
                      <div className="pt-2 border-t border-gray-200 flex justify-between font-semibold">
                        <span>Match Rate:</span>
                        <span className={results.matches.point_b_vs_e.length / results.point_b_count >= 0.8 ? 'text-green-600' : 'text-yellow-600'}>
                          {formatPercentage((results.matches.point_b_vs_e.length / results.point_b_count) || 0)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Overall Summary */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="font-semibold text-blue-900 mb-3">Overall Summary</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-blue-600 mb-1">Total Items</p>
                    <p className="text-2xl font-bold text-blue-900">
                      {results.point_a_count + results.point_b_count + results.point_c_count + results.point_e_count}
                    </p>
                  </div>
                  <div>
                    <p className="text-green-600 mb-1">Total Matched</p>
                    <p className="text-2xl font-bold text-green-900">{results.summary.total_matched}</p>
                  </div>
                  <div>
                    <p className="text-red-600 mb-1">Total Unmatched</p>
                    <p className="text-2xl font-bold text-red-900">{results.summary.total_unmatched}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'matched' && (
            <div className="space-y-4">
              {/* Point A vs C Matches */}
              {results.matches.point_a_vs_c.length > 0 && (
                <div className="border border-gray-200 rounded-lg">
                  <button
                    onClick={() => toggleSection('point_a_vs_c')}
                    className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <CheckCircle className="w-5 h-5 text-green-600" />
                      <span className="font-semibold text-gray-900">
                        Point A vs C Matches ({results.matches.point_a_vs_c.length})
                      </span>
                    </div>
                    {expandedSection === 'point_a_vs_c' ? (
                      <ChevronUp className="w-5 h-5 text-gray-500" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-500" />
                    )}
                  </button>

                  {expandedSection === 'point_a_vs_c' && (
                    <div className="border-t border-gray-200 p-4">
                      <div className="space-y-3">
                        {results.matches.point_a_vs_c.slice(0, 10).map((match, index) => (
                          <div key={index} className="border border-gray-200 rounded-lg p-3 hover:border-blue-300 transition-colors">
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex-1">
                                <p className="font-medium text-gray-900">{match.details.nomor_faktur || 'N/A'}</p>
                                <p className="text-sm text-gray-600">{match.details.vendor_name || 'N/A'}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getMatchTypeColor(match.match_type)}`}>
                                  {match.match_type}
                                </span>
                                <span className={`font-semibold ${getConfidenceColor(match.match_confidence)}`}>
                                  {formatPercentage(match.match_confidence)}
                                </span>
                              </div>
                            </div>
                            <div className="grid grid-cols-3 gap-2 text-sm">
                              <div>
                                <p className="text-gray-500">Date</p>
                                <p className="font-medium">{match.details.tanggal || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-500">Amount</p>
                                <p className="font-medium">{match.details.amount ? formatCurrency(match.details.amount) : 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-500">Match Score</p>
                                <p className="font-medium">
                                  Date: {match.details.date_confidence ? formatPercentage(match.details.date_confidence) : 'N/A'} |
                                  Amt: {match.details.amount_confidence ? formatPercentage(match.details.amount_confidence) : 'N/A'}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                        {results.matches.point_a_vs_c.length > 10 && (
                          <p className="text-sm text-gray-500 text-center py-2">
                            Showing 10 of {results.matches.point_a_vs_c.length} matches. Export to Excel to see all.
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Point B vs E Matches */}
              {results.matches.point_b_vs_e.length > 0 && (
                <div className="border border-gray-200 rounded-lg">
                  <button
                    onClick={() => toggleSection('point_b_vs_e')}
                    className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <CheckCircle className="w-5 h-5 text-purple-600" />
                      <span className="font-semibold text-gray-900">
                        Point B vs E Matches ({results.matches.point_b_vs_e.length})
                      </span>
                    </div>
                    {expandedSection === 'point_b_vs_e' ? (
                      <ChevronUp className="w-5 h-5 text-gray-500" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-500" />
                    )}
                  </button>

                  {expandedSection === 'point_b_vs_e' && (
                    <div className="border-t border-gray-200 p-4">
                      <div className="space-y-3">
                        {results.matches.point_b_vs_e.slice(0, 10).map((match, index) => (
                          <div key={index} className="border border-gray-200 rounded-lg p-3 hover:border-purple-300 transition-colors">
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex-1">
                                <p className="font-medium text-gray-900">{match.details.nomor_faktur || 'N/A'}</p>
                                <p className="text-sm text-gray-600">{match.details.vendor_name || 'N/A'}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getMatchTypeColor(match.match_type)}`}>
                                  {match.match_type}
                                </span>
                                <span className={`font-semibold ${getConfidenceColor(match.match_confidence)}`}>
                                  {formatPercentage(match.match_confidence)}
                                </span>
                              </div>
                            </div>
                            <div className="grid grid-cols-3 gap-2 text-sm">
                              <div>
                                <p className="text-gray-500">Date</p>
                                <p className="font-medium">{match.details.tanggal || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-500">Amount</p>
                                <p className="font-medium">{match.details.amount ? formatCurrency(match.details.amount) : 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-500">Match Score</p>
                                <p className="font-medium">
                                  Date: {match.details.date_confidence ? formatPercentage(match.details.date_confidence) : 'N/A'} |
                                  Amt: {match.details.amount_confidence ? formatPercentage(match.details.amount_confidence) : 'N/A'}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                        {results.matches.point_b_vs_e.length > 10 && (
                          <p className="text-sm text-gray-500 text-center py-2">
                            Showing 10 of {results.matches.point_b_vs_e.length} matches. Export to Excel to see all.
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {results.matches.point_a_vs_c.length === 0 && results.matches.point_b_vs_e.length === 0 && (
                <div className="text-center py-12">
                  <XCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">No matches found</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'unmatched' && (
            <div className="space-y-4">
              {/* Point A Unmatched */}
              {results.mismatches.point_a_unmatched.length > 0 && (
                <div className="border border-gray-200 rounded-lg">
                  <button
                    onClick={() => toggleSection('point_a_unmatched')}
                    className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <XCircle className="w-5 h-5 text-red-600" />
                      <span className="font-semibold text-gray-900">
                        Point A Unmatched - Faktur Keluaran ({results.mismatches.point_a_unmatched.length})
                      </span>
                    </div>
                    {expandedSection === 'point_a_unmatched' ? (
                      <ChevronUp className="w-5 h-5 text-gray-500" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-500" />
                    )}
                  </button>

                  {expandedSection === 'point_a_unmatched' && (
                    <div className="border-t border-gray-200 p-4">
                      <div className="space-y-3">
                        {results.mismatches.point_a_unmatched.slice(0, 10).map((item: any, index) => (
                          <div key={index} className="border border-red-200 bg-red-50 rounded-lg p-3">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                              <div>
                                <p className="text-gray-600 text-xs">Nomor Faktur</p>
                                <p className="font-medium text-gray-900">{item['Nomor Faktur'] || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-600 text-xs">Tanggal</p>
                                <p className="font-medium text-gray-900">{item['Tanggal Faktur'] || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-600 text-xs">Nama Pembeli</p>
                                <p className="font-medium text-gray-900 break-words">{item['Nama Pembeli'] || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-600 text-xs">Total (Rp)</p>
                                <p className="font-medium text-gray-900">{item['Total'] ? formatCurrency(item['Total']) : 'N/A'}</p>
                              </div>
                            </div>
                          </div>
                        ))}
                        {results.mismatches.point_a_unmatched.length > 10 && (
                          <p className="text-sm text-gray-500 text-center py-2">
                            Showing 10 of {results.mismatches.point_a_unmatched.length} items. Export to Excel to see all.
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Point C Unmatched */}
              {results.mismatches.point_c_unmatched.length > 0 && (
                <div className="border border-gray-200 rounded-lg">
                  <button
                    onClick={() => toggleSection('point_c_unmatched')}
                    className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <XCircle className="w-5 h-5 text-red-600" />
                      <span className="font-semibold text-gray-900">
                        Point C Unmatched - Bukti Potong ({results.mismatches.point_c_unmatched.length})
                      </span>
                    </div>
                    {expandedSection === 'point_c_unmatched' ? (
                      <ChevronUp className="w-5 h-5 text-gray-500" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-500" />
                    )}
                  </button>

                  {expandedSection === 'point_c_unmatched' && (
                    <div className="border-t border-gray-200 p-4">
                      <div className="space-y-3">
                        {results.mismatches.point_c_unmatched.slice(0, 10).map((item: any, index) => (
                          <div key={index} className="border border-red-200 bg-red-50 rounded-lg p-3">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                              <div>
                                <p className="text-gray-600 text-xs">Nomor Bukti Potong</p>
                                <p className="font-medium text-gray-900">{item['Nomor Bukti Potong'] || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-600 text-xs">Tanggal</p>
                                <p className="font-medium text-gray-900">{item['Tanggal'] || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-600 text-xs">Nama Pemotong</p>
                                <p className="font-medium text-gray-900 break-words">{item['Nama Pemotong'] || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-600 text-xs">PPh Dipotong (Rp)</p>
                                <p className="font-medium text-gray-900">{item['PPh Dipotong'] ? formatCurrency(item['PPh Dipotong']) : 'N/A'}</p>
                              </div>
                            </div>
                          </div>
                        ))}
                        {results.mismatches.point_c_unmatched.length > 10 && (
                          <p className="text-sm text-gray-500 text-center py-2">
                            Showing 10 of {results.mismatches.point_c_unmatched.length} items. Export to Excel to see all.
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Point B Unmatched */}
              {results.mismatches.point_b_unmatched.length > 0 && (
                <div className="border border-gray-200 rounded-lg">
                  <button
                    onClick={() => toggleSection('point_b_unmatched')}
                    className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <XCircle className="w-5 h-5 text-red-600" />
                      <span className="font-semibold text-gray-900">
                        Point B Unmatched - Faktur Masukan ({results.mismatches.point_b_unmatched.length})
                      </span>
                    </div>
                    {expandedSection === 'point_b_unmatched' ? (
                      <ChevronUp className="w-5 h-5 text-gray-500" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-500" />
                    )}
                  </button>

                  {expandedSection === 'point_b_unmatched' && (
                    <div className="border-t border-gray-200 p-4">
                      <div className="space-y-3">
                        {results.mismatches.point_b_unmatched.slice(0, 10).map((item: any, index) => (
                          <div key={index} className="border border-red-200 bg-red-50 rounded-lg p-3">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                              <div>
                                <p className="text-gray-600 text-xs">Nomor Faktur</p>
                                <p className="font-medium text-gray-900">{item['Nomor Faktur'] || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-600 text-xs">Tanggal</p>
                                <p className="font-medium text-gray-900">{item['Tanggal Faktur'] || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-600 text-xs">Nama Penjual</p>
                                <p className="font-medium text-gray-900 break-words">{item['Nama Penjual'] || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-600 text-xs">Total (Rp)</p>
                                <p className="font-medium text-gray-900">{item['Total'] ? formatCurrency(item['Total']) : 'N/A'}</p>
                              </div>
                            </div>
                          </div>
                        ))}
                        {results.mismatches.point_b_unmatched.length > 10 && (
                          <p className="text-sm text-gray-500 text-center py-2">
                            Showing 10 of {results.mismatches.point_b_unmatched.length} items. Export to Excel to see all.
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Point E Unmatched */}
              {results.mismatches.point_e_unmatched.length > 0 && (
                <div className="border border-gray-200 rounded-lg">
                  <button
                    onClick={() => toggleSection('point_e_unmatched')}
                    className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <XCircle className="w-5 h-5 text-red-600" />
                      <span className="font-semibold text-gray-900">
                        Point E Unmatched - Rekening Koran ({results.mismatches.point_e_unmatched.length})
                      </span>
                    </div>
                    {expandedSection === 'point_e_unmatched' ? (
                      <ChevronUp className="w-5 h-5 text-gray-500" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-500" />
                    )}
                  </button>

                  {expandedSection === 'point_e_unmatched' && (
                    <div className="border-t border-gray-200 p-4">
                      <div className="space-y-3">
                        {results.mismatches.point_e_unmatched.slice(0, 10).map((item: any, index) => (
                          <div key={index} className="border border-red-200 bg-red-50 rounded-lg p-3">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                              <div>
                                <p className="text-gray-600 text-xs">Tanggal</p>
                                <p className="font-medium text-gray-900">{item['Tanggal'] || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-600 text-xs">Keterangan</p>
                                <p className="font-medium text-gray-900 break-words">{item['Keterangan'] || 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-600 text-xs">Debet (Rp)</p>
                                <p className="font-medium text-gray-900">{item['Debet'] ? formatCurrency(item['Debet']) : 'N/A'}</p>
                              </div>
                              <div>
                                <p className="text-gray-600 text-xs">Kredit (Rp)</p>
                                <p className="font-medium text-gray-900">{item['Kredit'] ? formatCurrency(item['Kredit']) : 'N/A'}</p>
                              </div>
                            </div>
                          </div>
                        ))}
                        {results.mismatches.point_e_unmatched.length > 10 && (
                          <p className="text-sm text-gray-500 text-center py-2">
                            Showing 10 of {results.mismatches.point_e_unmatched.length} items. Export to Excel to see all.
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {results.summary.total_unmatched === 0 && (
                <div className="text-center py-12">
                  <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
                  <p className="text-gray-600">All items are matched!</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReconciliationResults;
