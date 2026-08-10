import { useState } from "react";

function Sidebar({
  chats,
  activeChatId,
  onSelectChat,
  onNewChat,
  isOpen,
  onToggle,
  documents,
  onDeleteDocument,
  searchType,
  onSearchTypeChange,
  backendConnected,
}) {
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  function handleDeleteClick(e, fileId) {
    e.stopPropagation();
    if (confirmDeleteId === fileId) {
      onDeleteDocument(fileId);
      setConfirmDeleteId(null);
    } else {
      setConfirmDeleteId(fileId);
      setTimeout(() => {
        setConfirmDeleteId(null);
      }, 4000);
    }
  }

  return (
    <div
      className={`bg-gray-950 text-white flex flex-col border-r border-gray-800 transition-all duration-300 ${
        isOpen ? "w-72" : "w-16"
      }`}
    >
      <div className="p-3 border-b border-gray-800 flex items-center justify-between">
        {isOpen ? (
          <div className="flex items-center gap-2">
            <span className="font-bold text-base text-blue-400">RAG Chatbot</span>
            <span
              className={`w-2 h-2 rounded-full ${
                backendConnected ? "bg-emerald-500" : "bg-rose-500 animate-pulse"
              }`}
              title={backendConnected ? "Backend Online" : "Backend Offline"}
            />
          </div>
        ) : (
          <span className="font-bold text-blue-400 mx-auto text-sm">RAG</span>
        )}
        <button
          onClick={onToggle}
          className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-gray-800 transition-colors"
          title={isOpen ? "Collapse Sidebar" : "Expand Sidebar"}
        >
          {isOpen ? "«" : "»"}
        </button>
      </div>

      <div className="p-3">
        <button
          onClick={onNewChat}
          className={`bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2 ${
            isOpen ? "w-full py-2 px-3 text-sm" : "w-10 h-10 mx-auto text-lg"
          }`}
        >
          <span>+</span>
          {isOpen && <span>New Chat</span>}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 space-y-4">
        <div>
          {isOpen && (
            <div className="px-2 pb-1 text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
              Conversations
            </div>
          )}
          <div className="space-y-1">
            {chats.map((chat) => {
              const isActive = chat.id === activeChatId;
              return (
                <button
                  key={chat.id}
                  onClick={() => onSelectChat(chat.id)}
                  title={chat.title}
                  className={`w-full text-left rounded-lg transition-colors flex items-center ${
                    isOpen ? "px-3 py-2 text-sm gap-2" : "w-10 h-10 mx-auto justify-center"
                  } ${
                    isActive
                      ? "bg-gray-800 text-white font-medium border border-gray-700"
                      : "text-gray-400 hover:bg-gray-900 hover:text-gray-200"
                  }`}
                >
                  <span className="text-sm shrink-0">💬</span>
                  {isOpen && <span className="truncate">{chat.title}</span>}
                </button>
              );
            })}
          </div>
        </div>

        {isOpen && (
          <div className="pt-2 border-t border-gray-850">
            <div className="px-2 pb-1.5 text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
              Search Strategy
            </div>
            <div className="px-1">
              <select
                value={searchType}
                onChange={(e) => onSearchTypeChange(e.target.value)}
                className="w-full bg-gray-900 text-gray-200 border border-gray-750 rounded-md px-2.5 py-1.5 text-xs focus:outline-none focus:border-blue-500"
              >
                <option value="hybrid">⚡ Hybrid (Docs + Wikipedia)</option>
                <option value="documents_only">📄 Documents Only</option>
                <option value="wikipedia_only">🌐 Wikipedia Only</option>
              </select>
            </div>
          </div>
        )}

        {isOpen && (
          <div className="pt-2 border-t border-gray-850">
            <div className="px-2 pb-1.5 flex items-center justify-between text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
              <span>Indexed Documents</span>
              <span className="text-gray-500 font-mono">({documents ? documents.length : 0})</span>
            </div>

            {!documents || documents.length === 0 ? (
              <div className="px-2 py-3 text-xs text-gray-500 italic bg-gray-900/40 rounded border border-gray-850 text-center">
                No documents uploaded yet
              </div>
            ) : (
              <div className="space-y-1 max-h-48 overflow-y-auto px-1">
                {documents.map((doc) => (
                  <div
                    key={doc.file_id}
                    className="p-2 rounded bg-gray-900 border border-gray-800 text-xs flex items-center justify-between gap-2 group hover:border-gray-700 transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-gray-200 truncate" title={doc.filename}>
                        📄 {doc.filename}
                      </div>
                      <div className="text-[10px] text-gray-400 flex items-center gap-1.5 mt-0.5">
                        <span>{doc.chunks} chunks</span>
                        {doc.pages > 0 && <span>• {doc.pages} pages</span>}
                      </div>
                    </div>
                    <button
                      onClick={(e) => handleDeleteClick(e, doc.file_id)}
                      className={`text-xs px-2 py-1 rounded transition-colors shrink-0 ${
                        confirmDeleteId === doc.file_id
                          ? "bg-rose-900 text-rose-200 font-bold border border-rose-700"
                          : "text-gray-500 hover:text-rose-400 hover:bg-gray-800"
                      }`}
                      title={confirmDeleteId === doc.file_id ? "Click again to delete" : "Delete document"}
                    >
                      {confirmDeleteId === doc.file_id ? "Confirm?" : "🗑️"}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="p-3 border-t border-gray-800 text-xs text-gray-400 text-center">
        {isOpen ? (
          <div>
            <span>FastAPI + FAISS + Gemini</span>
          </div>
        ) : (
          <span>v1.0</span>
        )}
      </div>
    </div>
  );
}

export default Sidebar;