// Agent model settings: maps agent name to their selected model
export interface AgentModelSettings {
    [key: string]: string | undefined;
}

// Agent memory settings
export interface AgentMemorySettings {
    enabled: boolean
    autoStore: boolean  // Automatically store facts from conversations
    autoRetrieve: boolean  // Automatically retrieve relevant memories for context
}

// Agent memory entry (from backend)
export interface AgentStep {
    agent: string
    message: string
    timestamp: string
}

export interface TokenUsage {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
}

export interface RagSettings {
    enabled: boolean
    include_web: boolean
    include_files: boolean
    include_db: boolean
    file_roots: string
    file_extensions: string
    embedding_model: string
    top_k: number
    max_files: number
    chunk_chars: number
    chunk_overlap: number
    db_type: "sqlite" | "postgres" | "mysql"
    db_connection: string
    db_table: string
    db_text_columns: string
}

// ChatMessage: a message in the chat, which includes the task, answer, and steps taken by the agent
export interface RetrievedDocument {
    doc_id: number
    filename: string
    relevance_score: number
    chunk_count?: number
}

export interface ChatMessage {
    id: string
    session_id: string
    task: string
    answer: string
    steps: AgentStep[]
    duration_seconds: number
    timestamp: string
    critique_performed: boolean
    critique_feedback?: string | null
    critique_suggestions: string[]
    execution_mode?: "chat" | "agent"
    model_used?: string
    token_usage?: TokenUsage
    retrieved_documents?: RetrievedDocument[]
}

// Chat: chats grouped by Today/Yesterday/Lastweek
export interface Chat {
    id: string
    title: string
    messages: ChatMessage[]
    timestamp: string
}

// Tools: model settings + toggle agents on/off + per-agent model selection
export interface ToolSettings {
    model: string
    temperature: number
    agentModelSettings: AgentModelSettings
    conversationModel?: string | null
    sessionId?: string | null
    autoCritique: boolean
    showAgentActivity: boolean
    userName: string
    ragSettings: RagSettings
    agentMemorySettings: AgentMemorySettings
}
