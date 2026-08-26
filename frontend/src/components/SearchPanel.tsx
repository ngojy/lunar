import { useState } from "react"
import type { Chat } from "../types"

interface SearchResult {
    chatId: string
    chatTitle: string
    messageId: string
    task: string
    answer: string
    timestamp: string
    matchType: "task" | "answer"
}

interface Props {
    chats: Chat[]
    onSelectChat: (id: string) => void
}


function searchChats(chats: Chat[], query: string): SearchResult[] {
  if (!query.trim()) return []

  const q = query.toLowerCase()
  const results: SearchResult[] = []

  for (const chat of chats) {
    for (const msg of chat.messages) {
      const taskMatch   = msg.task.toLowerCase().includes(q)
      const answerMatch = msg.answer.toLowerCase().includes(q)

      if (taskMatch) {
        results.push({
          chatId:    chat.id,
          chatTitle: chat.title,
          messageId: msg.id,
          task:      msg.task,
          answer:    msg.answer,
          timestamp: msg.timestamp,
          matchType: "task",
        })
      } else if (answerMatch) {
        results.push({
          chatId:    chat.id,
          chatTitle: chat.title,
          messageId: msg.id,
          task:      msg.task,
          answer:    msg.answer,
          timestamp: msg.timestamp,
          matchType: "answer",
        })
      }
    }
  }

  return results
}

function highlight(text: string, query: string): string {
  if (!query.trim()) return text
  const index = text.toLowerCase().indexOf(query.toLowerCase())
  if (index === -1) return text
  const start  = Math.max(0, index - 40)
  const end    = Math.min(text.length, index + query.length + 40)
  const slice  = (start > 0 ? "…" : "") + text.slice(start, end) + (end < text.length ? "…" : "")
  return slice
}


export default function SearchPanel({ chats, onSelectChat }: Props) {
    const [query, setQuery]     = useState("")
    const results               = searchChats(chats, query)

    function formatTime(iso: string) {
        return new Date(iso).toLocaleDateString([], {
            month: "short", day: "numeric",
        })
    } 

    return (
        <div className="side-panel">
            <div className="side-panel-header">
                <span>🔍︎</span> Search Chats
            </div>

            <div className="search-input-wrap">
                <input
                    className="search-input"
                    placeholder="Search your chats..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    autoFocus
                />
                {query && (
                    <button className="search-clear" onClick={() => setQuery("")}>✕</button>
                )}
            </div>

            <div className="search-results">
                {query && results.length === 0 && (
                    <div className="side-panel-empty">No results for "{query}"</div>
                )}

                {!query && (
                    <div className="side-panel-empty">Type to search your chat history</div>
                )}

                {results.map((r, i) => (
                    <button
                        key={i}
                        className="search-result-item"
                        onClick={() => onSelectChat(r.chatId)}
                    >
                        <div className="search-result-chat">{r.chatTitle}</div>
                        <div className="search-result-task">{r.task}</div>
                        <div className="search-result-preview">
                            {highlight(r.matchType === "task" ? r.task : r.answer, query)}
                        </div>
                        <div className="search-result-meta">
                            {r.matchType === "task" ? "Question" : "Answer"} · {formatTime(r.timestamp)}
                        </div>
                    </button>
                ))}
            </div>
        </div>
    )
}