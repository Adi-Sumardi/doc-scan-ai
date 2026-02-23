import { useState, useEffect, useCallback, useRef } from 'react';
import toast from 'react-hot-toast';
import { apiService } from '../services/api';
import type { ReconciliationSession, ReconciliationMessage } from '../services/api';
import ChatSidebar from '../components/reconciliation/ChatSidebar';
import ChatMessages from '../components/reconciliation/ChatMessages';
import ChatInput from '../components/reconciliation/ChatInput';

export default function ReconciliationChat() {
  const [sessions, setSessions] = useState<ReconciliationSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ReconciliationMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingType, setProcessingType] = useState<'chat' | 'reconciliation'>('chat');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loadState, setLoadState] = useState<'loading' | 'error' | 'ready'>('loading');
  const [messagesLoading, setMessagesLoading] = useState(false);

  // AbortController ref for cancelling in-flight session loads
  const loadSessionAbortRef = useRef<AbortController | null>(null);

  const loadSessions = useCallback(async () => {
    try {
      const data = await apiService.reconciliation.getSessions();
      setSessions(data);
      setLoadState('ready');
    } catch {
      setLoadState('error');
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Load messages when session changes — with AbortController to cancel stale requests
  useEffect(() => {
    if (activeSessionId) {
      if (loadSessionAbortRef.current) {
        loadSessionAbortRef.current.abort();
      }
      const controller = new AbortController();
      loadSessionAbortRef.current = controller;

      setMessagesLoading(true);
      apiService.reconciliation.getSession(activeSessionId)
        .then(data => {
          if (!controller.signal.aborted) {
            setMessages(data.messages || []);
            setMessagesLoading(false);
          }
        })
        .catch(() => {
          if (!controller.signal.aborted) {
            toast.error('Gagal memuat sesi');
            setMessagesLoading(false);
          }
        });

      return () => { controller.abort(); };
    } else {
      setMessages([]);
      setMessagesLoading(false);
    }
  }, [activeSessionId]);

  const handleNewSession = useCallback(async () => {
    try {
      const session = await apiService.reconciliation.createSession();
      setSessions(prev => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([]);
    } catch {
      toast.error('Gagal membuat sesi baru');
    }
  }, []);

  const handleSelectSession = useCallback((id: string) => {
    setActiveSessionId(id);
  }, []);

  const handleDeleteSession = useCallback(async (id: string) => {
    try {
      await apiService.reconciliation.deleteSession(id);
      setSessions(prev => prev.filter(s => s.id !== id));
      setActiveSessionId(prev => prev === id ? null : prev);
      if (activeSessionId === id) {
        setMessages([]);
      }
      toast.success('Sesi dihapus');
    } catch {
      toast.error('Gagal menghapus sesi');
    }
  }, [activeSessionId]);

  const handleSend = useCallback(async (prompt: string, files: File[], useAI: boolean) => {
    // Prevent double-submit
    if (isProcessing) return;

    let sessionId = activeSessionId;

    // Set processing early to prevent race condition on rapid clicks
    setIsProcessing(true);

    // Auto-create session if none active
    if (!sessionId) {
      try {
        const session = await apiService.reconciliation.createSession();
        setSessions(prev => [session, ...prev]);
        setActiveSessionId(session.id);
        sessionId = session.id;
      } catch {
        toast.error('Gagal membuat sesi baru');
        setIsProcessing(false);
        return;
      }
    }

    const fileNames = files.map(f => f.name);

    // Optimistic: show user message immediately with unique ID
    const tempUserMsg: ReconciliationMessage = {
      id: `temp-${crypto.randomUUID()}`,
      role: 'user',
      content: prompt,
      attachments: fileNames.map(name => ({ name })),
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempUserMsg]);
    setProcessingType(files.length > 0 ? 'reconciliation' : 'chat');

    try {
      const formData = new FormData();
      formData.append('prompt', prompt);
      formData.append('use_ai', String(useAI));
      files.forEach(file => formData.append('files', file));

      const result = await apiService.reconciliation.sendMessage(sessionId, formData);

      // Replace temp user message with real one, add assistant message
      setMessages(prev => [
        ...prev.filter(m => m.id !== tempUserMsg.id),
        result.user_message,
        result.assistant_message,
      ]);

      // Update session title in sidebar from server response
      if (result.user_message.content || fileNames.length > 0) {
        setSessions(prev => prev.map(s =>
          s.id === sessionId
            ? {
                ...s,
                title: result.user_message.content?.slice(0, 50) || `Rekonsiliasi ${fileNames[0] || ''}`.slice(0, 50),
                updated_at: new Date().toISOString()
              }
            : s
        ));
      }

    } catch (err: unknown) {
      // Remove temp user message on error
      setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
      let errorMsg = 'Gagal memproses pesan';
      if (err instanceof Error && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        errorMsg = axiosErr.response?.data?.detail || errorMsg;
      }
      toast.error(errorMsg);
    } finally {
      setIsProcessing(false);
    }
  }, [activeSessionId, isProcessing]);

  const handleExport = useCallback(async (messageId: string) => {
    if (!activeSessionId) return;

    try {
      const blob = await apiService.reconciliation.exportResults(activeSessionId, messageId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Reconciliation_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      // Delay revoke to allow download to start (Safari compatibility)
      setTimeout(() => window.URL.revokeObjectURL(url), 1000);
      toast.success('Excel berhasil diunduh');
    } catch {
      toast.error('Gagal mengunduh Excel');
    }
  }, [activeSessionId]);

  return (
    <div className="flex h-[calc(100vh-5rem)] -m-6 -mt-2 overflow-hidden">
      {/* Sidebar */}
      <ChatSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        isOpen={sidebarOpen}
        loadState={loadState}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        onNewSession={handleNewSession}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        onRetryLoad={loadSessions}
      />

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0 bg-gradient-to-b from-slate-50 to-white">
        {/* Chat header */}
        <div className="bg-white/80 backdrop-blur-sm border-b border-slate-200 px-4 sm:px-6 py-3 flex items-center gap-3">
          <div className="pl-10 lg:pl-0 flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-sm"
                 role="img" aria-label="R++Con Assistant logo">
              <span className="text-white text-xs font-bold">R+</span>
            </div>
            <div>
              <h1 className="font-semibold text-slate-800 text-sm">
                {activeSessionId
                  ? sessions.find(s => s.id === activeSessionId)?.title || 'R++Con Assistant'
                  : 'R++Con Assistant'
                }
              </h1>
              <p className="text-xs text-slate-400">
                Tax reconciliation AI assistant
              </p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <ChatMessages
          messages={messages}
          isProcessing={isProcessing}
          processingType={processingType}
          messagesLoading={messagesLoading}
          onExport={handleExport}
        />

        {/* Input */}
        <ChatInput
          onSend={handleSend}
          disabled={isProcessing}
        />
      </div>
    </div>
  );
}
