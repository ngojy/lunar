import { useEffect, useMemo, useState, useRef } from "react"
import type { AgentStep } from "../types"

type AgentStatus = "idle" | "working" | "done" | "error" | "waiting-for-input"

type AgentRuntime = {
    id: string
    name: string
    role: string
    avatar: string
    status: AgentStatus
    currentTask: string
    taskDescription: string
    lastOutput: string
    color: string
}

type ActivityLogEntry = {
    timestamp: string
    agentId: string
    agentName: string
    message: string
}

type Props = {
    steps: AgentStep[]
    isLoading: boolean
    currentAgent: string
    onPanelCollapsedChange?: (isPanelCollapsed: boolean) => void
}

const AGENT_COLOR_PALETTE = [
    { name: "Azurite", hex: "#4d5d69" },
    { name: "Malachite", hex: "#54625f" },
    { name: "Gold", hex: "#9b5f47" },
    { name: "Dusty Rose", hex: "#9c6b6b" },
    { name: "Sage", hex: "#7d8a6f" },
    { name: "Slate Blue", hex: "#6b7a94" },
    { name: "Mauve", hex: "#8a7189" },
    { name: "Ochre", hex: "#b08a4e" },
    { name: "Teal Dim", hex: "#5c7d78" },
    { name: "Clay", hex: "#a8735a" },
]

function normalizeAgentId(agent: string): string {
    return agent.toLowerCase().replace(/\s+/g, "_")
}

const DEFAULT_AGENTS: AgentRuntime[] = [
    {
        id: "router",
        name: "Router",
        role: "Coordinator",
        avatar: "R",
        status: "idle",
        currentTask: "Awaiting routing tasks",
        taskDescription: "",
        lastOutput: "",
        color: AGENT_COLOR_PALETTE[0].hex,
    },
    {
        id: "planning",
        name: "Planner",
        role: "Researcher",
        avatar: "P",
        status: "idle",
        currentTask: "Awaiting planning tasks",
        taskDescription: "",
        lastOutput: "",
        color: AGENT_COLOR_PALETTE[1].hex,
    },
    {
        id: "retrieval",
        name: "Retrieval",
        role: "Knowledge",
        avatar: "K",
        status: "idle",
        currentTask: "Awaiting retrieval tasks",
        taskDescription: "",
        lastOutput: "",
        color: AGENT_COLOR_PALETTE[2].hex,
    },
    {
        id: "research_specialist",
        name: "Research Specialist",
        role: "Researcher",
        avatar: "RS",
        status: "idle",
        currentTask: "Awaiting research tasks",
        taskDescription: "",
        lastOutput: "",
        color: AGENT_COLOR_PALETTE[3].hex,
    },
    {
        id: "coding_specialist",
        name: "Coding Specialist",
        role: "Coder",
        avatar: "CS",
        status: "idle",
        currentTask: "Awaiting coding tasks",
        taskDescription: "",
        lastOutput: "",
        color: AGENT_COLOR_PALETTE[4].hex,
    },
    {
        id: "synthesizer",
        name: "Synthesizer",
        role: "Responder",
        avatar: "S",
        status: "idle",
        currentTask: "Awaiting synthesis tasks",
        taskDescription: "",
        lastOutput: "",
        color: AGENT_COLOR_PALETTE[5].hex,
    },
    {
        id: "critic",
        name: "Critic",
        role: "Reviewer",
        avatar: "C",
        status: "idle",
        currentTask: "Awaiting critique tasks",
        taskDescription: "",
        lastOutput: "",
        color: AGENT_COLOR_PALETTE[6].hex,
    },
]

function createAgentFromId(agentId: string): AgentRuntime {
    const words = agentId
        .split("_")
        .map((part) => part.trim())
        .filter(Boolean)

    const name = words
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ")

    const avatar = words.length > 1
        ? `${words[0].charAt(0)}${words[1].charAt(0)}`.toUpperCase()
        : (words[0]?.slice(0, 2).toUpperCase() || "A")

    return {
        id: agentId,
        name: name || "Agent",
        role: "Agent",
        avatar,
        status: "idle",
        currentTask: "Awaiting tasks",
        taskDescription: "",
        lastOutput: "",
        color: AGENT_COLOR_PALETTE[0].hex,
    }
}

