import { useState, useEffect, useRef } from "react"
import ChatPanel from "./components/ChatPanel"
import ActivityPanel from "./components/ActivityPanel"
import HistoryPanel from "./components/HistoryPanel"
import type { ChatMessage, AgentStep } from "./types"
import { sendMessage, getHistory, clearHistory, checkHealth } from "./api"
import "./App.css"

export default function App() {
    const [messages, setMessages]         = useState<ChatMessage[]>([]) // messages: all chat messages shown in ChatPanel
    const [history, setHistory]           = useState<ChatMessage[]>([]) // history: past conversations shown in HistoryPanel
    const [liveSteps, setLiveSteps]       = useState<AgentStep[]>([]) // liveSteps: agent steps shown in ActivityPanel
    const [currentAgent, setCurrentAgent] = useState<string>("") // currentAgent: shows which agent is running right now
    const [isLoading, setIsLoading]       = useState(false) // isLoading: shows whether the system is processing
    const [input, setInput]               = useState("") // input: text in the input box
    const [status, setStatus]             = useState<"online" | "offline" | "checking">("checking") // status: shows whether the backend is online
    const inputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
        checkHealth().then((ok) => setStatus(ok ? "online" : "offline"))
        getHistory().then(setHistory)
    }, [])

    async function handleSend() {
        if (!input.trim() || isLoading) return

        const task = input.trim()
        setInput("")
        setIsLoading(true)
        setLiveSteps([])
        setCurrentAgent("orchestrator")

        try{
            const response = await sendMessage(task)
            setMessages((prev) => [...prev, response]) // prev => [...prev, response]: safe way to update arrays in React state, never mutate state directly
            setHistory((prev) => [...prev, response])
            setLiveSteps(response.steps)
            setCurrentAgent("")
        } catch (err) {
            console.error(err)
            setCurrentAgent("")
        } finally {
        setIsLoading(false)
        inputRef.current?.focus()
        }
    }

    async function handleClearHistory() {
        await clearHistory()
        setHistory([])
    }

    function handleSelectHistory(msg: ChatMessage) {
        setMessages((prev) => {
            const exists = prev.find((m) => m.id === msg.id)
            if (exists) return prev
            return [...prev, msg]
        })
        setLiveSteps(msg.steps)
    }


    const statusColour =
        status === "online" ? "#69f0ae" :
        status === "offline" ? "#ff5252" : "#ffd740"

    const statusText =
        status === "online" ? "● Online" :
        status === "offline" ? "● Offline" : "● Connecting..."

    return (
        <div className="app">
            <header className="titlebar">
                <div className="titlebar-left">
                    <span className="logo">🌙</span>
                    <span className="app-name">Lunar</span>
                    <span className="app-subtitle">Multi-Agent System</span>
                </div>
                <div className="titlebar-right">
                    <span style={{ color: statusColour }}>{statusText}</span>
                </div>
            </header>

            <div className="layout">
                <div className="left-col">
                    <ChatPanel messages={messages} isLoading={isLoading} />
                    <div className="input-row">
                        <input
                            ref={inputRef}
                            className="chat-input"
                            placeholder="Ask Lunar anything..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleSend()}
                            disabled={isLoading}
                        />
                        <button
                            className="send-btn"
                            onClick={handleSend}
                            disabled={isLoading || !input.trim()}
                        >
                            {isLoading ? "..." : "Send"}
                        </button>
                    </div>
                </div>

                <div className="right-col">
                    <ActivityPanel
                        steps={liveSteps}
                        isLoading={isLoading}
                        currentAgent={currentAgent}
                    />
                    <HistoryPanel
                        history={history}
                        onSelect={handleSelectHistory}
                        onClear={handleClearHistory}
                    />
                </div>
            </div>
        </div>
    )
}