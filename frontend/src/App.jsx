import { useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";

function App() {
  const [chats, setChats] = useState([
    { id: 1, title: "New Chat", messages: [], fileName: "" },
  ]);
  const [activeChatId, setActiveChatId] = useState(1);

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
      title: firstUserMessage ? firstUserMessage.text.slice(0, 24) : "New Chat",
    });
  }

  return (
    <div className="flex h-screen">
      <Sidebar chats={chats} activeChatId={activeChatId} onSelectChat={setActiveChatId} onNewChat={handleNewChat} />
      <div className="flex flex-col flex-1">
        <header className="p-4 bg-gray-900 text-white text-lg font-semibold">
          Document Chatbot
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