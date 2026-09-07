import { useState, useEffect, useRef } from "react"
import ChatPanel from "./components/ChatPanel"
import AgentPanel from "./components/AgentPanel"
import Sidebar from "./components/Sidebar"
import SearchPanel from "./components/SearchPanel"
import ChatsPage from "./components/ChatsPage"
import ToolsPanel from "./components/ToolsPanel"
import type { AgentStep, Chat, ToolSettings, ChatMessage } from "./types"
import { sendMessageStream, checkHealth, listAvailableModels, getSessionHistory, listSessions, deleteChat } from "./api"
import { 
    loadAgentModels, 
    saveAgentModels, 
    loadConversationModel, 
    saveConversationModel,
    loadModelDetectionTimes,
    saveModelDetectionTimes
} from "./modelSettings"
import "./App.css"

type Page = "welcome" | "chat" | "search" | "chats" | "tools"

type ChatComposerProps = {
    value: string
    onChange: (value: string) => void
    onSubmit: () => void
    inputRefElement: React.RefObject<HTMLInputElement | null>
    placeholder: string
    disabled: boolean
    selectedModel: string
    availableModels: string[]
    onSelectModel: (model: string) => void
    composerMode: "chat" | "agent"
    onModeChange: (mode: "chat" | "agent") => void
    settings: ToolSettings
    detectedModelTimes: Record<string, string>
    onRefreshModels: () => Promise<void>
}

const RECENT_DETECTION_WINDOW_MS = 3 * 24 * 60 * 60 * 1000

function generateId() {
    return Math.random().toString(36).slice(2, 10)
}

function generateTitle(task: string) {
    return task.length > 40 ? task.slice(0, 40) + "…" : task
}

const DEFAULT_SETTINGS: ToolSettings = {
    model: "",
    temperature: 0,
    agentModelSettings: {},
    conversationModel: undefined,
    autoCritique: true,
    showAgentActivity: true,
    userName: "",
    agentMemorySettings: {
        enabled: true,
        autoStore: true,
        autoRetrieve: true,
    },
    ragSettings: {
        enabled: true,
        include_web: true,
        include_files: true,
        include_db: false,
        file_roots: "",
        file_extensions: ".txt,.md,.json,.csv,.py,.ts,.tsx,.js,.jsx,.pdf,.docx",
        embedding_model: "nomic-embed-text",
        top_k: 5,
        max_files: 200,
        chunk_chars: 900,
        chunk_overlap: 120,
        db_type: "sqlite",
        db_connection: "",
        db_table: "",
        db_text_columns: "content,text,body,description",
    },
}

function getModelDeveloper(modelName: string): string {
    const normalized = modelName.toLowerCase()

    if (normalized.startsWith("gpt-") || normalized.startsWith("o1") || normalized.startsWith("o3") || normalized.startsWith("o4") || normalized.startsWith("o5") || normalized.startsWith("openai")) {
        return "OpenAI"
    }
    if (normalized.includes("claude") || normalized.includes("anthropic")) return "Anthropic"
    if (normalized.includes("gemini") || normalized.includes("gemma") || normalized.includes("google")) return "Google"
    if (normalized.includes("qwen")) return "Alibaba"
    if (normalized.includes("deepseek")) return "DeepSeek"
    if (normalized.includes("llama") || normalized.includes("meta")) return "Meta"
    if (normalized.includes("mistral")) return "Mistral"
    if (normalized.includes("phi")) return "Microsoft"
    if (normalized.includes("command")) return "Cohere"
    if (normalized.includes("yi")) return "01.AI"
    if (normalized.includes("mixtral")) return "Mistral"

    return "Local / Ollama"
}

function getModelMode(modelName: string, settings: ToolSettings): string {
    const chatModel = settings.conversationModel || settings.model
    const agentModels = Object.values(settings.agentModelSettings || {}).filter(Boolean)
    const isChat = chatModel === modelName
    const isAgent = agentModels.includes(modelName)

    if (isChat && isAgent) return "Chat + Agent"
    if (isChat) return "Chat"
    if (isAgent) return "Agent"
    return "Available"
}

