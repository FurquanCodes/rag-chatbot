function MessageBubble({ role, text, sources }) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 shadow-md leading-relaxed text-sm ${
          isUser
            ? "bg-[#2563EB] text-white rounded-br-none"
            : "bg-[#131B2E] border border-[#22304E] text-slate-200 rounded-bl-none"
        }`}
      >
        <div className="whitespace-pre-wrap">{text}</div>

        {!isUser && sources && sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[#22304E]/80 space-y-1.5">
            <p className="text-[11px] font-bold text-slate-400 tracking-wider uppercase">
              Sources:
            </p>
            <div className="flex flex-wrap gap-1.5">
              {sources.map((src, idx) => (
                <div
                  key={idx}
                  className="bg-[#1C2843] border border-[#2B3C63] rounded-md px-2.5 py-1 text-[11px] text-slate-300 flex items-center gap-1.5"
                >
                  {src.source_type === "wikipedia" ? (
                    <>
                      <span>🌐</span>
                      {src.wikipedia_url ? (
                        <a
                          href={src.wikipedia_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:underline text-blue-400 font-medium"
                        >
                          {src.source_name}
                        </a>
                      ) : (
                        <span>{src.source_name}</span>
                      )}
                    </>
                  ) : (
                    <>
                      <span>📄</span>
                      <span className="font-medium text-slate-200">
                        {src.source_name}
                      </span>
                      {src.page_number && (
                        <span className="text-slate-400">
                          (Page {src.page_number})
                        </span>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default MessageBubble;