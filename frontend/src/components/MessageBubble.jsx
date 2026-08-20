import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function MessageBubble({ role, text, sources }) {
  const isUser = role === "user";
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy text:", err);
    }
  }

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4 group`}>
      <div
        className={`relative max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 shadow-md leading-relaxed text-sm ${
          isUser
            ? "bg-[#2563EB] text-white rounded-br-none"
            : "bg-[#131B2E] border border-[#22304E] text-slate-200 rounded-bl-none"
        }`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {isUser ? (
              <div className="whitespace-pre-wrap">{text}</div>
            ) : (
              <div className="prose prose-invert max-w-none text-sm leading-relaxed text-slate-200 overflow-x-auto">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    table: ({ node, ...props }) => (
                      <div className="my-3 overflow-x-auto rounded-lg border border-[#2B3C63]">
                        <table className="w-full text-left text-xs border-collapse" {...props} />
                      </div>
                    ),
                    thead: ({ node, ...props }) => (
                      <thead className="bg-[#1C2843] text-blue-300 font-semibold border-b border-[#2B3C63]" {...props} />
                    ),
                    th: ({ node, ...props }) => (
                      <th className="p-2.5 border-r border-[#2B3C63] last:border-r-0" {...props} />
                    ),
                    td: ({ node, ...props }) => (
                      <td className="p-2.5 border-t border-r border-[#2B3C63] last:border-r-0 text-slate-300" {...props} />
                    ),
                    code: ({ node, inline, className, children, ...props }) => {
                      return (
                        <code
                          className="bg-[#1C2843] text-pink-400 px-1.5 py-0.5 rounded font-mono text-xs"
                          {...props}
                        >
                          {children}
                        </code>
                      );
                    },
                  }}
                >
                  {text}
                </ReactMarkdown>
              </div>
            )}
          </div>

          <button
            onClick={handleCopy}
            title={copied ? "Copied!" : "Copy message text"}
            className={`shrink-0 flex items-center gap-1 text-xs px-2 py-1 rounded-md transition-all border ${
              copied
                ? "bg-emerald-600/30 text-emerald-400 border-emerald-500/50"
                : isUser
                ? "bg-blue-700/60 hover:bg-blue-700 text-blue-100 border-blue-400/40 opacity-70 group-hover:opacity-100"
                : "bg-[#1C2843] hover:bg-[#253659] text-slate-300 border-[#2B3C63] opacity-70 group-hover:opacity-100"
            }`}
          >
            {copied ? (
              <>
                <span>✓</span>
                <span>Copied</span>
              </>
            ) : (
              <>
                <span>📋</span>
                <span>Copy</span>
              </>
            )}
          </button>
        </div>

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
                        {fileNumPrefix}{sName}
                      </span>
                    </div>

                    {src.page_number && (
                      <div className="text-slate-300 font-medium flex items-center gap-1.5 mt-1">
                        <span>📑</span>
                        <span>{unitLabel}: {src.page_number}</span>
                      </div>
                    )}

                    {lineDisplay && (
                      <div className="text-slate-300 font-medium flex items-center gap-1.5 mt-1">
                        <span>🔢</span>
                        <span>{lineDisplay}</span>
                      </div>
                    )}

                    {src.original_text && (
                      <div className="mt-2 pt-2 border-t border-[#2B3C63]/60 text-slate-300 italic text-[12px] leading-relaxed border-l-2 border-l-blue-500 pl-2">
                        Exact Source Text:
                        <br/>
                        "{src.original_text}"
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