import { useState, useEffect, useRef, useCallback } from 'react';
import { Plus, MessageSquare, Trash2, X, Menu, RefreshCw, AlertTriangle } from 'lucide-react';

interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at?: string;
}

interface ChatSidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  isOpen: boolean;
  loadState: 'loading' | 'error' | 'ready';
  onToggle: () => void;
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onRetryLoad: () => void;
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '-';
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Hari ini';
    if (days === 1) return 'Kemarin';
    if (days < 7) return `${days} hari lalu`;
    return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short' });
  } catch {
    return '-';
  }
}

function DeleteModal({ sessionTitle, onConfirm, onCancel }: {
  sessionTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    cancelRef.current?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onCancel(); return; }
      // Focus trap: cycle between Cancel and Hapus buttons
      if (e.key === 'Tab') {
        const focusable = [cancelRef.current, confirmRef.current].filter(Boolean) as HTMLElement[];
        if (focusable.length < 2) return;
        const idx = focusable.indexOf(document.activeElement as HTMLElement);
        if (e.shiftKey) {
          e.preventDefault();
          focusable[idx <= 0 ? focusable.length - 1 : idx - 1].focus();
        } else {
          e.preventDefault();
          focusable[(idx + 1) % focusable.length].focus();
        }
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onCancel]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="Konfirmasi hapus">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onCancel} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-sm w-full p-6 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-800 text-sm">Hapus Sesi Chat</h3>
            <p className="text-xs text-slate-500 mt-0.5">Tindakan ini tidak dapat dibatalkan</p>
          </div>
        </div>

        <p className="text-sm text-slate-600 mb-6 pl-[52px]">
          Yakin ingin menghapus sesi <span className="font-medium text-slate-800">"{sessionTitle}"</span> beserta seluruh riwayat chat-nya?
        </p>

        <div className="flex gap-3 justify-end">
          <button
            ref={cancelRef}
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-xl hover:bg-slate-200 transition-colors"
          >
            Batal
          </button>
          <button
            ref={confirmRef}
            onClick={onConfirm}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-xl hover:bg-red-700 transition-colors shadow-sm"
          >
            Hapus
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ChatSidebar({
  sessions, activeSessionId, isOpen, loadState, onToggle,
  onNewSession, onSelectSession, onDeleteSession, onRetryLoad
}: ChatSidebarProps) {
  const [deleteTarget, setDeleteTarget] = useState<Session | null>(null);

  const handleSessionKeyDown = useCallback((e: React.KeyboardEvent, sessionId: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelectSession(sessionId);
      if (window.innerWidth < 1024) onToggle();
    }
  }, [onSelectSession, onToggle]);

  return (
    <>
      {/* Delete confirmation modal */}
      {deleteTarget && (
        <DeleteModal
          sessionTitle={deleteTarget.title}
          onConfirm={() => {
            onDeleteSession(deleteTarget.id);
            setDeleteTarget(null);
          }}
          onCancel={() => setDeleteTarget(null)}
        />
      )}

      {/* Mobile overlay */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 lg:hidden" onClick={onToggle} />
      )}

      {/* Mobile toggle button */}
      <button
        onClick={onToggle}
        className="fixed top-24 left-4 z-30 lg:hidden p-2 bg-white rounded-lg shadow-md border border-slate-200 hover:bg-slate-50 transition-colors"
        aria-label="Buka sidebar"
      >
        <Menu className="w-5 h-5 text-slate-600" />
      </button>

      {/* Sidebar */}
      <nav className={`
        fixed lg:static inset-y-0 left-0 z-50 lg:z-auto
        w-72 bg-slate-900 text-white flex flex-col
        transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        lg:translate-x-0
      `}
        aria-label="Sidebar sesi chat"
      >
        {/* Header */}
        <div className="p-4 flex items-center justify-between border-b border-slate-700/50">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center"
                 role="img" aria-label="R++Con logo">
              <span className="text-white text-[9px] font-bold">R+</span>
            </div>
            <div>
              <h2 className="font-semibold text-sm text-white">R++Con</h2>
              <p className="text-[10px] text-slate-400">Assistant</p>
            </div>
          </div>
          <button onClick={onToggle} className="lg:hidden p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
                  aria-label="Tutup sidebar">
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        {/* New chat button */}
        <div className="p-3">
          <button
            onClick={() => { onNewSession(); if (window.innerWidth < 1024) onToggle(); }}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl border border-slate-600/50
              hover:bg-slate-800 transition-all text-sm font-medium"
            aria-label="Buat chat baru"
          >
            <Plus className="w-4 h-4" />
            Chat Baru
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto px-3 pb-3" role="list" aria-label="Daftar sesi">
          {loadState === 'loading' ? (
            <div className="space-y-2 mt-2">
              {[1, 2, 3].map(i => (
                <div key={i} className="animate-pulse flex items-center gap-2.5 px-3 py-2.5 rounded-xl">
                  <div className="w-4 h-4 bg-slate-700 rounded" />
                  <div className="flex-1 space-y-1.5">
                    <div className="h-3 bg-slate-700 rounded w-3/4" />
                    <div className="h-2 bg-slate-800 rounded w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : loadState === 'error' ? (
            <div className="text-center mt-8 px-4">
              <div className="w-10 h-10 rounded-full bg-red-900/30 flex items-center justify-center mx-auto mb-3">
                <X className="w-5 h-5 text-red-400" />
              </div>
              <p className="text-slate-400 text-xs">Gagal memuat sesi</p>
              <button
                onClick={onRetryLoad}
                className="mt-2 flex items-center gap-1.5 mx-auto text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                <RefreshCw className="w-3 h-3" />
                Coba lagi
              </button>
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center mt-8 px-4">
              <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-3">
                <MessageSquare className="w-5 h-5 text-slate-500" />
              </div>
              <p className="text-slate-500 text-xs">Belum ada sesi chat</p>
              <p className="text-slate-600 text-[11px] mt-1">Mulai chat baru untuk rekonsiliasi</p>
            </div>
          ) : (
            <div className="space-y-0.5">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  onClick={() => { onSelectSession(session.id); if (window.innerWidth < 1024) onToggle(); }}
                  onKeyDown={(e) => handleSessionKeyDown(e, session.id)}
                  tabIndex={0}
                  role="listitem"
                  aria-selected={activeSessionId === session.id}
                  aria-label={`Sesi: ${session.title}`}
                  className={`group flex items-center gap-2.5 px-3 py-2.5 rounded-xl cursor-pointer
                    transition-all text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 ${
                      activeSessionId === session.id
                        ? 'bg-slate-700/80 text-white'
                        : 'text-slate-300 hover:bg-slate-800/60'
                    }`}
                >
                  <MessageSquare className="w-4 h-4 flex-shrink-0 opacity-50" aria-hidden="true" />
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-[13px]">{session.title}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">{formatDate(session.created_at)}</p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteTarget(session);
                    }}
                    className="opacity-0 group-hover:opacity-100 focus:opacity-100 p-1 hover:bg-slate-600 rounded-lg transition-all"
                    aria-label={`Hapus sesi ${session.title}`}
                  >
                    <Trash2 className="w-3.5 h-3.5 text-slate-400" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </nav>
    </>
  );
}