function getModelSize(modelName: string): string | null {
    // Match common Ollama-style size tags like 7b, 13b, 405b, 1.5b, 512m.
    const match = modelName.toLowerCase().match(/(?:^|[^\d])(\d+(?:\.\d+)?)(m|b)(?=$|[^a-z0-9])/i)
    if (!match) return null
    return `${match[1]}${match[2].toUpperCase()}`
}

function truncateMiddle(text: string, maxChars: number): string {
    if (text.length <= maxChars) return text
    const front = Math.max(4, Math.floor((maxChars - 1) / 2))
    const back = Math.max(4, maxChars - 1 - front)
    return `${text.slice(0, front)}...${text.slice(-back)}`
}

function isRecentlyDetected(modelName: string, detectedModelTimes: Record<string, string>): boolean {
    const detectedAt = detectedModelTimes[modelName]
    if (!detectedAt) return false

    const detectedAtMs = new Date(detectedAt).getTime()
    if (Number.isNaN(detectedAtMs)) return false

    return Date.now() - detectedAtMs <= RECENT_DETECTION_WINDOW_MS
}

function highlightMatch(text: string, query: string) {
    const trimmed = query.trim()
    if (!trimmed) return text

    const lower = text.toLowerCase()
    const target = trimmed.toLowerCase()
    const index = lower.indexOf(target)

    if (index === -1) return text

    const before = text.slice(0, index)
    const match = text.slice(index, index + trimmed.length)
    const after = text.slice(index + trimmed.length)

    return (
        <>
            {before}
            <mark className="composer-model-highlight">{match}</mark>
            {after}
        </>
    )
}

