function Sidebar({ chats, activeChatId, onSelectChat, onNewChat, isOpen, onToggle }) {
  function handleMouseEnter() {
    if (!isOpen) onToggle();
  }

  return (
    <div
      onMouseEnter={handleMouseEnter}
      className={`bg-gray-950 text-white flex flex-col transition-all duration-300 ${isOpen ? "w-64" : "w-14"}`}
    >
      {isOpen && (
        <div className="p-3 flex items-center justify-between">
          <span className="text-sm font-semibold">Chats</span>
          <button onClick={onToggle} className="text-white text-lg w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-800">
            «
          </button>
        </div>
      )}

      <div className={`px-2 pb-2 ${isOpen ? "pt-2" : "pt-3 flex flex-col items-center"}`}>
        <button
          onClick={onNewChat}
          title="New Chat"
          className={isOpen
            ? "w-full bg-blue-600 px-3 py-2 rounded-lg text-sm"
            : "w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center text-lg"}
        >
          {isOpen ? "New Chat" : "+"}
        </button>
      </div>

      <div className={`flex-1 overflow-y-auto px-2 ${isOpen ? "" : "flex flex-col items-center gap-1"}`}>
        {chats.map((chat) => (
          <button
            key={chat.id}
            onClick={() => onSelectChat(chat.id)}
            title={chat.title}
            className={
              isOpen
                ? `w-full text-left px-3 py-2 rounded-lg text-sm mb-1 truncate ${chat.id === activeChatId ? "bg-gray-700" : "hover:bg-gray-800"}`
                : `w-9 h-9 rounded-lg flex items-center justify-center text-xs mb-1 ${chat.id === activeChatId ? "bg-gray-700" : "hover:bg-gray-800"}`
            }
          >
            {isOpen ? chat.title : chat.title.charAt(0).toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );
}

export default Sidebar;