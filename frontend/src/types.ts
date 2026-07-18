// AgentStep: one action taken by an agent
export interface AgentStep {
    agent: string
    message: string
    timestamp: string
}


// ChatMessage: a message in the chat, which includes the task, answer, and steps taken by the agent
export interface ChatMessage {
    id: string
    task: string
    answer: string
    steps: AgentStep[]
    duration_seconds: number
    timestamp: string
}
