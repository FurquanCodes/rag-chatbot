import ReactMarkdown from "react-markdown";

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
        {isUser ? (
          <div className="whitespace-pre-wrap">{text}</div>
        ) : (
          <div className="prose prose-invert max-w-none text-sm leading-relaxed text-slate-200">
            <ReactMarkdown>{text}</ReactMarkdown>
          </div>
        )}

        {!isUser && sources && sources.length > 0 && (
          <div className="mt-4 pt-3 border-t border-[#22304E]/80 space-y-2">
            <p className="text-[11px] font-bold text-slate-400 tracking-wider uppercase">
              Sources:
            </p>
            <div className="space-y-2">
              {sources.map((src, idx) => {
                const isPptx =
                  src.file_type === "pptx" ||
                  (src.source_name &&
                    src.source_name.toLowerCase().endsWith(".pptx"));
                const unitLabel = isPptx ? "Slide" : "Page";
                
                const sName = src.source_name || "";
                const fileNumPrefix = src.file_number && !sName.toLowerCase().startsWith("file ")
                  ? `File ${src.file_number} — `
                  : "";

                const lineDisplay = src.line_start
                  ? src.line_start === src.line_end || !src.line_end
                    ? `Line: ${src.line_start}`
                    : `Lines: ${src.line_start}–${src.line_end}`
                  : null;

                return (
                  <div
                    key={idx}
                    className="bg-[#1C2843] border border-[#2B3C63] rounded-lg p-3 text-xs text-slate-200 space-y-1 shadow-sm"
                  >
                    <div className="font-semibold text-blue-400 flex items-center gap-1.5">
                      <span>📄</span>
                      <span>
                        {fileNumPrefix}
                        {sName}
                      </span>
                    </div>

                    {src.page_number && (
                      <div className="text-slate-300 font-medium">
                        {unitLabel}: {src.page_number}
                      </div>
                    )}

                    {lineDisplay && (
                      <div className="text-slate-300 font-medium">
                        {lineDisplay}
                      </div>
                    )}

                    {src.original_text && (
                      <div className="mt-2 pt-2 border-t border-[#2B3C63]/60 text-slate-300 italic font-mono text-[11px] leading-snug">
                        Exact Quote: "{src.original_text}"
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default MessageBubble;