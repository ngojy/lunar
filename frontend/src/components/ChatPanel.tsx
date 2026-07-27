import { useEffect, useRef, useState } from "react"
import type { ChatMessage } from "../types"


// props: data passes into a component from its parent
interface Props {
    messages: ChatMessage[]
    isLoading: boolean
    pendingMessage: string
    selectedModel: string
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

function LoadingIndicator({ selectedModel }: { selectedModel: string }) {
    const [elapsed, setElapsed] = useState(0)

    useEffect(() => {
        const start = Date.now()
        const interval = setInterval(() => {
            setElapsed(((Date.now() - start) / 1000))
        }, 100)
        return () => clearInterval(interval)
    }, [])

    return (
        <div className="message nova">
            <div className="message-label">{selectedModel || "Model"}</div>
            <div className="message-bubble nova-bubble loading-bubble">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
                <span className="loading-timer">{elapsed.toFixed(1)}s</span>
            </div>
        </div>
    )
}

// message.map(): loops over every message and renders a pair of bubbles (user+Lunar)
// key={msg.id}: React needs a unique key on each item in a list to track changes efficiently
// ref={bottomref}: an invisible div at the bottom. useEffect scrolls to it every time messages updates so the chat always shows the latest message
// {isLoading && (...)}: only renders the loading dots when isLoading is true
export default function ChatPanel({ messages, isLoading, pendingMessage, selectedModel }: Props) {
    const bottomRef = useRef<HTMLDivElement>(null)

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

                {messages.map((msg) => (
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
                                    {msg.answer.split("\n").map((line, i) => (
                                        <p key={i}>{line}</p>
                                    ))}
                                </div>
                                <div className="message-meta-row">
                                    <span className="message-token-usage">
                                        {formatTokenRate(msg)}
                                    </span>
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
                            </div>
                        </div>
                    </div>
                ))}

                {/* Show pending user message while loading */}
                {isLoading && pendingMessage && (
                    <div className="message-group">
                        <div className="message you">
                            <div className="message-label">You</div>
                            <div className="message-bubble you-bubble">
                                {pendingMessage}
                            </div>
                        </div>
                        <LoadingIndicator selectedModel={selectedModel} />
                    </div>
                )}

                <div ref={bottomRef} />
            </div>
        </div>
    )
}