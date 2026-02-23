import { FileSpreadsheet, X } from 'lucide-react';

interface FileChipProps {
  name: string;
  detectedType?: string;
  rowCount?: number;
  error?: string;
  onRemove?: () => void;
  compact?: boolean;
}

const TYPE_LABELS: Record<string, string> = {
  faktur_pajak: 'Faktur Pajak',
  bukti_potong: 'Bukti Potong',
  rekening_koran: 'Rekening Koran',
  unknown: 'Unknown',
  error: 'Error',
};

export default function FileChip({ name, detectedType, rowCount, error, onRemove, compact }: FileChipProps) {
  const hasError = error || detectedType === 'error' || detectedType === 'unknown';

  return (
    <div className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-sm
      ${hasError ? 'bg-red-50 border-red-200 text-red-700' : 'bg-blue-50 border-blue-200 text-blue-700'}`}
    >
      <FileSpreadsheet className="w-3.5 h-3.5 flex-shrink-0" />
      <span className="truncate max-w-[200px]">{name}</span>
      {!compact && detectedType && detectedType !== 'error' && detectedType !== 'unknown' && (
        <span className="text-xs bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded">
          {TYPE_LABELS[detectedType] || detectedType}
        </span>
      )}
      {!compact && rowCount !== undefined && rowCount > 0 && (
        <span className="text-xs text-blue-500">{rowCount} rows</span>
      )}
      {onRemove && (
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          className="ml-0.5 p-0.5 rounded-full hover:bg-blue-200 transition-colors"
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </div>
  );
}
