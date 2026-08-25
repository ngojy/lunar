import { useRef, useState } from "react"
import type { ToolSettings } from "../types"
import { AGENT_NAMES, getAgentDisplayName } from "../modelSettings"
import ModelDetector from "./ModelDetector"
import StoragePanel from "./StoragePanel"
import AgentMemoryPanel from "./AgentMemoryPanel"

interface Props {
    settings: ToolSettings
    onChange: (settings: ToolSettings) => void
    availableModels: string[]
    onClose: () => void
}

const TABS = [
    { id: "model",   label: "Model" },
    { id: "general", label: "General" },
    { id: "display", label: "Display" },
    { id: "rag", label: "RAG" },
    { id: "agent-memory", label: "Agent Memory" },
    { id: "storage", label: "Storage" },
]

function SliderToggle({
    value,
    onChange,
}: {
    value: boolean
    onChange: (v: boolean) => void
}) {
    return (
        <div
            className={`toggle-track ${value ? "on" : ""}`}
            onClick={() => onChange(!value)}
        >
            <div className="toggle-thumb" />
        </div>
    )
}

export default function ToolsPanel({ settings, onChange, availableModels, onClose }: Props) {
    const modelRef   = useRef<HTMLDivElement | null>(null)
    const ragRef = useRef<HTMLDivElement | null>(null)
    const generalRef = useRef<HTMLDivElement | null>(null)
    const displayRef = useRef<HTMLDivElement | null>(null)
    const agentMemoryRef = useRef<HTMLDivElement | null>(null)
    const storageRef = useRef<HTMLDivElement | null>(null)
    const [search, setSearch] = useState("")

    const refs: Record<string, React.RefObject<HTMLDivElement | null>> = {
        model:   modelRef,
        general: generalRef,
        display: displayRef,
        rag: ragRef,
        "agent-memory": agentMemoryRef,
        storage: storageRef,
    }

    function scrollTo(id: string) {
        refs[id]?.current?.scrollIntoView({ behavior: "smooth", block: "start" })
    }

    function updateModel(model: string) {
        onChange({ ...settings, model })
    }

    function updateTemperature(temperature: number) {
        onChange({ ...settings, temperature })
    }

    function updateAgentModel(agentName: string, model: string) {
        const updatedSettings = { ...settings.agentModelSettings }
        if (model === "") {
            delete updatedSettings[agentName]
        } else {
            updatedSettings[agentName] = model
        }
        onChange({
            ...settings,
            agentModelSettings: updatedSettings,
        })
    }

    const query = search.trim().toLowerCase()
    const modelMatches = !query || "model temperature per-agent".includes(query) || availableModels.some((model) => model.toLowerCase().includes(query))
    const ragMatches = !query || "rag retrieval files docs database embedding chunk sqlite postgres mysql".includes(query)
    const generalMatches = !query || "general your name user name personalize".includes(query)
    const displayMatches = !query || "display agent activity panel".includes(query)
    const agentMemoryMatches = !query || "agent memory facts experiences rules learning behavior".includes(query)

    const filteredAgentNames = AGENT_NAMES.filter((agent) => {
        if (!query) return true
        return getAgentDisplayName(agent).toLowerCase().includes(query) || agent.toLowerCase().includes(query)
    })

    return (
        <div className="tools-page-shell">
            <div className="tools-card">
                <div className="tools-card-header">
                    <div>
                        <div className="tools-card-title">Settings</div>
                        <div className="tools-card-subtitle">Search and tune Lunar</div>
                    </div>
                    <div className="tools-header-actions">
                        <input
                            className="tools-search-input"
                            placeholder="Search settings..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                        <button className="tools-close-btn" onClick={onClose} aria-label="Close tool settings" title="Close">
                            ✕
                        </button>
                    </div>
                </div>

                <div className="tools-layout">
                    <div className="tools-tabs">
                        {TABS.map((tab) => (
                            <button
                                key={tab.id}
                                className="tools-tab"
                                onClick={() => scrollTo(tab.id)}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    <div className="tools-scroll">
                        {modelMatches && (
                            <div ref={modelRef} className="tools-section-block">
                                <div className="tools-section-title">Model</div>
                                <div className="tools-section-desc">
                                    Select and configure the AI model powering Lunar.
                                </div>
                                <div className="tools-separator" />

                                <ModelDetector
                                    currentModel={settings.model}
                                    onSelectModel={updateModel}
                                    settings={settings}
                                />

                                <div className="tools-field">
                                    <label className="tools-label">
                                        Temperature
                                        <span className="tools-value">
                                            {settings.temperature.toFixed(1)}
                                        </span>
                                    </label>
                                    <input
                                        type="range"
                                        className="tools-slider"
                                        min={0}
                                        max={1}
                                        step={0.1}
                                        value={settings.temperature}
                                        onChange={(e) => updateTemperature(parseFloat(e.target.value))}
                                    />
                                    <div className="tools-slider-labels">
                                        <span>Precise</span>
                                        <span>Creative</span>
                                    </div>
                                </div>

                                <div className="tools-separator" style={{ marginTop: "1.5em" }} />
                                <div style={{ marginTop: "1.5em" }}>
                                    <div className="tools-label">Per-Agent Models</div>
                                    <p className="tools-field-hint">
                                        Override the model for specific agents (leave blank to use the conversation model).
                                    </p>
                                    {filteredAgentNames.map((agent) => (
                                        <div key={agent} className="tools-field" style={{ marginTop: "0.75em" }}>
                                            <label className="tools-label">{getAgentDisplayName(agent)}</label>
                                            <select
                                                className="tools-text-input"
                                                style={{ width: "100%" }}
                                                value={settings.agentModelSettings[agent] || ""}
                                                onChange={(e) => updateAgentModel(agent, e.target.value)}
                                            >
                                                <option value="">Conversation model</option>
                                                {availableModels.map((model) => (
                                                    <option key={model} value={model}>
                                                        {model}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {generalMatches && (
                            <div ref={generalRef} className="tools-section-block">
                                <div className="tools-section-title">General</div>
                                <div className="tools-section-desc">
                                    Personalise your experience with Lunar.
                                </div>
                                <div className="tools-separator" />

                                <div className="tools-field">
                                    <label className="tools-label">Your Name</label>
                                    <p className="tools-field-hint">
                                        Lunar will address you by this name during conversations.
                                    </p>
                                    <input
                                        className="tools-text-input"
                                        placeholder="Enter your name..."
                                        value={settings.userName}
                                        onChange={(e) =>
                                            onChange({ ...settings, userName: e.target.value })
                                        }
                                    />
                                </div>
                            </div>
                        )}

                        <div className="tools-page-separator" />

                        {displayMatches && (
                            <div ref={displayRef} className="tools-section-block">
                                <div className="tools-section-title">Display</div>
                                <div className="tools-section-desc">
                                    Control what is visible on the chat page.
                                </div>
                                <div className="tools-separator" />

                                <div className="tools-row">
                                    <div className="tools-row-info">
                                        <span className="tools-row-name">Agent Activity Panel</span>
                                        <span className="tools-row-desc">
                                            Show live agent activity on the right side of the chat page
                                        </span>
                                    </div>
                                    <SliderToggle
                                        value={settings.showAgentActivity}
                                        onChange={(v) =>
                                            onChange({ ...settings, showAgentActivity: v })
                                        }
                                    />
                                </div>
                            </div>
                        )}

                        {ragMatches && (
                            <div ref={ragRef} className="tools-section-block">
                                <div className="tools-section-title">RAG Sources</div>
                                <div className="tools-section-desc">
                                    Configure semantic retrieval for files, documents, and database records.
                                </div>
                                <div className="tools-separator" />

                                <div className="tools-row">
                                    <div className="tools-row-info">
                                        <span className="tools-row-name">Enable RAG</span>
                                        <span className="tools-row-desc">Enable multi-source retrieval during agent mode</span>
                                    </div>
                                    <SliderToggle
                                        value={settings.ragSettings.enabled}
                                        onChange={(v) => onChange({
                                            ...settings,
                                            ragSettings: { ...settings.ragSettings, enabled: v },
                                        })}
                                    />
                                </div>

                                <div className="tools-row">
                                    <div className="tools-row-info">
                                        <span className="tools-row-name">Include Web</span>
                                        <span className="tools-row-desc">Use Tavily or DuckDuckGo as a retrieval source</span>
                                    </div>
                                    <SliderToggle
                                        value={settings.ragSettings.include_web}
                                        onChange={(v) => onChange({
                                            ...settings,
                                            ragSettings: { ...settings.ragSettings, include_web: v },
                                        })}
                                    />
                                </div>

                                <div className="tools-row">
                                    <div className="tools-row-info">
                                        <span className="tools-row-name">Include Files/Docs</span>
                                        <span className="tools-row-desc">Scan configured roots and retrieve semantic chunks</span>
                                    </div>
                                    <SliderToggle
                                        value={settings.ragSettings.include_files}
                                        onChange={(v) => onChange({
                                            ...settings,
                                            ragSettings: { ...settings.ragSettings, include_files: v },
                                        })}
                                    />
                                </div>

                                <div className="tools-row">
                                    <div className="tools-row-info">
                                        <span className="tools-row-name">Include Database</span>
                                        <span className="tools-row-desc">Retrieve semantic matches from configured table rows</span>
                                    </div>
                                    <SliderToggle
                                        value={settings.ragSettings.include_db}
                                        onChange={(v) => onChange({
                                            ...settings,
                                            ragSettings: { ...settings.ragSettings, include_db: v },
                                        })}
                                    />
                                </div>

                                <div className="tools-field">
                                    <label className="tools-label">File/Doc Root Paths</label>
                                    <p className="tools-field-hint">Comma-separated absolute folder paths.</p>
                                    <input
                                        className="tools-text-input"
                                        value={settings.ragSettings.file_roots}
                                        placeholder="C:\\docs, C:\\projects\\notes"
                                        onChange={(e) => onChange({
                                            ...settings,
                                            ragSettings: { ...settings.ragSettings, file_roots: e.target.value },
                                        })}
                                    />
                                </div>

                                <div className="tools-field">
                                    <label className="tools-label">File Extensions</label>
                                    <p className="tools-field-hint">Comma-separated extensions to scan.</p>
                                    <input
                                        className="tools-text-input"
                                        value={settings.ragSettings.file_extensions}
                                        placeholder=".txt,.md,.pdf,.docx"
                                        onChange={(e) => onChange({
                                            ...settings,
                                            ragSettings: { ...settings.ragSettings, file_extensions: e.target.value },
                                        })}
                                    />
                                </div>

                                <div className="tools-field">
                                    <label className="tools-label">Embedding Model</label>
                                    <input
                                        className="tools-text-input"
                                        value={settings.ragSettings.embedding_model}
                                        placeholder="nomic-embed-text"
                                        onChange={(e) => onChange({
                                            ...settings,
                                            ragSettings: { ...settings.ragSettings, embedding_model: e.target.value },
                                        })}
                                    />
                                </div>

                                <div className="tools-field">
                                    <label className="tools-label">DB Type</label>
                                    <select
                                        className="tools-text-input"
                                        value={settings.ragSettings.db_type}
                                        onChange={(e) => onChange({
                                            ...settings,
                                            ragSettings: {
                                                ...settings.ragSettings,
                                                db_type: e.target.value as "sqlite" | "postgres" | "mysql",
                                            },
                                        })}
                                    >
                                        <option value="sqlite">sqlite</option>
                                        <option value="postgres">postgres</option>
                                        <option value="mysql">mysql</option>
                                    </select>
                                </div>

                                <div className="tools-field">
                                    <label className="tools-label">DB Connection</label>
                                    <input
                                        className="tools-text-input"
                                        value={settings.ragSettings.db_connection}
                                        placeholder="sqlite:///C:\\data\\app.db"
                                        onChange={(e) => onChange({
                                            ...settings,
                                            ragSettings: { ...settings.ragSettings, db_connection: e.target.value },
                                        })}
                                    />
                                </div>

                                <div className="tools-field">
                                    <label className="tools-label">DB Table</label>
                                    <input
                                        className="tools-text-input"
                                        value={settings.ragSettings.db_table}
                                        placeholder="documents"
                                        onChange={(e) => onChange({
                                            ...settings,
                                            ragSettings: { ...settings.ragSettings, db_table: e.target.value },
                                        })}
                                    />
                                </div>

                                <div className="tools-field">
                                    <label className="tools-label">DB Text Columns</label>
                                    <input
                                        className="tools-text-input"
                                        value={settings.ragSettings.db_text_columns}
                                        placeholder="content,text,body,description"
                                        onChange={(e) => onChange({
                                            ...settings,
                                            ragSettings: { ...settings.ragSettings, db_text_columns: e.target.value },
                                        })}
                                    />
                                </div>
                            </div>
                        )}

                        <div className="tools-page-separator" />

                        {agentMemoryMatches && (
                            <div ref={agentMemoryRef} className="tools-section-block">
                                <div className="tools-section-title">Agent Memory</div>
                                <div className="tools-section-desc">
                                    Store and manage facts, experiences, and behavioral rules for agents.
                                </div>
                                <div className="tools-separator" />
                                <AgentMemoryPanel
                                    settings={settings.agentMemorySettings}
                                    onChange={(agentMemorySettings) =>
                                        onChange({ ...settings, agentMemorySettings })
                                    }
                                />
                            </div>
                        )}

                        <div className="tools-page-separator" />

                        {
                            <div ref={storageRef} className="tools-section-block">
                                <StoragePanel onClose={onClose} />
                            </div>
                        }
                    </div>
                </div>
            </div>
        </div>
    )
}