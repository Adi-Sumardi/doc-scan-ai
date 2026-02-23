import { useState } from 'react';
import {
  CheckCircle, XCircle, ChevronDown, ChevronRight,
  Download, AlertTriangle
} from 'lucide-react';
import FileChip from './FileChip';

interface ChatResultCardProps {
  results: {
    files_detected?: Array<{ name: string; detected_type: string; row_count: number; error?: string }>;
    company_npwp?: string;
    reconciliation?: {
      status: string;
      error?: string;
      point_a_count?: number;
      point_b_count?: number;
      point_c_count?: number;
      point_e_count?: number;
      matches?: {
        point_a_vs_c?: any[];
        point_b_vs_e?: any[];
      };
      mismatches?: {
        point_a_unmatched?: any[];
        point_c_unmatched?: any[];
        point_b_unmatched?: any[];
        point_e_unmatched?: any[];
      };
      summary?: {
        match_rate?: number;
        total_auto_matched?: number;
        total_suggested?: number;
        total_unmatched?: number;
        match_rate_a_vs_c?: number;
        match_rate_b_vs_e?: number;
        [key: string]: any;
      };
    };
  };
  onExport?: () => void;
}

function formatRupiah(value: any): string {
  if (value === null || value === undefined || value === 0) return '-';
  const num = typeof value === 'number' ? value : parseFloat(String(value));
  if (isNaN(num)) return '-';
  return `Rp ${Math.round(num).toLocaleString('id-ID')}`;
}

function getMatchKey(m: any, index: number): string {
  const faktur = m.details?.nomor_faktur || m.nomor_faktur || '';
  const vendor = m.details?.vendor_name || '';
  return faktur ? `${faktur}-${vendor}-${index}` : `match-${index}`;
}

function getUnmatchedKey(item: any, groupKey: string, index: number): string {
  const id = item[groupKey] || item['Nomor Faktur'] || item['Keterangan'] || '';
  return id ? `${id}-${index}` : `unmatched-${index}`;
}

