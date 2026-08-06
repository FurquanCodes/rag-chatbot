function Sidebar({ chats, activeChatId, onSelectChat, onNewChat }) {
  return (
    <div className="w-64 bg-gray-950 text-white flex flex-col">
      <div className="p-4">
        <button onClick={onNewChat} className="w-full bg-blue-500 px-3 py-2 rounded-lg text-sm">
          + New Chat
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-2">
        {chats.map((chat) => (
          <button
            key={chat.id}
            onClick={() => onSelectChat(chat.id)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-1 truncate ${
              chat.id === activeChatId ? "bg-gray-700" : "hover:bg-gray-800"
            }`}
          >
            {chat.title}
          </button>
        ))}
      </div>
    </div>
  );
}

export default Sidebar;