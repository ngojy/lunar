import { useState } from "react"
import type { Chat } from "../types"

type GroupFilter = "all" | "today" | "yesterday" | "last7" | "last30"

interface Props {
    chats: Chat[]
    activeChatId: string
    onSelectChat: (id: string) => void
    onDeleteChat: (id: string) => void
}


function filterChats(chats: Chat[], filter: GroupFilter): Chat[] {
    const now       = new Date()
    const today     = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    const last7     = new Date(today)
    last7.setDate(last7.getDate() - 7)
    const last30    = new Date(today)
    last30.setDate(last30.getDate() - 30)

    return [...chats].reverse().filter((chat) => {
        const date = new Date(chat.timestamp)
        if (filter === "all")       return true
        if (filter === "today")     return date >= today
        if (filter === "yesterday") return date >= yesterday && date < today
        if (filter === "last7")     return date >= last7
        if (filter === "last30")    return date >= last30
        return true
    })
}

function groupChats(chats: Chat[]): Record<string, Chat[]> {
    const now       = new Date()
    const today     = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    const last7     = new Date(today)
    last7.setDate(last7.getDate() - 7)
    const last30    = new Date(today)
    last30.setDate(last30.getDate() - 30)

    const groups: Record<string, Chat[]> = {
        "Today":        [],
        "Yesterday":    [],
        "Last 7 Days":  [],
        "Last 30 Days": [],
        "Older":        [],
    }

    for (const chat of chats) {
        const date = new Date(chat.timestamp)
        if (date >= today)          groups["Today"].push(chat)
        else if (date >= yesterday) groups["Yesterday"].push(chat)
        else if (date >= last7)     groups["Last 7 Days"].push(chat)
        else if (date >= last30)    groups["Last 30 Days"].push(chat)
        else                        groups["Older"].push(chat)
    }

    return groups
}

function formatTime(iso: string) {
    return new Date(iso).toLocaleTimeString([], {
        hour: "2-digit", minute: "2-digit",
    })
}

function getPreview(chat: Chat): string {
    if (chat.messages.length === 0) return "No messages yet"
    const first = chat.messages[0]
    return first.task.length > 80
        ? first.task.slice(0, 80) + "…"
        : first.task
}


export default function ChatsPage({
    chats,
    activeChatId,
    onSelectChat,
    onDeleteChat,
}: Props) {
    const [filter, setFilter] = useState<GroupFilter>("all")

    const filtered = filterChats(chats, filter)
    const groups   = groupChats(filtered)

    return (
        <div className="side-panel">
            <div className="side-panel-header">
                <span>🗪</span> Chats
            </div>

            {/* Grouping dropdown */}
            <div className="chats-filter-row">
                <label className="chats-filter-label">Group by</label>
                <select
                    className="chats-filter-select"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value as GroupFilter)}
                >
                    <option value="all">All</option>
                    <option value="today">Today</option>
                    <option value="yesterday">Yesterday</option>
                    <option value="last7">Last 7 Days</option>
                    <option value="last30">Last 30 Days</option>
                </select>
            </div>

            {/* Empty state */}
            {filtered.length === 0 && (
                <div className="side-panel-empty">
                    No chats found for this time period.
                </div>
            )}

            {/* Grouped chats */}
            <div className="history-groups">
                {Object.entries(groups)
                    .filter(([, chats]) => chats.length > 0)
                    .map(([label, groupChats]) => (
                        <div key={label} className="history-group">
                            <div className="history-group-label">{label}</div>

                            {groupChats.map((chat) => (
                                <button
                                    key={chat.id}
                                    className={`history-item ${chat.id === activeChatId ? "active" : ""}`}
                                    onClick={() => onSelectChat(chat.id)}
                                >
                                    <div className="history-item-top">
                                        <span className="history-item-title">
                                            {chat.title}
                                        </span>
                                        <span className="history-item-time">
                                            {formatTime(chat.timestamp)}
                                        </span>
                                    </div>
                                    <div className="history-item-preview">
                                        {getPreview(chat)}
                                    </div>
                                    <button
                                        className="history-delete-btn"
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            onDeleteChat(chat.id)
                                        }}
                                    >
                                        ✕
                                    </button>
                                </button>
                            ))}
                        </div>
                    ))}
            </div>
        </div>
    )
}