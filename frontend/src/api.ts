import axios from "axios"
import type { ChatMessage, AgentModelSettings, RagSettings } from "./types"
import { saveAvailableModels } from "./modelSettings"

const api = axios.create({
    baseURL: "http://localhost:8000",
})


// listAvailableModels: GET /models, fetches list of available models from backend
export async function listAvailableModels(): Promise<string[]> {
    try {
        const res = await api.get<{ models: string[] }>("/models")
        const models = res.data.models || []
        saveAvailableModels(models)
        return models
    } catch (error) {
        console.warn("Failed to fetch available models:", error)
        return []
    }
}


// sendMessage: POST /chat, sends user message with model and agent settings, gets full agent response
export async function sendMessage(
    message: string,
    executionMode: "chat" | "agent" = "chat",
    model: string | null | undefined = null,
    temperature: number = 0,
    userName: string = "",
    agentModelSettings: AgentModelSettings = {},
    ragSettings: RagSettings | undefined = undefined,
    sessionId: string | null | undefined = null,
    autoCritique: boolean = true,
    requestCritique: boolean = false,
): Promise<ChatMessage> {
    const payload: any = {
        message,
        execution_mode: executionMode,
        temperature,
        user_name: userName,
        agent_model_settings: agentModelSettings,
        rag_settings: ragSettings,
        auto_critique: autoCritique,
        request_critique: requestCritique,
    }

    // Only include model if explicitly provided
    if (model) {
        payload.model = model
    }
    
    // Include session_id if provided
    if (sessionId) {
        payload.session_id = sessionId
    }

    const res = await api.post<ChatMessage>("/chat", payload)
    return res.data
}


// Stream event types
export type StreamEventType = "step" | "token" | "done" | "error"

export interface StreamEvent {
    type: StreamEventType
    agent?: string
    message?: string
    timestamp?: string
    content?: string
    session_id?: string
    duration_seconds?: number
    critique_performed?: boolean
    critique_feedback?: string
    critique_suggestions?: string[]
    execution_mode?: string
    model_used?: string
    retrieved_documents?: Array<{
        doc_id: number
        filename: string
        relevance_score: number
        chunk_count?: number
    }>
    token_usage?: {
        prompt_tokens: number
        completion_tokens: number
        total_tokens: number
    }
}

// sendMessageStream: POST /chat/stream, streaming endpoint for real-time responses
export async function sendMessageStream(
    message: string,
    executionMode: "chat" | "agent" = "chat",
    model: string | null | undefined = null,
    temperature: number = 0,
    userName: string = "",
    agentModelSettings: AgentModelSettings = {},
    ragSettings: RagSettings | undefined = undefined,
    sessionId: string | null | undefined = null,
    autoCritique: boolean = true,
    requestCritique: boolean = false,
    onEvent: (event: StreamEvent) => void
): Promise<void> {
    const payload: any = {
        message,
        execution_mode: executionMode,
        temperature,
        user_name: userName,
        agent_model_settings: agentModelSettings,
        rag_settings: ragSettings,
        auto_critique: autoCritique,
        request_critique: requestCritique,
    }

    if (model) {
        payload.model = model
    }

    if (sessionId) {
        payload.session_id = sessionId
    }

    try {
        console.log("[Stream] Starting stream request to /chat/stream", { payload })
        const response = await fetch("http://localhost:8000/chat/stream", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        })

        console.log("[Stream] Response status:", response.status, response.statusText)

        if (!response.ok) {
            const errorText = await response.text()
            console.error("[Stream] Error response:", errorText)
            throw new Error(`Stream error: ${response.statusText} - ${errorText}`)
        }

        const reader = response.body?.getReader()
        if (!reader) {
            throw new Error("Response body not readable")
        }

        console.log("[Stream] Reader acquired, starting to read stream...")

        const decoder = new TextDecoder()
        let buffer = ""
        let eventCount = 0

        while (true) {
            const { done, value } = await reader.read()
            
            if (done) {
                console.log(`[Stream] Stream complete. Total events received: ${eventCount}`)
                break
            }

            if (value) {
                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split("\n")
                
                // Keep the last incomplete line in the buffer
                buffer = lines.pop() || ""

                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            const event = JSON.parse(line) as StreamEvent
                            eventCount++
                            console.log(`[Stream] Event #${eventCount}:`, event.type, event)
                            onEvent(event)
                        } catch (e) {
                            console.error("[Stream] Failed to parse event:", line, e)
                        }
                    }
                }
            }
        }

        // Process any remaining buffer
        if (buffer.trim()) {
            try {
                const event = JSON.parse(buffer) as StreamEvent
                eventCount++
                console.log(`[Stream] Final event #${eventCount}:`, event.type, event)
                onEvent(event)
            } catch (e) {
                console.error("[Stream] Failed to parse final event:", buffer, e)
            }
        }

        console.log(`[Stream] Stream fully processed with ${eventCount} total events`)
    } catch (error) {
        console.error("[Stream] Stream error:", error)
        throw error
    }
}


// checkHealth: GET /health, checks if backend is online
export async function checkHealth(): Promise<boolean> {
    try {
        await api.get("/health")
        return true
    } catch {
        return false
    }
}

// getSessionHistory: GET /session/{sessionId}, retrieves chat history AND title from persistent storage
export async function getSessionHistory(sessionId: string): Promise<{ title: string; messages: Array<{ role: string; content: string; timestamp?: string }> }> {
    try {
        const res = await api.get<{ session_id: string; title?: string; messages: any[] }>(`/session/${sessionId}`)
        const title = res.data.title || ""
        const messages = res.data.messages || []
        if (!messages.length) {
            return { title, messages: [] }
        }

        // Convert backend format (message_role, message_content) to simple format (role, content)
        const converted = messages.map((msg: any) => ({
            role: msg.role || msg.message_role || "user",
            content: msg.content || msg.message_content || "",
            timestamp: msg.timestamp || msg.created_at,
        }))
        return { title, messages: converted }
    } catch (error) {
        console.warn(`Failed to fetch session history for ${sessionId}:`, error)
        return { title: "", messages: [] }
    }
}

// listSessions: GET /sessions, retrieves list of all chat sessions from persistent storage
export async function listSessions(): Promise<Array<{ session_id: string; title: string; message_count: number; last_message_at?: string }>> {
    try {
        const res = await api.get<{
            sessions: Array<{ session_id: string; title: string; message_count: number; last_message_at?: string }>;
            total: number
        }>("/sessions")
        return res.data.sessions || []
    } catch (error) {
        console.warn("Failed to fetch sessions list:", error)
        return []
    }
}

// deleteChat: DELETE /session/{sessionId}, deletes a chat session from persistent storage
export async function deleteChat(sessionId: string): Promise<boolean> {
    try {
        const res = await api.delete<{ status: string; message: string }>(`/session/${sessionId}`)
        return res.data.status === "success"
    } catch (error) {
        console.warn(`Failed to delete session ${sessionId}:`, error)
        return false
    }
}