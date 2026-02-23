import { useRef, useEffect } from 'react';
import { User } from 'lucide-react';
import ChatResultCard from './ChatResultCard';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  attachments?: Array<{ name: string; detected_type?: string; row_count?: number; error?: string }>;
  results?: any;
  created_at?: string;
}

interface ChatMessagesProps {
  messages: ChatMessage[];
  isProcessing?: boolean;
  processingType?: 'chat' | 'reconciliation';
  messagesLoading?: boolean;
  onExport?: (messageId: string) => void;
}

function AssistantAvatar() {
  return (
    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0 shadow-sm"
         role="img" aria-label="R++Con Assistant">
      <span className="text-white text-[10px] font-bold">R+</span>
    </div>
  );
}

function WelcomeMessage() {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg mb-5"
           role="img" aria-label="R++Con logo">
        <span className="text-white text-xl font-bold">R++</span>
      </div>
      <h2 className="text-xl font-semibold text-slate-800 mb-2">R++Con Assistant</h2>
      <p className="text-slate-500 text-sm text-center max-w-md mb-8">
        Asisten rekonsiliasi pajak Anda. Upload file Excel dan berikan instruksi, atau tanyakan seputar perpajakan Indonesia.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-2xl w-full">
        <div className="bg-white rounded-xl border border-slate-200 p-4 hover:border-indigo-300 hover:shadow-sm transition-all">
          <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center mb-3">
            <span className="text-blue-600 text-sm font-semibold">FP</span>
          </div>
          <p className="text-sm font-medium text-slate-700">Faktur Pajak</p>
          <p className="text-xs text-slate-400 mt-1">Nomor Faktur, NPWP, DPP, PPN</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 hover:border-indigo-300 hover:shadow-sm transition-all">
          <div className="w-8 h-8 rounded-lg bg-green-50 flex items-center justify-center mb-3">
            <span className="text-green-600 text-sm font-semibold">BP</span>
          </div>
          <p className="text-sm font-medium text-slate-700">Bukti Potong</p>
          <p className="text-xs text-slate-400 mt-1">Nomor Bukti Potong, NPWP Pemotong</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 hover:border-indigo-300 hover:shadow-sm transition-all">
          <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center mb-3">
            <span className="text-amber-600 text-sm font-semibold">RK</span>
          </div>
          <p className="text-sm font-medium text-slate-700">Rekening Koran</p>
          <p className="text-xs text-slate-400 mt-1">Tanggal, Keterangan, Debet, Kredit</p>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message, onExport }: { message: ChatMessage; onExport?: () => void }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex gap-3 mb-5 justify-end" role="listitem">
        <div className="max-w-[80%] flex flex-col items-end">
          {/* Attachments above bubble */}
          {message.attachments && message.attachments.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-1.5 justify-end">
              {message.attachments.map((att, i) => (
                <div key={`${att.name}-${i}`} className="inline-flex items-center gap-1.5 bg-indigo-50 border border-indigo-200 rounded-lg px-2.5 py-1 text-xs text-indigo-700">
                  <span className="truncate max-w-[150px]">{att.name}</span>
                </div>
              ))}
            </div>
          )}

          {/* User bubble */}
          {message.content?.trim() && (
            <div className="bg-indigo-600 text-white rounded-2xl rounded-br-md px-4 py-3 shadow-sm">
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
            </div>
          )}

          {message.created_at && (
            <div className="text-[11px] text-slate-400 mt-1 mr-1">
              {new Date(message.created_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}
            </div>
          )}
        </div>

        <div className="w-8 h-8 rounded-lg bg-slate-200 flex items-center justify-center flex-shrink-0"
             role="img" aria-label="User">
          <User className="w-4 h-4 text-slate-600" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 mb-5" role="listitem">
      <AssistantAvatar />

      <div className="flex-1 max-w-[85%]">
        <div className="bg-white rounded-2xl rounded-tl-md px-4 py-3 shadow-sm border border-slate-100">
          {message.content?.trim() && (
            <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{message.content}</p>
          )}

          {message.results && (
            <ChatResultCard results={message.results} onExport={onExport} />
          )}
        </div>

        {message.created_at && (
          <div className="text-[11px] text-slate-400 mt-1 ml-1">
            {new Date(message.created_at).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}
          </div>
        )}
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="flex gap-3 mb-5 animate-pulse">
      <div className="w-8 h-8 rounded-lg bg-slate-200" />
      <div className="flex-1 max-w-[60%] space-y-2">
        <div className="bg-slate-200 rounded-2xl h-10 w-full" />
        <div className="bg-slate-200 rounded-2xl h-10 w-3/4" />
      </div>
    </div>
  );
}

export default function ChatMessages({ messages, isProcessing, processingType = 'chat', messagesLoading, onExport }: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6" role="log" aria-label="Chat messages" aria-live="polite">
      {messagesLoading ? (
        <>
          <LoadingSkeleton />
          <LoadingSkeleton />
        </>
      ) : messages.length === 0 && !isProcessing ? (
        <WelcomeMessage />
      ) : (
        <div role="list">
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              onExport={msg.role === 'assistant' && msg.results?.reconciliation?.status === 'completed'
                ? () => onExport?.(msg.id)
                : undefined
              }
            />
          ))}
        </div>
      )}

      {isProcessing && (
        <div className="flex gap-3 mb-5" role="status" aria-label="R++Con sedang mengetik">
          <AssistantAvatar />
          <div className="bg-white rounded-2xl rounded-tl-md px-4 py-3 shadow-sm border border-slate-100">
            <div className="flex items-center gap-2.5">
              <div className="flex gap-1" aria-hidden="true">
                <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-sm text-slate-400">
                {processingType === 'reconciliation' ? 'Memproses rekonsiliasi...' : 'Mengetik...'}
              </span>
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
