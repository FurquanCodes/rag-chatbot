import { useState, useEffect, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import { listDocuments, deleteDocument, checkBackendHealth } from "./api";

const STOP_WORDS = new Set([
  "the", "a", "an", "is", "are", "was", "were", "am", "be", "been", "being",
  "what", "who", "when", "where", "why", "how", "which", "whom",
  "can", "could", "would", "should", "will", "shall", "may", "might", "must",
  "do", "does", "did", "doing",
  "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "my", "your", "his", "its", "our", "their",
  "to", "of", "in", "on", "for", "with", "from", "about", "into", "at", "by", "as",
  "please", "tell", "explain", "give", "show", "describe", "this", "that", "these", "those",
]);

function generateTitle(text) {
  const words = text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, "")
    .split(/\s+/)
    .filter((w) => w && !STOP_WORDS.has(w));

  if (words.length === 0) return "New Chat";

  return words
    .slice(0, 4)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function App() {
  const [chats, setChats] = useState([
    { id: 1, title: "New Chat", messages: [], fileName: "" },
  ]);
  const [activeChatId, setActiveChatId] = useState(1);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [documents, setDocuments] = useState([]);
  const [searchType, setSearchType] = useState("hybrid");
  const [backendConnected, setBackendConnected] = useState(false);
  const collectionId = "default";

  const activeChat = chats.find((c) => c.id === activeChatId) || chats[0];

  const fetchDocs = useCallback(async () => {
    try {
      const res = await listDocuments(collectionId);
      if (res && res.data && res.data.documents) {
        setDocuments(res.data.documents);
      }
    } catch {
      setDocuments([]);
    }
  }, [collectionId]);

  const verifyHealth = useCallback(async () => {
    try {
      await checkBackendHealth();
      setBackendConnected(true);
    } catch {
      setBackendConnected(false);
    }
  }, []);

  useEffect(() => {
    verifyHealth();
    fetchDocs();
    const interval = setInterval(() => {
      verifyHealth();
    }, 15000);
    return () => clearInterval(interval);
  }, [verifyHealth, fetchDocs]);

  function updateActiveChat(updates) {
    setChats((prev) =>
      prev.map((c) => (c.id === activeChatId ? { ...c, ...updates } : c))
    );
  }

  function handleNewChat() {
    const newId = Date.now();
    setChats((prev) => [
      ...prev,
      { id: newId, title: "New Chat", messages: [], fileName: "" },
    ]);
    setActiveChatId(newId);
  }

  async function handleUploaded(uploadResult) {
    await fetchDocs();
    const files = uploadResult?.data?.uploaded_files || [];
    const count = files.length;
    const name = files.map((f) => f.filename).join(", ") || "Uploaded Document";

    updateActiveChat({
      fileName: name,
      messages: [
        ...activeChat.messages,
        {
          role: "assistant",
          text: `Successfully processed ${count} file(s): "${name}". Ask me anything about your documents!`,
        },
      ],
    });
  }

  async function handleDeleteDocument(fileId) {
    try {
      await deleteDocument(fileId, collectionId);
      await fetchDocs();
    } catch (err) {
      alert("Failed to delete document: " + err.message);
    }
  }

  function setMessages(updater) {
    const newMessages =
      typeof updater === "function" ? updater(activeChat.messages) : updater;
    const firstUserMessage = newMessages.find((m) => m.role === "user");
    updateActiveChat({
      messages: newMessages,
      title: firstUserMessage
        ? generateTitle(firstUserMessage.text)
        : "New Chat",
    });
  }

  return (
    <div className="flex h-screen bg-gray-900 overflow-hidden font-sans">
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={setActiveChatId}
        onNewChat={handleNewChat}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
        documents={documents}
        onDeleteDocument={handleDeleteDocument}
        searchType={searchType}
        onSearchTypeChange={setSearchType}
        backendConnected={backendConnected}
      />
      <div className="flex flex-col flex-1 h-full overflow-hidden">
        <header className="px-6 py-3.5 bg-gray-950 border-b border-gray-800 text-white flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <h1 className="text-base font-semibold tracking-wide">
              {activeChat ? activeChat.title : "Chatbot"}
            </h1>
            <span className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded-full border border-gray-700 font-mono">
              {searchType === "hybrid"
                ? "Hybrid RAG"
                : searchType === "documents_only"
                ? "Docs Only"
                : "Wikipedia Only"}
            </span>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <span className="text-gray-400">
              {documents.length} document(s) in index
            </span>
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border ${
                backendConnected
                  ? "bg-emerald-950/80 text-emerald-300 border-emerald-800"
                  : "bg-rose-950/80 text-rose-300 border-rose-800"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  backendConnected ? "bg-emerald-400" : "bg-rose-400 animate-ping"
                }`}
              />
              <span>{backendConnected ? "Backend Ready" : "Disconnected"}</span>
            </div>
          </div>
        </header>

        <ChatWindow
          messages={activeChat ? activeChat.messages : []}
          setMessages={setMessages}
          fileName={activeChat ? activeChat.fileName : ""}
          onUploaded={handleUploaded}
          searchType={searchType}
          documents={documents}
          collectionId={collectionId}
          backendConnected={backendConnected}
        />
      </div>
    </div>
  );
}

export default App;