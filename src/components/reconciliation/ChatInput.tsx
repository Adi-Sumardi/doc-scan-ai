import { useState, useRef, useCallback } from 'react';
import { Paperclip, Send, Zap, ZapOff } from 'lucide-react';
import toast from 'react-hot-toast';
import FileChip from './FileChip';

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const MAX_FILES = 10;

interface ChatInputProps {
  onSend: (prompt: string, files: File[], useAI: boolean) => void;
  disabled?: boolean;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [prompt, setPrompt] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [useAI, setUseAI] = useState(true);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const validateAndAddFiles = useCallback((newFiles: File[]) => {
    const validFiles: File[] = [];
    for (const f of newFiles) {
      if (!f.name.endsWith('.xlsx') && !f.name.endsWith('.xls')) {
        toast.error(`${f.name}: Hanya file .xlsx atau .xls yang didukung`);
        continue;
      }
      if (f.size > MAX_FILE_SIZE) {
        toast.error(`${f.name}: File terlalu besar (${formatFileSize(f.size)}). Maks ${formatFileSize(MAX_FILE_SIZE)}`);
        continue;
      }
      if (f.size === 0) {
        toast.error(`${f.name}: File kosong`);
        continue;
      }
      validFiles.push(f);
    }

    setFiles(prev => {
      const total = prev.length + validFiles.length;
      if (total > MAX_FILES) {
        toast.error(`Maksimal ${MAX_FILES} file`);
        return [...prev, ...validFiles.slice(0, MAX_FILES - prev.length)];
      }
      return [...prev, ...validFiles];
    });
  }, []);

  const handleSend = useCallback(() => {
    if (disabled || (!prompt.trim() && files.length === 0)) return;
    onSend(prompt.trim(), files, useAI);
    setPrompt('');
    setFiles([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [prompt, files, useAI, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      validateAndAddFiles(Array.from(e.target.files));
    }
    e.target.value = '';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    validateAndAddFiles(Array.from(e.dataTransfer.files));
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const canSend = !disabled && (prompt.trim() || files.length > 0);

  return (
    <div
      className={`bg-white border-t border-slate-200 px-4 sm:px-6 py-3 transition-colors relative ${isDragOver ? 'bg-indigo-50 border-indigo-300' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      role="form"
      aria-label="Chat input"
    >
      {/* Attached files */}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2.5" role="list" aria-label="File terlampir">
          {files.map((file, i) => (
            <FileChip key={`${file.name}-${file.size}-${file.lastModified}`} name={file.name} onRemove={() => removeFile(i)} compact />
          ))}
        </div>
      )}

      {/* Input container */}
      <div className="flex items-end gap-2">
        {/* Left actions */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            className="p-2 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors disabled:opacity-40"
            aria-label="Lampirkan file Excel"
          >
            <Paperclip className="w-5 h-5" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            multiple
            onChange={handleFileSelect}
            className="hidden"
            aria-hidden="true"
          />

          <button
            onClick={() => setUseAI(!useAI)}
            disabled={disabled}
            className={`p-2 rounded-lg transition-colors disabled:opacity-40 ${
              useAI
                ? 'text-indigo-600 bg-indigo-50 hover:bg-indigo-100'
                : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'
            }`}
            aria-label={useAI ? 'AI Matching aktif, klik untuk menonaktifkan' : 'AI Matching nonaktif, klik untuk mengaktifkan'}
            aria-pressed={useAI}
          >
            {useAI ? <Zap className="w-5 h-5" /> : <ZapOff className="w-5 h-5" />}
          </button>
        </div>

        {/* Textarea */}
        <div className="flex-1">
          <textarea
            ref={textareaRef}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={isDragOver ? 'Drop file di sini...' : 'Tanyakan seputar perpajakan atau instruksi rekonsiliasi...'}
            rows={1}
            aria-label="Pesan"
            className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm
              text-slate-700 placeholder:text-slate-400
              focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-300 focus:bg-white
              disabled:opacity-40 disabled:bg-slate-100 max-h-32 overflow-y-auto transition-all"
            style={{ minHeight: '42px' }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = 'auto';
              target.style.height = Math.min(target.scrollHeight, 128) + 'px';
            }}
          />
        </div>

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={!canSend}
          className={`p-2.5 rounded-xl transition-all ${
            canSend
              ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-700 hover:to-purple-700 shadow-sm hover:shadow'
              : 'bg-slate-100 text-slate-300 cursor-not-allowed'
          }`}
          aria-label="Kirim pesan"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>

      {/* Drag overlay */}
      {isDragOver && (
        <div className="absolute inset-0 flex items-center justify-center bg-indigo-50/90 rounded-lg pointer-events-none z-10 border-2 border-dashed border-indigo-400">
          <p className="text-indigo-600 font-medium text-sm">Drop file Excel di sini</p>
        </div>
      )}
    </div>
  );
}
