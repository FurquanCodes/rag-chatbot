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
                const isWiki =
                  src.source_type === "wikipedia" ||
                  Boolean(src.wikipedia_url) ||
                  (src.source_name &&
                    src.source_name.toLowerCase().includes("wikipedia"));

                if (isWiki) {
                  const wikiTitle = (src.source_name || "").replace(/^Wikipedia\s*-\s*/i, "").trim();
                  const wikiUrl =
                    src.wikipedia_url ||
                    `https://en.wikipedia.org/wiki/${encodeURIComponent(wikiTitle)}`;

                  return (
                    <a
                      key={idx}
                      href={wikiUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block bg-[#1C2843] border border-[#2B3C63] hover:border-blue-500 rounded-lg p-3 text-xs text-slate-200 space-y-1 shadow-sm transition-all cursor-pointer group"
                    >
                      <div className="font-semibold text-blue-400 group-hover:text-blue-300 flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <span>🌐</span>
                          <span>{src.source_name}</span>
                        </div>
                        <span className="text-[10px] text-blue-400 group-hover:translate-x-0.5 transition-transform">↗</span>
                      </div>

                      {(src.evidence_snippet || src.original_text) && (
                        <div className="text-slate-300 text-[11px] leading-snug mt-1 line-clamp-2">
                          {src.evidence_snippet || src.original_text}
                        </div>
                      )}
                    </a>
                  );
                }

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