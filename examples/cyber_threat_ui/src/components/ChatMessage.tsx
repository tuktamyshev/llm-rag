import type { ChatEntry } from "../utils/types";

type Props = {
  message: ChatEntry;
};

export function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-3xl rounded-2xl px-4 py-3 ${isUser ? "bg-cyan-600 text-slate-950" : "bg-cyber-card"}`}>
        <p className="whitespace-pre-wrap text-sm">{message.text}</p>
        {!isUser && message.sources && message.sources.length > 0 ? (
          <div className="mt-3 border-t border-slate-700/60 pt-2 text-xs text-cyan-200">
            <p className="mb-1 uppercase tracking-wide">Sources</p>
            <ul className="list-disc pl-5">
              {message.sources.map((source, index) => (
                <li key={`${source}-${index}`}>{source}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}
