import axios from "axios"
import { ChatMessage } from "./types"

const api = axios.create({
    baseURL: "http://localhost:8000",
})


// sendMessage: POST /chat, sends user message, gets ful agent response
export async function sendMessage(message: string): Promise<ChatMessage> {
    const res = await api.post<ChatMessage>("/chat", { message })
    return res.data
}


// getHistory: GET /history, loads past conversations
export async function getHistory(): Promise<ChatMessage[]> {
    const res = await api.get<{ history: ChatMessage[] }>("/history")
    return res.data.history
}


// clearHistory: DELETE /history, wipes history
export async function clearHistory(): Promise<void> {
    await api.delete("/history")
}


// checkHealth: GET /health, checks if backend is online
export async function checkHealth(): Promise<boolean> {
    try {
        await api.get("\health")
        return true
    } catch {
        return false
    }
}