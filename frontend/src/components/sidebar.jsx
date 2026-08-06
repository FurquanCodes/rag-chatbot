function Sidebar({ chats, activeChatId, onSelectChat, onNewChat, isOpen, onToggle }) {
  return (
    <div className={`bg-gray-950 text-white flex flex-col transition-all duration-300 ${isOpen ? "w-64" : "w-14"}`}>
      <div className="p-3 flex items-center justify-between">
        {isOpen && <span className="text-sm font-semibold">Chats</span>}
        <button onClick={onToggle} className="text-white text-lg w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-800">
          {isOpen ? "«" : "»"}
        </button>
      </div>
      {isOpen && (
        <>
          <div className="px-3 pb-3">
            <button onClick={onNewChat} className="w-full bg-blue-600 px-3 py-2 rounded-lg text-sm">
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
        </>
      )}
    </div>
  );
}

export default Sidebar;