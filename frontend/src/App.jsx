import { useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";

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

  const activeChat = chats.find((c) => c.id === activeChatId);

  function updateActiveChat(updates) {
    setChats((prev) => prev.map((c) => (c.id === activeChatId ? { ...c, ...updates } : c)));
  }

  function handleNewChat() {
    const newId = Date.now();
    setChats((prev) => [...prev, { id: newId, title: "New Chat", messages: [], fileName: "" }]);
    setActiveChatId(newId);
  }

  function handleUploaded(name) {
    updateActiveChat({
      fileName: name,
      messages: [...activeChat.messages, { role: "assistant", text: `Document "${name}" is ready. Ask me anything about it.` }],
    });
  }

  function setMessages(updater) {
    const newMessages = typeof updater === "function" ? updater(activeChat.messages) : updater;
    const firstUserMessage = newMessages.find((m) => m.role === "user");
    updateActiveChat({
      messages: newMessages,
      title: firstUserMessage ? generateTitle(firstUserMessage.text) : "New Chat",
    });
  }

  return (
    <div className="flex h-screen bg-gray-900">
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={setActiveChatId}
        onNewChat={handleNewChat}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
      />
      <div className="flex flex-col flex-1">
        <header className="p-4 bg-gray-900 border-b border-gray-800 text-white text-lg font-semibold">
          Chatbot
        </header>
        <ChatWindow
          messages={activeChat.messages}
          setMessages={setMessages}
          fileName={activeChat.fileName}
          onUploaded={handleUploaded}
        />
      </div>
    </div>
  );
}

export default App;