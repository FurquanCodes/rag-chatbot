import { useState } from "react";
import UploadBox from "./components/UploadBox";
import ChatWindow from "./components/ChatWindow";

function App() {
  const [messages, setMessages] = useState([]);
  const [fileName, setFileName] = useState("");

  function handleUploaded(name) {
    setFileName(name);
    setMessages((prev) => [...prev, { role: "assistant", text: `Document "${name}" is ready. Ask me anything about it.` }]);
  }

  function handleNewChat() {
    setMessages([]);
  }

  return (
    <div className="flex flex-col h-screen">
      <header className="p-4 bg-gray-900 text-white flex items-center justify-between">
        <span className="text-lg font-semibold">Document Chatbot</span>
        <button onClick={handleNewChat} className="text-sm bg-gray-700 px-3 py-1 rounded-lg">
          New Chat
        </button>
      </header>
      <UploadBox onUploaded={handleUploaded} fileName={fileName} />
      <ChatWindow messages={messages} setMessages={setMessages} />
    </div>
  );
}

export default App;