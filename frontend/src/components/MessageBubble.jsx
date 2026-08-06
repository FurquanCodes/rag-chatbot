function MessageBubble({ role, text, source }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-[75%] p-3 rounded-lg ${isUser ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-100"}`}>
        <p>{text}</p>
        {source && <span className="text-xs text-gray-400 block mt-1">Source: {source}</span>}
      </div>
    </div>
  );
}

export default MessageBubble;