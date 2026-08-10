import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import { listDocuments, deleteDocument, checkHealth } from "./api";

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
  const [chats, setChats] = useState(() => {
    const saved = localStorage.getItem("rag_chatbot_chats");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      } catch (e) {}
    }
    return [{ id: Date.now(), title: "New Chat", messages: [], fileName: "" }];
  });

  const [activeChatId, setActiveChatId] = useState(() => {
    const savedId = localStorage.getItem("rag_chatbot_active_chat_id");
    if (savedId) {
      const num = Number(savedId);
      if (!isNaN(num)) return num;
    }
    return chats[0]?.id || Date.now();
  });

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [searchStrategy, setSearchStrategy] = useState("hybrid");
  const [documents, setDocuments] = useState([]);
  const [isConnected, setIsConnected] = useState(true);
  const [isUploading, setIsUploading] = useState(false);

  const activeChat = chats.find((c) => c.id === activeChatId) || chats[0] || { id: Date.now(), title: "New Chat", messages: [], fileName: "" };

  useEffect(() => {
    localStorage.setItem("rag_chatbot_chats", JSON.stringify(chats));
  }, [chats]);

  useEffect(() => {
    if (activeChatId) {
      localStorage.setItem("rag_chatbot_active_chat_id", String(activeChatId));
    }
  }, [activeChatId]);

  useEffect(() => {
    fetchDocuments();
    verifyHealth();

    const interval = setInterval(() => {
      fetchDocuments();
      verifyHealth();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  async function fetchDocuments() {
    try {
      const res = await listDocuments("default");
      if (res && res.data && Array.isArray(res.data.documents)) {
        setDocuments(res.data.documents);
      }
    } catch (err) {
      console.error("Error fetching documents:", err);
    }
  }

  async function verifyHealth() {
    try {
      const res = await checkHealth();
      setIsConnected(res && res.status === "healthy");
    } catch (err) {
      setIsConnected(false);
    }
  }

  function updateActiveChat(updates) {
    setChats((prev) =>
      prev.map((c) => (c.id === activeChatId ? { ...c, ...updates } : c))
    );
  }

  function handleNewChat() {
    const newId = Date.now();
    const newChat = { id: newId, title: "New Chat", messages: [], fileName: "" };
    setChats((prev) => [newChat, ...prev]);
    setActiveChatId(newId);
  }

  function handleDeleteChat(e, chatIdToDelete) {
    e.stopPropagation();
    setChats((prev) => {
      const remaining = prev.filter((c) => c.id !== chatIdToDelete);
      if (remaining.length === 0) {
        const freshId = Date.now();
        setActiveChatId(freshId);
        return [{ id: freshId, title: "New Chat", messages: [], fileName: "" }];
      }
      if (chatIdToDelete === activeChatId) {
        setActiveChatId(remaining[0].id);
      }
      return remaining;
    });
  }

  function handleUploaded(name) {
    updateActiveChat({
      fileName: name,
      messages: [
        ...activeChat.messages,
        {
          role: "assistant",
          text: `Document "${name}" is ready. Ask me anything about it.`,
        },
      ],
    });
    fetchDocuments();
  }

  async function handleDeleteDocument(fileId) {
    try {
      await deleteDocument(fileId, "default");
      fetchDocuments();
    } catch (err) {
      console.error("Error deleting document:", err);
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
    <div className="flex h-screen bg-[#0D111D] font-sans overflow-hidden">
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={setActiveChatId}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
        searchStrategy={searchStrategy}
        setSearchStrategy={setSearchStrategy}
        documents={documents}
        onDeleteDocument={handleDeleteDocument}
        isUploading={isUploading}
      />
      <div className="flex flex-col flex-1 min-w-0">
        <ChatWindow
          messages={activeChat.messages}
          setMessages={setMessages}
          fileName={activeChat.fileName}
          onUploaded={handleUploaded}
          searchStrategy={searchStrategy}
          documentsCount={documents ? documents.length : 0}
          isConnected={isConnected}
          isUploading={isUploading}
          setIsUploading={setIsUploading}
        />
      </div>
    </div>
  );
}

export default App;