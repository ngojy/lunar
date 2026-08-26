import { useEffect, useMemo, useState } from "react"
import type { ToolSettings } from "../types"

interface OllamaModel {
    name: string
    size: number
    modified_at: string
}

interface Props {
    onSelectModel: (model: string) => void
    currentModel: string
    settings: ToolSettings
}


function formatSize(bytes: number): string {
    const gb = bytes / 1024 / 1024 / 1024
    return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(bytes / 1024 / 1024).toFixed(0)} MB`
}

function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString([], {
        month: "short", day: "numeric", year: "numeric",
    })
}


function formatMode(modelName: string, settings: ToolSettings): string {
    const chatModel = settings.conversationModel || settings.model
    const agentModels = Object.values(settings.agentModelSettings || {}).filter(Boolean)
    const isChat = chatModel === modelName
    const isAgent = agentModels.includes(modelName)

    if (isChat && isAgent) return "Chat + Agent"
    if (isChat) return "Chat"
    if (isAgent) return "Agent"
    return "Available"
}

export default function ModelDetector({ onSelectModel, currentModel, settings }: Props) {
    const [models, setModels]   = useState<OllamaModel[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError]     = useState("")
    const [detected, setDetected] = useState(false)
    const [search, setSearch] = useState("")

    async function detectModels() {
        setLoading(true)
        setError("")

        try {
            const res = await fetch("http://localhost:11434/api/tags")
            if (!res.ok) throw new Error("Ollama not reachable")
            const data = await res.json()
            setModels(data.models ?? [])
            setDetected(true)
        } catch (e) {
            setError("Could not connect to Ollama. Make sure it is running.")
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        detectModels()
    }, [])

    const sortedModels = useMemo(() => {
        return [...models].sort(
            (a, b) => new Date(b.modified_at).getTime() - new Date(a.modified_at).getTime()
        )
    }, [models])

    const query = search.trim().toLowerCase()
    const filteredModels = useMemo(() => {
        if (!query) return sortedModels
        return sortedModels.filter((model) => {
            const mode = formatMode(model.name, settings).toLowerCase()
            return (
                model.name.toLowerCase().includes(query) ||
                mode.includes(query) ||
                formatSize(model.size).toLowerCase().includes(query) ||
                formatDate(model.modified_at).toLowerCase().includes(query)
            )
        })
    }, [query, settings, sortedModels])

    const recentModels = filteredModels.slice(0, 5)
    const remainingModels = filteredModels.slice(recentModels.length)

    return (
        <div className="model-detector">
            <div className="model-detector-header">
                <div className="model-detector-header-copy">
                    <span className="tools-section-label">Installed Models</span>
                    <span className="model-detector-subtitle">Search, sort, and pick a model</span>
                </div>
                <div className="model-detector-actions">
                    <input
                        className="model-detector-search"
                        placeholder="Search models..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                    <button
                        className="model-refresh-btn"
                        onClick={detectModels}
                        disabled={loading}
                    >
                        {loading ? "Scanning..." : "↻ Refresh"}
                    </button>
                </div>
            </div>

            {error && (
                <div className="model-detector-error">{error}</div>
            )}

            {!error && detected && models.length === 0 && (
                <div className="side-panel-empty">No models found</div>
            )}

            {recentModels.length > 0 && (
                <div className="model-section">
                    <div className="model-section-title">Recently Added</div>
                    <div className="model-section-subtitle">Most recently pulled models</div>
                    <div className="model-list">
                        {recentModels.map((model) => (
                            <button
                                key={model.name}
                                className={`model-item ${model.name === currentModel ? "active" : ""}`}
                                onClick={() => onSelectModel(model.name)}
                            >
                                <div className="model-item-left">
                                    <span className="model-item-name">{model.name}</span>
                                    <span className="model-item-date">
                                        Pulled {formatDate(model.modified_at)}
                                    </span>
                                </div>
                                <div className="model-item-right">
                                    <span className="model-item-mode">{formatMode(model.name, settings)}</span>
                                    <span className="model-item-size">{formatSize(model.size)}</span>
                                    {model.name === currentModel && (
                                        <span className="model-item-active">✓ Active</span>
                                    )}
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {remainingModels.length > 0 && (
                <div className="model-section">
                    <div className="model-section-title">All Models</div>
                    <div className="model-section-subtitle">Everything available in Ollama</div>
                    <div className="model-list">
                        {remainingModels.map((model) => (
                            <button
                                key={model.name}
                                className={`model-item ${model.name === currentModel ? "active" : ""}`}
                                onClick={() => onSelectModel(model.name)}
                            >
                                <div className="model-item-left">
                                    <span className="model-item-name">{model.name}</span>
                                    <span className="model-item-date">
                                        Pulled {formatDate(model.modified_at)}
                                    </span>
                                </div>
                                <div className="model-item-right">
                                    <span className="model-item-mode">{formatMode(model.name, settings)}</span>
                                    <span className="model-item-size">{formatSize(model.size)}</span>
                                    {model.name === currentModel && (
                                        <span className="model-item-active">✓ Active</span>
                                    )}
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}