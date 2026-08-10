import { useState } from "react";

function Sidebar({
  chats,
  activeChatId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  isOpen,
  onToggle,
  searchStrategy,
  setSearchStrategy,
  documents,
  onDeleteDocument,
  isUploading,
}) {
  return (
    <div
      className={`bg-[#0A0D16] text-slate-200 flex flex-col border-r border-[#1A2338] transition-all duration-300 z-20 ${
        isOpen ? "w-72" : "w-16"
      }`}
    >
      <div className="p-4 flex items-center justify-between border-b border-[#1A2338]">
        {isOpen ? (
          <div className="flex items-center gap-2">
            <span className="font-bold text-white text-base tracking-wide">
              RAG Chatbot
            </span>
            <span className="w-2 h-2 rounded-full bg-pink-500 animate-pulse"></span>
          </div>
        ) : (
          <span className="w-2.5 h-2.5 rounded-full bg-pink-500 mx-auto"></span>
        )}
        <button
          onClick={onToggle}
          title={isOpen ? "Collapse Sidebar" : "Expand Sidebar"}
          className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-[#1A2338] transition-colors"
        >
          {isOpen ? "«" : "»"}
        </button>
      </div>

      <div className="p-3">
        <button
          onClick={onNewChat}
          className={`w-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-medium rounded-lg flex items-center justify-center gap-2 transition-all shadow-md ${
            isOpen ? "py-2.5 px-4 text-sm" : "py-2.5 px-0 text-base"
          }`}
        >
          <span>+</span>
          {isOpen && <span>New Chat</span>}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 space-y-5 custom-scrollbar">
        <div>
          {isOpen && (
            <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">
              Conversations
            </h3>
          )}
          <div className="space-y-1">
            {chats.map((chat) => (
              <div
                key={chat.id}
                onClick={() => onSelectChat(chat.id)}
                title={chat.title}
                className={`w-full group rounded-lg transition-colors flex items-center justify-between cursor-pointer ${
                  isOpen ? "px-3 py-2 text-sm" : "p-2 justify-center"
                } ${
                  chat.id === activeChatId
                    ? "bg-[#1E293B] text-white font-medium border border-[#334155]"
                    : "text-slate-400 hover:bg-[#172033] hover:text-slate-200"
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  <span>💬</span>
                  {isOpen && <span className="truncate">{chat.title}</span>}
                </div>
                {isOpen && onDeleteChat && (
                  <button
                    onClick={(e) => onDeleteChat(e, chat.id)}
                    title="Delete Chat"
                    className="opacity-0 group-hover:opacity-100 hover:text-red-400 text-slate-500 p-0.5 rounded transition-all"
                  >
                    🗑️
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {isOpen && (
          <div>
            <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">
              Search Strategy
            </h3>
            <div className="relative">
              <select
                value={searchStrategy}
                onChange={(e) => setSearchStrategy(e.target.value)}
                className="w-full bg-[#172033] text-slate-200 border border-[#26334D] rounded-lg px-3 py-2 text-xs font-medium focus:outline-none focus:border-[#2563EB] cursor-pointer appearance-none"
              >
                <option value="hybrid">⚡ Hybrid (Docs + Wikipedia)</option>
                <option value="documents_only">📄 Documents Only</option>
                <option value="wikipedia_only">🌐 Wikipedia Only</option>
              </select>
              <span className="absolute right-3 top-2.5 text-xs text-slate-400 pointer-events-none">
                ▼
              </span>
            </div>
          </div>
        )}

        {isOpen && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                Indexed Documents
              </h3>
              <span className="text-xs text-slate-500 font-mono">
                ({documents ? documents.length : 0})
              </span>
            </div>

            {documents && documents.length > 0 ? (
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {documents.map((doc) => (
                  <div
                    key={doc.file_id}
                    className="bg-[#172033] border border-[#26334D] rounded-lg p-2.5 flex items-center justify-between gap-2 group hover:border-[#3B82F6] transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-slate-200 truncate">
                        {doc.filename}
                      </p>
                      <p className="text-[10px] text-slate-400 mt-0.5">
                        {doc.chunks || 0} chunks • {(doc.file_size_mb || 0).toFixed(2)} MB
                      </p>
                    </div>
                    <button
                      onClick={() => onDeleteDocument(doc.file_id)}
                      title="Delete document"
                      className="text-slate-500 hover:text-red-400 p-1 rounded opacity-60 group-hover:opacity-100 transition-all"
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="border border-dashed border-[#26334D] rounded-lg p-4 text-center">
                <p className="text-xs text-slate-500 italic">
                  {isUploading ? "Uploading file..." : "No documents uploaded yet"}
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="p-3 border-t border-[#1A2338] text-center">
        {isOpen ? (
          <p className="text-[11px] text-slate-500 font-mono">
            FastAPI + FAISS + Gemini
          </p>
        ) : (
          <span className="text-xs text-slate-600 font-mono">⚡</span>
        )}
      </div>
    </div>
  );
}

export default Sidebar;