function formatTime(iso: string) {
    return new Date(iso).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    })
}

function statusFromMessage(message: string): AgentStatus {
    const lower = message.toLowerCase()
    if (lower.includes("error") || lower.includes("failed")) return "error"
    if (lower.includes("waiting") || lower.includes("input")) return "waiting-for-input"
    return "done"
}

function statusClass(status: AgentStatus): string {
    if (status === "working") return "working"
    if (status === "done") return "done"
    if (status === "error") return "error"
    if (status === "waiting-for-input") return "waiting"
    return "idle"
}

export default function AgentPanel({ steps, isLoading, currentAgent, onPanelCollapsedChange }: Props) {
    const [isPanelCollapsed, setIsPanelCollapsed] = useState(false)
    const [expandedAgentId, setExpandedAgentId] = useState<string | null>(null)
    const [showActivityLog, setShowActivityLog] = useState(true)
    const [instructionInputByAgent, setInstructionInputByAgent] = useState<Record<string, string>>({})
    const [agents, setAgents] = useState<Record<string, AgentRuntime>>(() => {
        const byId: Record<string, AgentRuntime> = {}
        for (const agent of DEFAULT_AGENTS) {
            byId[agent.id] = agent
        }
        return byId
    })
    const [activityLog, setActivityLog] = useState<ActivityLogEntry[]>([])
    const activityLogRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        setAgents((prev) => {
            const next: Record<string, AgentRuntime> = { ...prev }

            for (const step of steps) {
                const id = normalizeAgentId(step.agent)
                if (!next[id]) {
                    next[id] = createAgentFromId(id)
                }

                next[id] = {
                    ...next[id],
                    status: statusFromMessage(step.message),
                    currentTask: step.message,
                    taskDescription: step.message,
                    lastOutput: step.message,
                }
            }

            if (isLoading && currentAgent) {
                const currentId = normalizeAgentId(currentAgent)
                if (!next[currentId]) {
                    next[currentId] = createAgentFromId(currentId)
                }

                next[currentId] = {
                    ...next[currentId],
                    status: "working",
                    currentTask: next[currentId].currentTask || "Running...",
                }
            }

            return next
        })

        if (steps.length > 0) {
            setActivityLog((prev) => {
                const seen = new Set(prev.map((entry) => `${entry.timestamp}|${entry.agentId}|${entry.message}`))
                const additions: ActivityLogEntry[] = []

                for (const step of steps) {
                    const agentId = normalizeAgentId(step.agent)
                    const key = `${step.timestamp}|${agentId}|${step.message}`
                    if (seen.has(key)) continue

                    additions.push({
                        timestamp: step.timestamp,
                        agentId,
                        agentName: step.agent,
                        message: step.message,
                    })
                    seen.add(key)
                }

                if (additions.length === 0) return prev
                return [...prev, ...additions]
            })
        }
    }, [steps, isLoading, currentAgent])

    useEffect(() => {
        if (activityLogRef.current && showActivityLog) {
            setTimeout(() => {
                if (activityLogRef.current) {
                    activityLogRef.current.scrollTop = activityLogRef.current.scrollHeight
                }
            }, 0)
        }
    }, [activityLog, showActivityLog])

    const orderedAgents = useMemo(() => Object.values(agents), [agents])

    const waitingCount = useMemo(
        () => orderedAgents.filter((agent) => agent.status === "waiting-for-input").length,
        [orderedAgents],
    )

    const hasPausedAgents = waitingCount > 0

    useEffect(() => {
        onPanelCollapsedChange?.(isPanelCollapsed)
    }, [isPanelCollapsed, onPanelCollapsedChange])

    function appendLog(agent: AgentRuntime, message: string) {
        setActivityLog((prev) => ([
            ...prev,
            {
                timestamp: new Date().toISOString(),
                agentId: agent.id,
                agentName: agent.name,
                message,
            },
        ]))
    }

    useEffect(() => {
        if (activityLogRef.current) {
            activityLogRef.current.scrollTop = activityLogRef.current.scrollHeight
        }
    }, [activityLog])

    function handleToggleAgent(agentId: string) {
        if (isPanelCollapsed) {
            setIsPanelCollapsed(false)
            setExpandedAgentId(agentId)
            return
        }

        setExpandedAgentId((prev) => (prev === agentId ? null : agentId))
    }

    function handlePauseAll() {
        setAgents((prev) => {
            const next: Record<string, AgentRuntime> = {}
            for (const [id, agent] of Object.entries(prev)) {
                next[id] = {
                    ...agent,
                    status: "waiting-for-input",
                }
            }
            return next
        })

        const now = new Date().toISOString()
        setActivityLog((prev) => ([
            ...prev,
            {
                timestamp: now,
                agentId: "system",
                agentName: "System",
                message: "Pause all agents",
            },
        ]))
    }

    function handleResumeAll() {
        setAgents((prev) => {
            const next: Record<string, AgentRuntime> = {}
            for (const [id, agent] of Object.entries(prev)) {
                next[id] = {
                    ...agent,
                    status: agent.status === "waiting-for-input" ? "idle" : agent.status,
                }
            }
            return next
        })

        const now = new Date().toISOString()
        setActivityLog((prev) => ([
            ...prev,
            {
                timestamp: now,
                agentId: "system",
                agentName: "System",
                message: "Resume all agents",
            },
        ]))
    }

    function handleAgentTaskChange(agentId: string, value: string) {
        setAgents((prev) => ({
            ...prev,
            [agentId]: {
                ...prev[agentId],
                taskDescription: value,
                currentTask: value,
            },
        }))
    }

    function handleInstructionInputChange(agentId: string, value: string) {
        setInstructionInputByAgent((prev) => ({
            ...prev,
            [agentId]: value,
        }))
    }

    function handleSendInstruction(agent: AgentRuntime) {
        const instruction = (instructionInputByAgent[agent.id] || "").trim()
        if (!instruction) return

        setAgents((prev) => ({
            ...prev,
            [agent.id]: {
                ...prev[agent.id],
                status: "working",
                currentTask: instruction,
                taskDescription: prev[agent.id].taskDescription || instruction,
                lastOutput: `Instruction queued: ${instruction}`,
            },
        }))

        setInstructionInputByAgent((prev) => ({
            ...prev,
            [agent.id]: "",
        }))

        appendLog(agent, `Instruction sent: ${instruction}`)
    }

    function handlePauseAgent(agent: AgentRuntime) {
        setAgents((prev) => ({
            ...prev,
            [agent.id]: {
                ...prev[agent.id],
                status: "waiting-for-input",
            },
        }))
        appendLog(agent, "Paused")
    }

    function handleStopAgent(agent: AgentRuntime) {
        setAgents((prev) => ({
            ...prev,
            [agent.id]: {
                ...prev[agent.id],
                status: "idle",
                currentTask: "Stopped",
                lastOutput: "Stopped by user",
            },
        }))
        appendLog(agent, "Stopped")
    }

    return (
        <aside className={`agent-panel ${isPanelCollapsed ? "collapsed" : "expanded"}`}>
            {isPanelCollapsed && (
                <div className="agent-panel-header agent-panel-header-collapsed">
                    <button
                        type="button"
                        className="agent-panel-toggle"
                        onClick={() => setIsPanelCollapsed(false)}
                        aria-label="Expand agent panel"
                        title="Expand"
                    >
                        ▸
                        {waitingCount > 0 && <span className="agent-panel-badge">{waitingCount}</span>}
                    </button>
                </div>
            )}

            {!isPanelCollapsed && (
                <div className="agent-panel-header">
                    <button
                        type="button"
                        className="agent-panel-toggle"
                        onClick={() => setIsPanelCollapsed(true)}
                        aria-label="Collapse agent panel"
                        title="Collapse"
                    >
                        ◂
                        {waitingCount > 0 && <span className="agent-panel-badge">{waitingCount}</span>}
                    </button>

                    <div className="agent-panel-title">Agents</div>

                    <div className="agent-panel-controls">
                        <button
                            type="button"
                            className="agent-control-btn"
                            onClick={hasPausedAgents ? handleResumeAll : handlePauseAll}
                            title={hasPausedAgents ? "Resume all" : "Pause all"}
                        >
                            <span className="agent-control-icon">{hasPausedAgents ? "▶" : "⏸"}</span>
                            <span>{hasPausedAgents ? "Resume All" : "Pause All"}</span>
                        </button>
                    </div>
                </div>
            )}



            <div className="agent-roster">
                {orderedAgents.map((agent) => (
                    <div
                        key={agent.id}
                        className={`agent-card ${expandedAgentId === agent.id ? "open" : ""} ${normalizeAgentId(currentAgent) === agent.id ? "active" : ""}`}
                        style={normalizeAgentId(currentAgent) === agent.id ? { borderColor: agent.color, borderWidth: "2px" } : undefined}
                    >
                        <button
                            type="button"
                            className="agent-card-head"
                            onClick={() => handleToggleAgent(agent.id)}
                            title={isPanelCollapsed ? `${agent.name} (${agent.role})` : undefined}
                        >
                            <span className="agent-avatar-wrap">
                                <span className="agent-avatar" style={{ borderColor: agent.color }}>{agent.avatar}</span>
                                <span className={`agent-status-dot ${statusClass(agent.status)}`} />
                            </span>

                            {!isPanelCollapsed && (
                                <span className="agent-card-main">
                                    <span className="agent-card-title-row">
                                        <span className="agent-name" style={{ color: agent.color }}>{agent.name}</span>
                                        <span className="agent-role">{agent.role}</span>
                                    </span>
                                    <span className="agent-task" title={agent.currentTask}>{agent.currentTask}</span>
                                </span>
                            )}
                        </button>

                        {!isPanelCollapsed && expandedAgentId === agent.id && (
                            <div className="agent-card-expanded">
                                <textarea
                                    className="agent-textarea"
                                    value={agent.taskDescription}
                                    onChange={(e) => handleAgentTaskChange(agent.id, e.target.value)}
                                    placeholder="Task description"
                                />
                                <div className="agent-output" title={agent.lastOutput || "No output yet"}>
                                    {agent.lastOutput || "No output yet."}
                                </div>
                                <div className="agent-instruction-row">
                                    <input
                                        className="agent-input"
                                        placeholder="Send instruction"
                                        value={instructionInputByAgent[agent.id] || ""}
                                        onChange={(e) => handleInstructionInputChange(agent.id, e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === "Enter") {
                                                e.preventDefault()
                                                handleSendInstruction(agent)
                                            }
                                        }}
                                    />
                                    <button type="button" className="agent-primary-btn" onClick={() => handleSendInstruction(agent)}>
                                        Send
                                    </button>
                                </div>
                                <div className="agent-action-row">
                                    <button type="button" className="agent-secondary-btn" onClick={() => handlePauseAgent(agent)}>
                                        Pause
                                    </button>
                                    <button type="button" className="agent-secondary-btn" onClick={() => handleStopAgent(agent)}>
                                        Stop
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {!isPanelCollapsed && (
                <div className="agent-log-section">
                <button
                    type="button"
                    className="agent-log-toggle"
                    onClick={() => setShowActivityLog((prev) => !prev)}
                    title="Toggle activity log"
                >
                    <span className="agent-control-icon">🕒</span>
                    <span>Activity log</span>
                </button>

                {showActivityLog && (
                    <div className="agent-log-list" ref={activityLogRef}>
                        {activityLog.length === 0 && (
                            <div className="agent-log-item">No activity yet.</div>
                        )}

                        {activityLog.map((entry, index) => {
                            const agentForColor = Object.values(agents).find((a) => a.id === entry.agentId)
                            return (
                                <div key={`${entry.timestamp}-${entry.agentId}-${index}`} className="agent-log-item">
                                    <span className="agent-log-time">{formatTime(entry.timestamp)}</span>
                                    {" "}
                                    <span className="agent-log-name" style={{ color: agentForColor?.color || "#fff" }}>
                                        {entry.agentName}:
                                    </span>
                                    {" "}
                                    {entry.message}
                                </div>
                            )
                        })}
                    </div>
                )}
                </div>
            )}
        </aside>
    )
}
