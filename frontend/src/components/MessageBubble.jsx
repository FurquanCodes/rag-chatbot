import { useState } from "react";

function MessageBubble({ role, text, source, sources, retrievalDetails, isError }) {
  const isUser = role === "user";
  const [expandedSourceIndex, setExpandedSourceIndex] = useState(null);

  function toggleSource(index) {
    setExpandedSourceIndex((prev) => (prev === index ? null : index));
  }

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[82%] p-4 rounded-xl shadow-md ${
          isUser
            ? "bg-blue-600 text-white rounded-br-none"
            : isError
            ? "bg-red-950/80 border border-red-800 text-red-200 rounded-bl-none"
            : "bg-gray-800 border border-gray-700 text-gray-100 rounded-bl-none"
        }`}
      >
        <div className="whitespace-pre-wrap leading-relaxed text-sm">{text}</div>

        {!isUser && !isError && retrievalDetails && (
          <div className="mt-2 text-[11px] text-gray-400 flex items-center gap-2 border-t border-gray-700/60 pt-2">
            <span>
              Search Strategy:{" "}
              <span className="text-gray-300 font-medium capitalize">
                {retrievalDetails.retrieval_strategy?.replace("_", " ")}
              </span>
            </span>
            {retrievalDetails.search_time_ms > 0 && (
              <span>• {Math.round(retrievalDetails.search_time_ms)}ms</span>
            )}
            {retrievalDetails.chunks_retrieved > 0 && (
              <span>• {retrievalDetails.chunks_retrieved} chunks retrieved</span>
            )}
          </div>
        )}

        {!isUser && !isError && sources && sources.length > 0 && (
          <div className="mt-3 pt-2 border-t border-gray-700/60">
            <span className="text-xs font-semibold text-gray-400 block mb-1.5">
              Sources & Evidence ({sources.length}):
            </span>
            <div className="flex flex-wrap gap-1.5">
              {sources.map((s, idx) => {
                const isExpanded = expandedSourceIndex === idx;
                const isWiki = s.source_type === "wikipedia";
                const scorePercent = s.relevance_score
                  ? Math.round(s.relevance_score * 100)
                  : null;

                return (
                  <div key={idx} className="w-full">
                    <button
                      onClick={() => toggleSource(idx)}
                      className={`text-left text-xs px-2.5 py-1 rounded-md flex items-center justify-between gap-2 w-full transition-colors ${
                        isExpanded
                          ? "bg-gray-700 text-white border border-gray-600"
                          : "bg-gray-750 text-gray-300 hover:bg-gray-700 border border-gray-700/80"
                      }`}
                    >
                      <div className="flex items-center gap-1.5 truncate">
                        <span className="text-xs">{isWiki ? "🌐" : "📄"}</span>
                        <span className="font-medium truncate">{s.source_name}</span>
                        {s.page_number && (
                          <span className="text-[10px] bg-gray-900/60 px-1.5 py-0.5 rounded text-gray-400">
                            p. {s.page_number}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {scorePercent !== null && (
                          <span
                            className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                              scorePercent >= 80
                                ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                : scorePercent >= 60
                                ? "bg-amber-950 text-amber-300 border border-amber-800"
                                : "bg-gray-900 text-gray-400 border border-gray-700"
                            }`}
                          >
                            {scorePercent}% match
                          </span>
                        )}
                        <span className="text-gray-400">{isExpanded ? "▲" : "▼"}</span>
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="mt-1 p-2.5 bg-gray-900/90 border border-gray-700 rounded-md text-xs text-gray-300 space-y-1">
                        {s.section_heading && (
                          <div className="font-semibold text-blue-400 text-[11px]">
                            Section: {s.section_heading}
                          </div>
                        )}
                        <div className="italic text-gray-300 bg-gray-950/70 p-2 rounded border border-gray-800 font-mono text-[11px]">
                          "{s.evidence_snippet}"
                        </div>
                        {isWiki && s.wikipedia_url && (
                          <a
                            href={s.wikipedia_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-blue-400 hover:underline text-[11px] pt-1"
                          >
                            View on Wikipedia ↗
                          </a>
                        )}
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