export default function ChatResultCard({ results, onExport }: ChatResultCardProps) {
  const [showMatched, setShowMatched] = useState(false);
  const [showUnmatched, setShowUnmatched] = useState(false);

  const filesDetected = results.files_detected || [];
  const recon = results.reconciliation;
  const summary = recon?.summary;

  const totalMatched = (summary?.total_auto_matched || 0) + (summary?.total_suggested || 0);
  const totalUnmatched = summary?.total_unmatched || 0;
  const matchRate = summary?.match_rate || 0;

  const matchesAC = recon?.matches?.point_a_vs_c || [];
  const matchesBE = recon?.matches?.point_b_vs_e || [];
  const unmatchedA = recon?.mismatches?.point_a_unmatched || [];
  const unmatchedC = recon?.mismatches?.point_c_unmatched || [];
  const unmatchedB = recon?.mismatches?.point_b_unmatched || [];
  const unmatchedE = recon?.mismatches?.point_e_unmatched || [];

  return (
    <div className="space-y-3 mt-2">
      {/* Files detected */}
      {filesDetected.length > 0 && (
        <div className="space-y-1.5" role="list" aria-label="File terdeteksi">
          {filesDetected.map((f) => (
            <div key={`${f.name}-${f.detected_type}`} className="flex items-center gap-2 text-sm" role="listitem">
              {f.error || f.detected_type === 'unknown' ? (
                <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" aria-label="Peringatan" />
              ) : (
                <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" aria-label="Terdeteksi" />
              )}
              <FileChip
                name={f.name}
                detectedType={f.detected_type}
                rowCount={f.row_count}
                error={f.error}
              />
            </div>
          ))}
        </div>
      )}

      {/* NPWP */}
      {results.company_npwp && (
        <p className="text-sm text-gray-600">
          NPWP Perusahaan: <span className="font-mono font-medium">{results.company_npwp}</span>
        </p>
      )}

      {/* Reconciliation failed */}
      {recon?.status === 'failed' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700" role="alert">
          <p className="font-medium">Rekonsiliasi gagal</p>
          <p>{recon.error}</p>
        </div>
      )}

      {/* Reconciliation results */}
      {recon?.status === 'completed' && summary && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-3 gap-2" role="group" aria-label="Ringkasan rekonsiliasi">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-blue-700">{matchRate.toFixed(1)}%</div>
              <div className="text-xs text-blue-600">Match Rate</div>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-green-700">{totalMatched}</div>
              <div className="text-xs text-green-600">Matched</div>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-red-700">{totalUnmatched}</div>
              <div className="text-xs text-red-600">Unmatched</div>
            </div>
          </div>

          {/* Point counts */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
            <div className="bg-gray-50 rounded-lg p-2 text-center">
              <div className="font-semibold">{recon.point_a_count || 0}</div>
              <div className="text-xs text-gray-500">Point A</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-2 text-center">
              <div className="font-semibold">{recon.point_b_count || 0}</div>
              <div className="text-xs text-gray-500">Point B</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-2 text-center">
              <div className="font-semibold">{recon.point_c_count || 0}</div>
              <div className="text-xs text-gray-500">Point C</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-2 text-center">
              <div className="font-semibold">{recon.point_e_count || 0}</div>
              <div className="text-xs text-gray-500">Point E</div>
            </div>
          </div>

          {/* Matched details (collapsible) */}
          {(matchesAC.length > 0 || matchesBE.length > 0) && (
            <button
              onClick={() => setShowMatched(!showMatched)}
              className="flex items-center gap-2 text-sm font-medium text-green-700 hover:text-green-800 transition-colors"
              aria-expanded={showMatched}
              aria-controls="matched-details"
            >
              {showMatched ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <CheckCircle className="w-4 h-4" />
              Detail Matched ({matchesAC.length + matchesBE.length})
            </button>
          )}
          {showMatched && (
            <div id="matched-details" className="space-y-2 pl-4 border-l-2 border-green-200">
              {matchesAC.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-green-600 mb-1">Point A vs C ({matchesAC.length})</p>
                  <div className="space-y-1 max-h-60 overflow-y-auto">
                    {matchesAC.slice(0, 10).map((m: any, i: number) => (
                      <div key={getMatchKey(m, i)} className="bg-green-50 rounded p-2 text-xs">
                        <div className="flex justify-between">
                          <span className="font-medium">{m.details?.nomor_faktur || '-'}</span>
                          <span className="text-green-600">{((m.match_confidence || 0) * 100).toFixed(0)}%</span>
                        </div>
                        <div className="text-gray-600">{m.details?.vendor_name || '-'} | {formatRupiah(m.details?.amount)}</div>
                      </div>
                    ))}
                    {matchesAC.length > 10 && (
                      <p className="text-xs text-gray-500 italic">+{matchesAC.length - 10} lainnya (export untuk melihat semua)</p>
                    )}
                  </div>
                </div>
              )}
              {matchesBE.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-purple-600 mb-1">Point B vs E ({matchesBE.length})</p>
                  <div className="space-y-1 max-h-60 overflow-y-auto">
                    {matchesBE.slice(0, 10).map((m: any, i: number) => (
                      <div key={getMatchKey(m, i)} className="bg-purple-50 rounded p-2 text-xs">
                        <div className="flex justify-between">
                          <span className="font-medium">{m.details?.nomor_faktur || '-'}</span>
                          <span className="text-purple-600">{((m.match_confidence || 0) * 100).toFixed(0)}%</span>
                        </div>
                        <div className="text-gray-600">{m.details?.vendor_name || '-'} | {formatRupiah(m.details?.amount)}</div>
                      </div>
                    ))}
                    {matchesBE.length > 10 && (
                      <p className="text-xs text-gray-500 italic">+{matchesBE.length - 10} lainnya (export untuk melihat semua)</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Unmatched details (collapsible) */}
          {totalUnmatched > 0 && (
            <button
              onClick={() => setShowUnmatched(!showUnmatched)}
              className="flex items-center gap-2 text-sm font-medium text-red-700 hover:text-red-800 transition-colors"
              aria-expanded={showUnmatched}
              aria-controls="unmatched-details"
            >
              {showUnmatched ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <XCircle className="w-4 h-4" />
              Detail Unmatched ({totalUnmatched})
            </button>
          )}
          {showUnmatched && (
            <div id="unmatched-details" className="space-y-2 pl-4 border-l-2 border-red-200">
              {[
                { label: 'Point A Unmatched', items: unmatchedA, key: 'Nomor Faktur' },
                { label: 'Point C Unmatched', items: unmatchedC, key: 'Nomor Bukti Potong' },
                { label: 'Point B Unmatched', items: unmatchedB, key: 'Nomor Faktur' },
                { label: 'Point E Unmatched', items: unmatchedE, key: 'Keterangan' },
              ].filter(g => g.items.length > 0).map((group) => (
                <div key={group.label}>
                  <p className="text-xs font-semibold text-red-600 mb-1">{group.label} ({group.items.length})</p>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {group.items.slice(0, 5).map((item: any, i: number) => (
                      <div key={getUnmatchedKey(item, group.key, i)} className="bg-red-50 rounded p-2 text-xs">
                        <span className="font-medium">{item[group.key] || item['Nomor Faktur'] || item['Keterangan'] || '-'}</span>
                        {item['Total (Rp)'] && <span className="text-gray-600 ml-2">{formatRupiah(item['Total (Rp)'])}</span>}
                      </div>
                    ))}
                    {group.items.length > 5 && (
                      <p className="text-xs text-gray-500 italic">+{group.items.length - 5} lainnya</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Export button */}
          {onExport && (
            <button
              onClick={onExport}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm rounded-lg
                hover:bg-green-700 transition-colors shadow-sm"
              aria-label="Export hasil rekonsiliasi ke Excel"
            >
              <Download className="w-4 h-4" />
              Export Excel
            </button>
          )}
        </>
      )}
    </div>
  );
}
