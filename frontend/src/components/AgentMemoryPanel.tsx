import { useEffect, useState } from "react"
import type { AgentMemorySettings } from "../types"

interface MemoryEntry {
    id: number
    memory_type: string
    key_concept: string
    content: string
    category?: string
    relevance_score: number
    usage_count: number
}

interface Props {
    settings: AgentMemorySettings
    onChange: (settings: AgentMemorySettings) => void
}

export default function AgentMemoryPanel({ settings, onChange }: Props) {
    const [memories, setMemories] = useState<MemoryEntry[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [filterType, setFilterType] = useState<string>("all")
    const [searchQuery, setSearchQuery] = useState("")
    const [newMemory, setNewMemory] = useState({
        type: "fact",
        category: "general",
        content: "",
    })
    const [activeTab, setActiveTab] = useState<"view" | "add">("view")

    // Fetch memories on component mount and when filter changes
    useEffect(() => {
        fetchMemories()
    }, [filterType])

    async function fetchMemories() {
        setLoading(true)
        setError(null)
        try {
            const url = filterType === "all" 
                ? "/api/memory/list"
                : `/api/memory/list?memory_type=${filterType}`
            
            const response = await fetch(url)
            if (!response.ok) throw new Error("Failed to fetch memories")
            const data = await response.json()
            setMemories(data.memories || [])
        } catch (err) {
            setError(err instanceof Error ? err.message : "Unknown error")
        } finally {
            setLoading(false)
        }
    }

    async function handleAddMemory() {
        if (!newMemory.content.trim()) {
            setError("Memory content cannot be empty")
            return
        }

        setLoading(true)
        setError(null)

        try {
            let endpoint = "/api/memory/store-fact"
            if (newMemory.type === "experience") endpoint = "/api/memory/store-experience"
            else if (newMemory.type === "behavioral_rule") endpoint = "/api/memory/store-rule"

            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    content: newMemory.content,
                    category: newMemory.category,
                    memory_type: newMemory.type,
                }),
            })

            if (!response.ok) throw new Error("Failed to save memory")

            // Reset form and refresh list
            setNewMemory({ type: "fact", category: "general", content: "" })
            setActiveTab("view")
            await fetchMemories()
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to save memory")
        } finally {
            setLoading(false)
        }
    }

    async function handleDeleteMemory(id: number) {
        if (!confirm("Delete this memory?")) return

        try {
            const response = await fetch(`/api/memory/delete/${id}`, {
                method: "DELETE",
            })
            if (!response.ok) throw new Error("Failed to delete memory")
            await fetchMemories()
        } catch (err) {
            setError(err instanceof Error ? err.message : "Delete failed")
        }
    }

    async function handleClearAll() {
        if (!confirm("Clear all memories? This cannot be undone.")) return

        try {
            const response = await fetch(
                `/api/memory/clear-all${filterType !== "all" ? `?memory_type=${filterType}` : ""}`,
                { method: "POST" }
            )
            if (!response.ok) throw new Error("Failed to clear memories")
            await fetchMemories()
        } catch (err) {
            setError(err instanceof Error ? err.message : "Clear failed")
        }
    }

    async function handleSearch() {
        if (!searchQuery.trim()) {
            await fetchMemories()
            return
        }

        setLoading(true)
        try {
            const response = await fetch(
                `/api/memory/search?query=${encodeURIComponent(searchQuery)}&limit=20`
            )
            if (!response.ok) throw new Error("Search failed")
            const data = await response.json()
            setMemories(data.memories || [])
        } catch (err) {
            setError(err instanceof Error ? err.message : "Search failed")
        } finally {
            setLoading(false)
        }
    }

    const filteredMemories = memories.filter((mem) => {
        const matchesSearch =
            !searchQuery ||
            mem.key_concept.toLowerCase().includes(searchQuery.toLowerCase()) ||
            mem.content.toLowerCase().includes(searchQuery.toLowerCase())
        return matchesSearch
    })

    return (
        <div className="agent-memory-panel">
            <div className="memory-header">
                <h3 className="memory-title">Agent Memory</h3>
                <p className="memory-subtitle">Store and manage facts, experiences, and behavioral rules</p>
            </div>

            {/* Memory Settings */}
            <div className="memory-settings">
                <div className="memory-setting-row">
                    <label className="memory-label">
                        <input
                            type="checkbox"
                            checked={settings.enabled}
                            onChange={(e) => onChange({ ...settings, enabled: e.target.checked })}
                        />
                        Enable Agent Memory
                    </label>
                    <span className="memory-hint">Turn on/off agent memory system</span>
                </div>

                <div className="memory-setting-row">
                    <label className="memory-label">
                        <input
                            type="checkbox"
                            checked={settings.autoStore}
                            onChange={(e) => onChange({ ...settings, autoStore: e.target.checked })}
                        />
                        Auto-Store Facts
                    </label>
                    <span className="memory-hint">Automatically save learned facts from conversations</span>
                </div>

                <div className="memory-setting-row">
                    <label className="memory-label">
                        <input
                            type="checkbox"
                            checked={settings.autoRetrieve}
                            onChange={(e) => onChange({ ...settings, autoRetrieve: e.target.checked })}
                        />
                        Auto-Retrieve Context
                    </label>
                    <span className="memory-hint">Automatically load relevant memories for agent context</span>
                </div>
            </div>

            <div className="memory-separator" />

            {/* Tabs */}
            <div className="memory-tabs">
                <button
                    className={`memory-tab ${activeTab === "view" ? "active" : ""}`}
                    onClick={() => setActiveTab("view")}
                >
                    View Memories ({filteredMemories.length})
                </button>
                <button
                    className={`memory-tab ${activeTab === "add" ? "active" : ""}`}
                    onClick={() => setActiveTab("add")}
                >
                    + Add Memory
                </button>
            </div>

            {/* View Tab */}
            {activeTab === "view" && (
                <div className="memory-view">
                    {/* Search and Filter */}
                    <div className="memory-controls">
                        <input
                            type="text"
                            placeholder="Search memories..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                            className="memory-search"
                        />
                        <button onClick={handleSearch} className="memory-search-btn">
                            Search
                        </button>

                        <select
                            value={filterType}
                            onChange={(e) => setFilterType(e.target.value)}
                            className="memory-filter"
                        >
                            <option value="all">All Types</option>
                            <option value="fact">Facts</option>
                            <option value="experience">Experiences</option>
                            <option value="behavioral_rule">Behavioral Rules</option>
                        </select>

                        {filteredMemories.length > 0 && (
                            <button
                                onClick={handleClearAll}
                                className="memory-clear-btn"
                                title="Clear all memories of selected type"
                            >
                                Clear All
                            </button>
                        )}
                    </div>

                    {/* Error Display */}
                    {error && <div className="memory-error">{error}</div>}

                    {/* Memories List */}
                    <div className="memory-list">
                        {loading && <div className="memory-loading">Loading memories...</div>}

                        {!loading && filteredMemories.length === 0 && (
                            <div className="memory-empty">
                                <p>No memories stored yet</p>
                                <p className="memory-empty-hint">Add your first memory to get started</p>
                            </div>
                        )}

                        {!loading &&
                            filteredMemories.map((mem) => (
                                <div key={mem.id} className="memory-item">
                                    <div className="memory-item-header">
                                        <span className="memory-type-badge">{mem.memory_type}</span>
                                        {mem.category && (
                                            <span className="memory-category-badge">{mem.category}</span>
                                        )}
                                        <span className="memory-score">
                                            {mem.relevance_score.toFixed(1)} ★
                                        </span>
                                        <span className="memory-usage">Used {mem.usage_count}x</span>
                                    </div>
                                    <div className="memory-concept">{mem.key_concept}</div>
                                    <div className="memory-content">{mem.content}</div>
                                    <button
                                        onClick={() => handleDeleteMemory(mem.id)}
                                        className="memory-delete-btn"
                                    >
                                        Delete
                                    </button>
                                </div>
                            ))}
                    </div>
                </div>
            )}

            {/* Add Tab */}
            {activeTab === "add" && (
                <div className="memory-add">
                    <div className="memory-form">
                        <div className="form-group">
                            <label className="form-label">Memory Type</label>
                            <select
                                value={newMemory.type}
                                onChange={(e) => setNewMemory({ ...newMemory, type: e.target.value })}
                                className="form-input"
                            >
                                <option value="fact">Fact</option>
                                <option value="experience">Experience</option>
                                <option value="behavioral_rule">Behavioral Rule</option>
                            </select>
                            <span className="form-hint">
                                {newMemory.type === "fact" && "A learned fact or piece of information"}
                                {newMemory.type === "experience" && "A past experience and its outcome"}
                                {newMemory.type === "behavioral_rule" && "A rule or guideline for agent behavior"}
                            </span>
                        </div>

                        <div className="form-group">
                            <label className="form-label">Category</label>
                            <input
                                type="text"
                                placeholder="e.g., general, programming, research..."
                                value={newMemory.category}
                                onChange={(e) => setNewMemory({ ...newMemory, category: e.target.value })}
                                className="form-input"
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Memory Content</label>
                            <textarea
                                placeholder="Enter the fact, experience, or rule..."
                                value={newMemory.content}
                                onChange={(e) => setNewMemory({ ...newMemory, content: e.target.value })}
                                className="form-textarea"
                                rows={6}
                            />
                            <span className="form-hint">
                                Be specific and clear. This will help agents find and use this memory effectively.
                            </span>
                        </div>

                        {error && <div className="memory-error">{error}</div>}

                        <button
                            onClick={handleAddMemory}
                            disabled={loading}
                            className="form-submit"
                        >
                            {loading ? "Saving..." : "Save Memory"}
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
