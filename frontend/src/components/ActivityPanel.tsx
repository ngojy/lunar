import {useEffect, useRef } from "react"
import { AgentStep } from "../types"

interface Props {
    steps: AgentStep[]
    isLoading: boolean
    currentAgent: string
}


// AGENT_COLORS: maps each agent name to a color
const AGENT_COLORS: Record<string, string> = {
    orchestrator: "light blue",
    researcher: "purple",
    executor: "yellow",
    critic: "red",
    assembler: "green",
    system: "blue",
}


// ??: nullish coalescing operator, if AGENT_COLORS[agent] is undefined, fall back to "blue"
function agentColour(agent: string): string {
    return AGENT_COLORS[agent.toLowerCase()] ?? "blue"
}

function formatTime(iso: string) {
    return new Date(iso).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    })
}


// {isLoading && currentAgent && (...)} only shows the "Running..." row when the system is active and we know which agent is currently running
export default function ActivityPanel({ steps, isLoading, currentAgent }: Props) {
    const bottomRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [steps, isLoading])

    return (
        <div className="activity-panel">
            <div className="panel-label">
                Agent Activity
                {isLoading && <span className="live-badge">LIVE</span>}
            </div>

            <div className="activity-list">
                {steps.length === 0 && !isLoading && (
                    <div className="empty-state small">
                        <p>Agent steps will appear here as they run.</p>
                    </div>
                )}

                {steps.map((step, i) => (
                    <div key={i} className="activity-step">
                        <span
                        className="step-agent"
                        style={{ color: agentColour(step.agent) }}
                        >
                            ✓ {step.agent.toUpperCase()}
                        </span>
                        <span className="step-message">{step.message}</span>
                        <span className="step-time">{formatTime(step.timestamp)}</span>
                    </div>
                ))}

                {isLoading && currentAgent && (
                    <div className="activity-step running">
                        <span
                            className="step-agent"
                            style={{ color: agentColour(currentAgent) }}
                        >
                            ⠋ {currentAgent.toUpperCase()}
                        </span>
                        <span className="step-message">Running...</span>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>
        </div>
    )
}