function ChatComposer({
    value,
    onChange,
    onSubmit,
    inputRefElement,
    placeholder,
    disabled,
    selectedModel,
    availableModels,
    onSelectModel,
    composerMode,
    onModeChange,
    settings,
    detectedModelTimes,
    onRefreshModels,
}: ChatComposerProps) {
    const [modelMenuOpen, setModelMenuOpen] = useState(false)
    const [modelSearch, setModelSearch] = useState("")
    const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
    const [isRefreshingModels, setIsRefreshingModels] = useState(false)
    const modelMenuRef = useRef<HTMLDivElement>(null)
    const uploadInputRef = useRef<HTMLInputElement>(null)

    async function handleRefreshModels() {
        setIsRefreshingModels(true)
        try {
            await onRefreshModels()
        } finally {
            setIsRefreshingModels(false)
        }
    }

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (modelMenuRef.current && !modelMenuRef.current.contains(event.target as Node)) {
                setModelMenuOpen(false)
            }
        }

        document.addEventListener("mousedown", handleClickOutside)
        return () => document.removeEventListener("mousedown", handleClickOutside)
    }, [])

    const filteredModels = availableModels.filter((model) => {
        const query = modelSearch.trim().toLowerCase()
        if (!query) return true
        return (
            model.toLowerCase().includes(query) ||
            getModelDeveloper(model).toLowerCase().includes(query) ||
            getModelMode(model, settings).toLowerCase().includes(query) ||
            (getModelSize(model) || "").toLowerCase().includes(query)
        )
    })

    const recentFiltered = filteredModels
        .filter((model) => isRecentlyDetected(model, detectedModelTimes))
        .sort((a, b) => {
            const aMs = new Date(detectedModelTimes[a] || 0).getTime()
            const bMs = new Date(detectedModelTimes[b] || 0).getTime()
            return bMs - aMs
        })

    const allFiltered = filteredModels
        .filter((model) => !isRecentlyDetected(model, detectedModelTimes))
        .sort((a, b) => a.localeCompare(b))

    function handleSelect(model: string) {
        onSelectModel(model)
        setModelMenuOpen(false)
        setModelSearch("")
    }

    function handleUploadFiles(event: React.ChangeEvent<HTMLInputElement>) {
        const fileList = Array.from(event.target.files || [])
        if (!fileList.length) return
        setUploadedFiles((prev) => [...prev, ...fileList])
        event.target.value = ""
    }

    function removeUploadedFile(index: number) {
        setUploadedFiles((prev) => prev.filter((_, i) => i !== index))
    }

    const selectedModelSize = selectedModel ? getModelSize(selectedModel) : null
    const selectedModelLabel = selectedModel
        ? truncateMiddle(selectedModel, selectedModelSize ? 16 : 22)
        : "Select Model"
    const selectedModelTitle = selectedModel
        ? (selectedModelSize ? `${selectedModel} (${selectedModelSize})` : selectedModel)
        : "Select Model"

    return (
        <div className="composer-shell">
            <div className="composer-input-row">
                <input
                    ref={inputRefElement}
                    className="chat-input composer-input"
                    placeholder={placeholder}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && selectedModel && onSubmit()}
                    disabled={disabled}
                />
            </div>

            <div className="composer-controls-row">
                <div className="composer-mode-segmented" role="group" aria-label="Composer mode">
                    <button
                        type="button"
                        className={`composer-mode-segment ${composerMode === "chat" ? "active" : ""}`}
                        onClick={() => onModeChange("chat")}
                        aria-pressed={composerMode === "chat"}
                        title="Chat mode"
                    >
                        Chat
                    </button>
                    <button
                        type="button"
                        className={`composer-mode-segment ${composerMode === "agent" ? "active" : ""}`}
                        onClick={() => onModeChange("agent")}
                        aria-pressed={composerMode === "agent"}
                        title="Agent mode"
                    >
                        Agent
                    </button>
                </div>

                <div className="composer-actions-wrap">
                    <div className="composer-model-wrap" ref={modelMenuRef}>
                        <button
                            type="button"
                            className="composer-model-select"
                            onClick={() => setModelMenuOpen((prev) => !prev)}
                            title={selectedModelTitle}
                        >
                            <span className="composer-model-select-text">
                                {selectedModelLabel}
                            </span>
                            {selectedModelSize && (
                                <span className="composer-model-select-size">{selectedModelSize}</span>
                            )}
                            <span className="composer-model-caret">▾</span>
                        </button>

                        {modelMenuOpen && (
                            <div className="composer-model-popover">
                                <div className="composer-model-popover-header">
                                    <input
                                        className="composer-model-search"
                                        placeholder="Search models..."
                                        value={modelSearch}
                                        onChange={(e) => setModelSearch(e.target.value)}
                                        disabled={isRefreshingModels}
                                    />
                                    <button
                                        type="button"
                                        className="composer-model-refresh-btn"
                                        onClick={handleRefreshModels}
                                        disabled={isRefreshingModels}
                                        title="Refresh model list"
                                        aria-label="Refresh model list"
                                    >
                                        {isRefreshingModels ? "↻" : "↻"}
                                    </button>
                                </div>

                                <div className="composer-model-list">
                                    {recentFiltered.length > 0 && (
                                        <div className="composer-model-group">
                                            <div className="composer-model-group-title">Recent</div>
                                            {recentFiltered.map((model) => (
                                                (() => {
                                                    const modelSize = getModelSize(model)
                                                    return (
                                                        <button
                                                            key={`recent-${model}`}
                                                            type="button"
                                                            className={`composer-model-item ${model === selectedModel ? "active" : ""}`}
                                                            onClick={() => handleSelect(model)}
                                                        >
                                                            <div className="composer-model-item-main">
                                                                <span className="composer-model-item-name">{highlightMatch(model, modelSearch)}</span>
                                                                <span className="composer-model-item-developer">{highlightMatch(getModelDeveloper(model), modelSearch)}</span>
                                                            </div>
                                                            <div className="composer-model-item-meta">
                                                                <span className="composer-model-item-mode">{highlightMatch(getModelMode(model, settings), modelSearch)}</span>
                                                                {modelSize && <span className="composer-model-item-size">{highlightMatch(modelSize, modelSearch)}</span>}
                                                            </div>
                                                        </button>
                                                    )
                                                })()
                                            ))}
                                        </div>
                                    )}

                                    {allFiltered.length > 0 && (
                                        <div className="composer-model-group">
                                            <div className="composer-model-group-title">All Models</div>
                                            {allFiltered.map((model) => (
                                                (() => {
                                                    const modelSize = getModelSize(model)
                                                    return (
                                                        <button
                                                            key={model}
                                                            type="button"
                                                            className={`composer-model-item ${model === selectedModel ? "active" : ""}`}
                                                            onClick={() => handleSelect(model)}
                                                        >
                                                            <div className="composer-model-item-main">
                                                                <span className="composer-model-item-name">{highlightMatch(model, modelSearch)}</span>
                                                                <span className="composer-model-item-developer">{highlightMatch(getModelDeveloper(model), modelSearch)}</span>
                                                            </div>
                                                            <div className="composer-model-item-meta">
                                                                <span className="composer-model-item-mode">{highlightMatch(getModelMode(model, settings), modelSearch)}</span>
                                                                {modelSize && <span className="composer-model-item-size">{highlightMatch(modelSize, modelSearch)}</span>}
                                                            </div>
                                                        </button>
                                                    )
                                                })()
                                            ))}
                                        </div>
                                    )}

                                    {recentFiltered.length === 0 && allFiltered.length === 0 && (
                                        <div className="composer-model-empty">No models match your search.</div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    <button
                        type="button"
                        className="composer-upload-btn"
                        onClick={() => uploadInputRef.current?.click()}
                        title="Upload file/doc/image"
                        aria-label="Upload file/doc/image"
                    >
                        +
                    </button>
                    <input
                        ref={uploadInputRef}
                        type="file"
                        multiple
                        accept=".txt,.md,.pdf,.doc,.docx,.csv,.json,.png,.jpg,.jpeg,.webp,.gif"
                        className="composer-upload-input"
                        onChange={handleUploadFiles}
                    />
                    <button
                        type="button"
                        className="send-btn send-arrow-btn"
                        onClick={onSubmit}
                        disabled={!selectedModel || !value.trim() || disabled}
                        aria-label="Send"
                        title="Send"
                    >
                        ➜
                    </button>
                </div>
            </div>

            {!selectedModel && availableModels.length > 0 && (
                <div className="tools-field-hint composer-hint">
                    Select a model before sending.
                </div>
            )}

            {uploadedFiles.length > 0 && (
                <div className="composer-upload-preview">
                    {uploadedFiles.map((file, index) => (
                        <div key={`${file.name}-${index}`} className="composer-upload-chip">
                            <span className="composer-upload-chip-name" title={file.name}>{file.name}</span>
                            <button
                                type="button"
                                className="composer-upload-chip-remove"
                                onClick={() => removeUploadedFile(index)}
                                aria-label={`Remove ${file.name}`}
                            >
                                ✕
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {availableModels.length === 0 && (
                <div className="tools-field-hint composer-hint">
                    No models detected. Start Ollama or refresh the model list.
                </div>
            )}
        </div>
    )
}

export default function App() {
    const [chats, setChats]               = useState<Chat[]>([])
    const [activeChatId, setActiveChatId] = useState<string>("")
    const [activePage, setActivePage]     = useState<Page>("welcome")
    const [liveSteps, setLiveSteps]       = useState<AgentStep[]>([])
    const [currentAgent, setCurrentAgent] = useState<string>("")
    const [isLoading, setIsLoading]       = useState(false)
    const [input, setInput]               = useState("")
    const [welcomeInput, setWelcomeInput] = useState("")
    const [pendingMessage, setPendingMessage] = useState("")
    const [composerMode, setComposerMode] = useState<"chat" | "agent">("chat")
    const [toolSettings, setToolSettings] = useState<ToolSettings>(DEFAULT_SETTINGS)
    const [status, setStatus]             = useState<"online" | "offline" | "checking">("checking")
    const [availableModels, setAvailableModels] = useState<string[]>([])
    const [detectedModelTimes, setDetectedModelTimes] = useState<Record<string, string>>(() => loadModelDetectionTimes())
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
    const [isToolsOpen, setIsToolsOpen]   = useState(false)
    const [isAgentPanelCollapsed, setIsAgentPanelCollapsed] = useState(false)
    const inputRef        = useRef<HTMLInputElement>(null)
    const welcomeInputRef = useRef<HTMLInputElement>(null)

    const activeChat = chats.find((c) => c.id === activeChatId) ?? null
    const selectedModel = toolSettings.conversationModel || toolSettings.model

    function handleConversationModelChange(model: string) {
        setToolSettings((prev) => ({
            ...prev,
            conversationModel: model || undefined,
        }))
    }

    function handlePageChange(page: Page) {
        if (page === "tools") {
            setIsToolsOpen(true)
            return
        }

        setIsToolsOpen(false)
        setActivePage(page)
    }

    function handleCloseTools() {
        setIsToolsOpen(false)
    }

    async function handleRefreshAvailableModels() {
        const models = await listAvailableModels()
        setAvailableModels(models)
        setDetectedModelTimes((prev) => {
            const now = new Date().toISOString()
            const next: Record<string, string> = { ...prev }
            for (const model of models) {
                next[model] = now
            }
            return next
        })
    }

    // On mount: check health, load settings from localStorage, and fetch available models
    useEffect(() => {
        checkHealth().then((ok) => setStatus(ok ? "online" : "offline"))
        
        // Load persisted model settings
        const agentModels = loadAgentModels()
        const conversationModel = loadConversationModel()
        setToolSettings(prev => ({
            ...prev,
            agentModelSettings: agentModels,
            conversationModel,
        }))

        // Load previous chat ID from localStorage
        const savedChatId = localStorage.getItem("activeChatId")
        if (savedChatId) {
            console.log("[App] Restoring chat from localStorage:", savedChatId)
            setActiveChatId(savedChatId)
            setActivePage("chat")
        }

                // Load sessions list from backend
        listSessions().then((sessionsList) => {
            if (sessionsList.length > 0) {
                setChats((prev) => {
                    const prevById = new Map(prev.map(chat => [chat.id, chat]))
                    return sessionsList.map((session, index) => {
                        const existing = prevById.get(session.session_id)
                        return {
                            id: session.session_id,
                            title: existing?.title ?? session.title ?? `Chat ${sessionsList.length - index}`,
                            messages: existing?.messages ?? [],
                            timestamp: session.last_message_at || new Date().toISOString(),
                        }
                    })
                })
            }
        }).catch(err => console.warn("[App] Failed to load sessions:", err))

        // Fetch available models from backend and keep detection timestamps.
        listAvailableModels().then((models) => {
            setAvailableModels(models)
            setDetectedModelTimes((prev) => {
                const now = new Date().toISOString()
                const next: Record<string, string> = { ...prev }
                for (const model of models) {
                    if (!next[model]) {
                        next[model] = now
                    }
                }
                return next
            })
        })
    }, [])

    // Persist agent model settings whenever they change
    useEffect(() => {
        saveAgentModels(toolSettings.agentModelSettings)
    }, [toolSettings.agentModelSettings])

    // Persist conversation model whenever it changes
    useEffect(() => {
        saveConversationModel(toolSettings.conversationModel || undefined)
    }, [toolSettings.conversationModel])

    useEffect(() => {
        saveModelDetectionTimes(detectedModelTimes)
    }, [detectedModelTimes])

    // Load persistent session history when active chat changes
    useEffect(() => {
        if (!activeChatId || activeChatId === "") {
            return
        }

        const loadSessionHistory = async () => {
            try {
                const { title: sessionTitle, messages } = await getSessionHistory(activeChatId)
                const convertedMessages: ChatMessage[] = messages.map((msg: any, index) => {
                    const role: string = (msg as any).role || (msg as any).message_role || "user";
                    const content: string = (msg as any).content || (msg as any).message_content || "";
                    const timestamp: string = (msg as any).timestamp || (msg as any).created_at || new Date().toISOString();
                    return {
                        id: (msg as any).id || `msg-${index}`,
                        session_id: activeChatId,
                        task: role === "user" ? content : "",
                        answer: role === "assistant" ? content : "",
                        steps: [],
                        duration_seconds: 0,
                        timestamp: timestamp,
                        critique_performed: false,
                        critique_feedback: null,
                        critique_suggestions: [],
                        execution_mode: (role === "user" ? "agent" : "chat") as "chat" | "agent",
                        model_used: "Loaded from history",
                    };
                }).sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
                setChats((prev) => {
                    const exists = prev.some((chat) => chat.id === activeChatId)
                    if (exists) {
                        return prev.map((chat) =>
                            chat.id === activeChatId ? { ...chat, messages: convertedMessages, title: sessionTitle || chat.title } : chat
                        )
                    }
                    return [
                        ...prev,
                        {
                            id: activeChatId,
                            title: sessionTitle || "Chat",
                            messages: convertedMessages,
                            timestamp: new Date().toISOString(),
                        },
                    ]
                })
            } catch (error) {
                console.error("Failed to load session history:", error)
            }
        }

        loadSessionHistory()
    }, [activeChatId])

    // Save active chat ID to localStorage whenever it changes
    useEffect(() => {
        if (activeChatId) {
            localStorage.setItem("activeChatId", activeChatId)
            console.log("[App] Saved active chat ID to localStorage:", activeChatId)
        } else {
            localStorage.removeItem("activeChatId")
        }
    }, [activeChatId])

    function handleNewChat() {
        setActiveChatId("")
        setActivePage("welcome")
        setLiveSteps([])
        setInput("")
        setWelcomeInput("")
    }

    function handleSelectChat(id: string) {
        setActiveChatId(id)
        setActivePage("chat")
        const chat = chats.find((c) => c.id === id)
        setLiveSteps(chat?.messages.flatMap((m) => m.steps) ?? [])
    }

    async function handleDeleteChat(id: string) {
        // Delete from backend first
        const success = await deleteChat(id)
        if (!success) {
            console.error(`Failed to delete chat ${id} from backend`)
            alert("Failed to delete chat. Please try again.")
            return
        }

        // Then update local state
        setChats((prev) => prev.filter((c) => c.id !== id))
        if (activeChatId === id) {
            const remaining = chats.filter((c) => c.id !== id)
            if (remaining.length > 0) {
                handleSelectChat(remaining[remaining.length - 1].id)
            } else {
                handleNewChat()
            }
        }
    }

    async function handleSend(taskOverride?: string) {
        const task = (taskOverride ?? input).trim()
        if (!task || isLoading) return
        if (!selectedModel) return

        // If on welcome page, create a new chat first
        let chatId = activeChatId
        if (activePage === "welcome" || !chatId) {
            const id = generateId()
            const newChat: Chat = {
                id,
                title: generateTitle(task),
                messages: [],
                timestamp: new Date().toISOString(),
            }
            setChats((prev) => [...prev, newChat])
            setActiveChatId(id)
            setActivePage("chat")
            chatId = id
        }

        setInput("")
        setPendingMessage(task)
        setWelcomeInput("")
        setIsLoading(true)
        setLiveSteps([])
        setCurrentAgent(composerMode === "agent" ? "router" : "")

        // Create initial message with metadata for streaming
        const messageId = generateId()
        const messageStartTime = new Date().toISOString()
        let currentAnswer = ""
        let currentSteps: ChatMessage["steps"] = []
        let streamingMetadata: any = {
            duration_seconds: 0,
            critique_performed: false,
            critique_feedback: null,
            critique_suggestions: [],
            execution_mode: composerMode,
            model_used: selectedModel || "Model",
            token_usage: {
                prompt_tokens: 0,
                completion_tokens: 0,
                total_tokens: 0,
            },
            session_id: chatId,
        }

        // Create empty message immediately to avoid duplication
        const initialMessage: ChatMessage = {
            id: messageId,
            task,
            answer: "",
            steps: [],
            timestamp: messageStartTime,
            ...streamingMetadata,
        }

        setChats((prev) => prev.map((chat) => {
            if (chat.id !== chatId) return chat
            return {
                ...chat,
                messages: [...chat.messages, initialMessage],
            }
        }))

        try {
            // Stream the response
            console.log("[Chat] Starting stream for task:", task)
            await sendMessageStream(
                task,
                composerMode,
                toolSettings.conversationModel || toolSettings.model,
                toolSettings.temperature,
                toolSettings.userName,
                toolSettings.agentModelSettings,
                toolSettings.ragSettings,
                chatId,
                toolSettings.autoCritique,
                false,
                (event) => {
                    console.log("[Chat] Received event:", event.type, event)
                    
                    if (event.type === "step") {
                        // Update current agent and add step to live steps
                        const agentName = event.agent || "system"
                        setCurrentAgent(agentName)
                        const step = {
                            agent: agentName,
                            message: event.message || "",
                            timestamp: event.timestamp || new Date().toISOString(),
                        }
                        currentSteps.push(step)
                        setLiveSteps((prev) => [...prev, step])
                        console.log("[Chat] Added step:", step)
                    } else if (event.type === "token") {
                        // Append token to current answer
                        const content = event.content || ""
                        currentAnswer += content
                        console.log("[Chat] Added token, current answer length:", currentAnswer.length)
                    } else if (event.type === "done") {
                        // Update metadata from completion event
                        console.log("[Chat] Received done event")
                        streamingMetadata = {
                            ...streamingMetadata,
                            session_id: event.session_id || chatId,
                            duration_seconds: event.duration_seconds || 0,
                            critique_performed: event.critique_performed || false,
                            critique_feedback: event.critique_feedback || null,
                            critique_suggestions: event.critique_suggestions || [],
                            execution_mode: event.execution_mode || composerMode,
                            model_used: event.model_used || selectedModel || "Model",
                            retrieved_documents: event.retrieved_documents || [],
                            token_usage: event.token_usage || streamingMetadata.token_usage,
                        }
                    } else if (event.type === "error") {
                        console.error("[Chat] Stream error:", event.message)
                    }

                    // Update the message in real-time
                    setChats((prev) => prev.map((chat) => {
                        if (chat.id !== chatId) return chat
                        
                        return {
                            ...chat,
                            messages: chat.messages.map((msg) => {
                                if (msg.id === messageId) {
                                    console.log("[Chat] Updating message, answer length:", currentAnswer.length)
                                    return {
                                        ...msg,
                                        answer: currentAnswer,
                                        steps: currentSteps,
                                        ...streamingMetadata,
                                    }
                                }
                                return msg
                            }),
                        }
                    }))
                }
            )

            console.log("[Chat] Stream completed")
            setLiveSteps(currentSteps)
            setCurrentAgent("")
        } catch (err) {
            console.error("[Chat] Error:", err)
            setCurrentAgent("")
        } finally {
            setIsLoading(false)
            setPendingMessage("")
            inputRef.current?.focus()
            
            // After sending the first message, we should refresh the chat to get updated title
            if (activePage === "welcome" || !activeChatId) {
                // Force a refresh of the session to ensure title is properly set
                setTimeout(() => {
                    const chat = chats.find((c) => c.id === chatId)
                    if (chat) {
                        // This will trigger useEffect to reload session history 
                        setActiveChatId(chatId)
                    }
                }, 100)
            }
        }
    }

    const statusColour =
        status === "online"  ? "#69f0ae" :
        status === "offline" ? "#ff5252" : "#ffd740"

    const statusText =
        status === "online"  ? "● Online" :
        status === "offline" ? "● Offline" : "● Connecting..."

    const pageTitle =
        isToolsOpen ? "Tools" :
        activePage === "chat"    ? (activeChat?.title ?? "New Chat") :
        activePage === "search"  ? "Search" :
        activePage === "chats"   ? "Chats" :
        "Lunar"

    return (
        <div className="app">
            <Sidebar
                chats={chats}
                activeChatId={activeChatId}
                activePage={activePage}
                onNewChat={handleNewChat}
                onSelectChat={handleSelectChat}
                onDeleteChat={handleDeleteChat}
                onPageChange={handlePageChange}
                collapsed={sidebarCollapsed}
                onToggleCollapsed={() => setSidebarCollapsed((prev) => !prev)}
                toolsOpen={isToolsOpen}
            />

            <div className={`main ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
                {/* Title bar */}
                <header className="titlebar">
                    <div className="titlebar-left">
                        <span className="chat-title">{pageTitle}</span>
                    </div>
                    <div className="titlebar-right">
                        <span style={{ color: statusColour }}>{statusText}</span>
                    </div>
                </header>

                {/* Pages */}
                <div className="page-content">

                    {/* Welcome page */}
                    {activePage === "welcome" && (
                        <div className="welcome-page">
                            <div className="welcome-content">
                                <div className="welcome-logo">🌙</div>
                                <h1 className="welcome-title">Lunar</h1>
                                <p className="welcome-subtitle">
                                    What can I help you with today?
                                </p>
                                <ChatComposer
                                    value={welcomeInput}
                                    onChange={setWelcomeInput}
                                    onSubmit={() => handleSend(welcomeInput)}
                                    inputRefElement={welcomeInputRef}
                                    placeholder="Ask Lunar anything..."
                                    disabled={isLoading}
                                    selectedModel={selectedModel}
                                    availableModels={availableModels}
                                    onSelectModel={handleConversationModelChange}
                                    composerMode={composerMode}
                                    onModeChange={setComposerMode}
                                    settings={toolSettings}
                                    detectedModelTimes={detectedModelTimes}
                                    onRefreshModels={handleRefreshAvailableModels}
                                />
                            </div>
                        </div>
                    )}

                    {/* Chat page */}
                    {activePage === "chat" && (
                        <div className={`content ${toolSettings.showAgentActivity ? "with-activity" : "without-activity"} ${isAgentPanelCollapsed ? "agent-panel-collapsed" : "agent-panel-expanded"}`}>
                            <div className="left-col">
                                <ChatPanel
                                    messages={activeChat?.messages ?? []}
                                    isLoading={isLoading}
                                    pendingMessage={pendingMessage}
                                    currentAgent={currentAgent}
                                />
                                <ChatComposer
                                    value={input}
                                    onChange={setInput}
                                    onSubmit={() => handleSend()}
                                    inputRefElement={inputRef}
                                    placeholder={
                                        composerMode === "agent"
                                            ? "Ask Lunar to do a task..."
                                            : "Chat with Lunar..."
                                    }
                                    disabled={isLoading}
                                    selectedModel={selectedModel}
                                    availableModels={availableModels}
                                    onSelectModel={handleConversationModelChange}
                                    composerMode={composerMode}
                                    onModeChange={setComposerMode}
                                    settings={toolSettings}
                                    detectedModelTimes={detectedModelTimes}
                                    onRefreshModels={handleRefreshAvailableModels}
                                />
                            </div>

                            {toolSettings.showAgentActivity && (
                                <div className="right-col">
                                    <AgentPanel
                                        steps={liveSteps}
                                        isLoading={isLoading}
                                        currentAgent={currentAgent}
                                        onPanelCollapsedChange={setIsAgentPanelCollapsed}
                                    />
                                </div>
                            )}
                        </div>
                    )}

                    {/* Search page */}
                    {activePage === "search" && (
                        <div className="full-page">
                            <SearchPanel
                                chats={chats}
                                onSelectChat={handleSelectChat}
                            />
                        </div>
                    )}

                    {/* Chats page */}
                    {activePage === "chats" && (
                        <div className="full-page">
                            <ChatsPage
                                chats={chats}
                                activeChatId={activeChatId}
                                onSelectChat={handleSelectChat}
                                onDeleteChat={handleDeleteChat}
                            />
                        </div>
                    )}

                    {isToolsOpen && (
                        <div className="tools-overlay" role="dialog" aria-modal="true" aria-label="Tool settings">
                            <div className="tools-overlay-window" onClick={(e) => e.stopPropagation()}>
                                <ToolsPanel
                                    settings={toolSettings}
                                    onChange={setToolSettings}
                                    availableModels={availableModels}
                                    onClose={handleCloseTools}
                                />
                            </div>
                            <button
                                className="tools-backdrop"
                                aria-label="Close tool settings"
                                onClick={handleCloseTools}
                            />
                        </div>
                    )}

                </div>
            </div>
        </div>
    )
}
