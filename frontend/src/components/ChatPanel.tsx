import { useEffect, useRef, useState } from "react"
import type { ChatMessage } from "../types"
import { parseMarkdown, renderMarkdown } from "../utils/markdownRenderer"


// props: data passes into a component from its parent
interface Props {
    messages: ChatMessage[]
    isLoading: boolean
    pendingMessage: string
    currentAgent?: string
}


// helper function: converts an ISO timestamp into (ex: 08:30)
function formatTime(iso: string) {
    return new Date(iso).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
    })
}

function formatModeLabel(mode?: "chat" | "agent") {
    if (mode === "agent") return "Agent"
    return "Chat"
}

// message.map(): loops over every message and renders a pair of bubbles (user+Lunar)
// key={msg.id}: React needs a unique key on each item in a list to track changes efficiently
// ref={bottomref}: an invisible div at the bottom. useEffect scrolls to it every time messages updates so the chat always shows the latest message
// {isLoading && (...)}: shows loading indicator in the message bubble when waiting for response
export default function ChatPanel({ messages, isLoading, pendingMessage, currentAgent }: Props) {
    const bottomRef = useRef<HTMLDivElement>(null)
    const [elapsed, setElapsed] = useState(0)
    const [expandedDocMessageId, setExpandedDocMessageId] = useState<string | null>(null)

    function formatTokenRate(msg: ChatMessage) {
        if (!msg.duration_seconds || msg.duration_seconds <= 0) {
            return "tok/s unavailable"
        }

        const totalTokens = msg.token_usage?.total_tokens ?? Math.max(1, Math.round((msg.task.length + msg.answer.length) / 4))
        const rate = totalTokens / msg.duration_seconds
        return `${rate.toFixed(1)} tok/s`
    }

    async function handleCopy(text: string) {
        try {
            await navigator.clipboard.writeText(text)
        } catch (err) {
            console.warn("Clipboard copy failed", err)
        }
    }

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages, isLoading, pendingMessage])

    useEffect(() => {
        if (!isLoading) {
            setElapsed(0)
            return
        }

        const start = Date.now()
        const interval = setInterval(() => {
            setElapsed(((Date.now() - start) / 1000))
        }, 100)
        return () => clearInterval(interval)
    }, [isLoading])

    return (
        <div className="chat-panel">
            <div className="panel-label">Chat</div>

            <div className="chat-messages">
                {messages.length === 0 && !isLoading && (
                    <div className="empty-state">
                        <span>🌙</span>
                        <p>Ask Lunar anything. The multi-agent system will research, reason, and respond.</p>
                    </div>
                )}

                {messages.map((msg, index) => {
                    const isCurrentMessage = index === messages.length - 1 && isLoading && msg.answer === ""
                    const agentLabel = currentAgent 
                        ? `${currentAgent.charAt(0).toUpperCase() + currentAgent.slice(1)} is analyzing...`
                        : "Processing..."

                    return (
                    <div key={msg.id} className="message-group">
                        <div className="message you">
                            <div className="message-label">
                                You <span className="message-time">{formatTime(msg.timestamp)}</span>
                            </div>
                            <div className="message-bubble you-bubble">{msg.task}</div>
                        </div>

                        <div className="message nova">
                            <div className="message-label">
                                {msg.model_used || "Model"}
                                <span className={`message-mode-badge ${msg.execution_mode === "agent" ? "agent" : "chat"}`}>
                                    {formatModeLabel(msg.execution_mode)}
                                </span>
                                <span className="message-time">
                                    {formatTime(msg.timestamp)} · {msg.duration_seconds}s
                                </span>
                            </div>
                            <div className="nova-message-content">
                                <div className="message-bubble nova-bubble">
                                    {isCurrentMessage ? (
                                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                            <span className="loading-text">{agentLabel}</span>
                                            <span className="loading-timer">{elapsed.toFixed(1)}s</span>
                                        </div>
                                    ) : (
                                        <div className="markdown-content">
                                            {renderMarkdown(parseMarkdown(msg.answer))}
                                        </div>
                                    )}
                                </div>
                                {!isCurrentMessage && (
                                    <div className="message-meta-row">
                                        <span className="message-token-usage">
                                            {formatTokenRate(msg)}
                                        </span>
                                        {msg.retrieved_documents && msg.retrieved_documents.length > 0 && (
                                            <button
                                                type="button"
                                                className="message-docs-btn"
                                                onClick={() => setExpandedDocMessageId(expandedDocMessageId === msg.id ? null : msg.id)}
                                                title={`${msg.retrieved_documents.length} document(s) used`}
                                                aria-label={`Show ${msg.retrieved_documents.length} document(s)`}
                                            >
                                                📚 {msg.retrieved_documents.length}
                                            </button>
                                        )}
                                        <button
                                            type="button"
                                            className="message-copy-btn"
                                            onClick={() => handleCopy(msg.answer)}
                                            title="Copy response"
                                            aria-label="Copy response"
                                        >
                                            ⧉
                                        </button>
                                    </div>
                                )}
                                {expandedDocMessageId === msg.id && msg.retrieved_documents && msg.retrieved_documents.length > 0 && (
                                    <div className="message-docs-list">
                                        <div className="message-docs-header">📚 Retrieved Documents</div>
                                        {msg.retrieved_documents.map((doc) => (
                                            <div key={`${msg.id}-doc-${doc.doc_id}`} className="message-doc-item">
                                                <div className="message-doc-name">{doc.filename}</div>
                                                <div className="message-doc-meta">
                                                    <span className="message-doc-score">Score: {(doc.relevance_score * 100).toFixed(1)}%</span>
                                                    {doc.chunk_count && <span className="message-doc-chunks">{doc.chunk_count} chunk(s)</span>}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                    )
                })}

                <div ref={bottomRef} />
            </div>
        </div>
    )
}