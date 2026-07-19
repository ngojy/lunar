import { useEffect, useRef } from "react"
import { ChatMessage } from "../types"


// props: data passes into a component from its parent
interface Props {
    messages: ChatMessage[]
    isLoading: boolean
}


// helper function: converts an ISO timestamp into (ex: 08:30)
function formatTime(iso: string) {
    return new Date(iso).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
    })
}


// message.map(): loops over every message and renders a pair of bubbles (user+Lunar)
// key={msg.id}: React needs a unique key on each item in a list to track changes efficiently
// ref={bottomref}: an invisible div at the bottom. useEffect scrolls to it every time messages updates so the chat always shows the latest message
// {isLoading && (...)}: only renders the loading dots when isLoading is true
export default function ChatPanel({ messages, isLoading }: Props) {
    const bottomRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages, isLoading])

    return (
        <div className="chat-panel">
            <div className="panel-label">Chat</div>

            <div className="chat-messages">
                {messages.length === 0 && (
                    <div className="empty-state">
                        <span>^_^</span>
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
                                Lunar
                                <span className="message-time">
                                    {formatTime(msg.timestamp)} . {msg.duration_seconds}s
                                </span>
                            </div>
                            <div className="message-bubble nova-bubble">
                                {msg.answer.split("\n").map((line, i) => (
                                    <p key={i}>{line}</p>
                                ))}
                            </div>
                        </div>
                    </div>
                ))}
                
                {isLoading && (
                    <div className="message nova">
                        <div className="message-label">Lunar</div>
                        <div className="message-bubble nova-bubble loading-bubble">
                            <span className="dot" />
                            <span className="dot" />
                            <span className="dot" />
                        </div>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>
        </div>
    )
}