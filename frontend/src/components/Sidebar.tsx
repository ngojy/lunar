import type { Chat } from "../types"

type Page = "welcome" | "chat" | "search" | "chats" | "tools"

interface Props {
    chats: Chat[]
    activeChatId: string
    activePage: Page
    onNewChat: () => void
    onSelectChat: (id: string) => void
    onDeleteChat: (id: string) => void
    onPageChange: (page: Page) => void
    collapsed: boolean
    onToggleCollapsed: () => void
    toolsOpen: boolean
}

export default function Sidebar({
    chats,
    activeChatId,
    activePage,
    onNewChat,
    onSelectChat,
    onDeleteChat,
    onPageChange,
    collapsed,
    onToggleCollapsed,
    toolsOpen,
}: Props) {
    function handleSelectChat(id: string) {
        onSelectChat(id)
        onPageChange("chat")
    }

    return (
        <div className={`sidebar ${collapsed ? "collapsed" : ""}`}>
            <div className="sidebar-topbar">
                <div className="sidebar-logo">
                    <span className="app-name">{collapsed ? "🌙" : "Lunar"}</span>
                </div>
                <button className="sidebar-collapse-btn" onClick={onToggleCollapsed} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand" : "Collapse"}>
                    {collapsed ? "›" : "‹"}
                </button>
            </div>

            {!collapsed && (
                <>
                    <button className="new-chat-btn" onClick={onNewChat}>
                        <span>+</span> New Chat
                    </button>

                    <nav className="sidebar-nav">
                        <button
                            className={`nav-item ${activePage === "search" ? "active" : ""}`}
                            onClick={() => onPageChange("search")}
                        >
                            <span>🔍︎</span> Search
                        </button>
                        <button
                            className={`nav-item ${activePage === "chats" ? "active" : ""}`}
                            onClick={() => onPageChange("chats")}
                        >
                            <span>🗪</span> Chats
                        </button>
                        <button
                            className={`nav-item ${activePage === "tools" || toolsOpen ? "active" : ""}`}
                            onClick={() => onPageChange("tools")}
                        >
                            <span>🛠</span> Tools
                        </button>
                    </nav>

                    <div className="sidebar-divider" />

                    <div className="sidebar-section-label">Recent</div>
                    <div className="sidebar-chats">
                        {chats.length === 0 && (
                            <div className="sidebar-empty">No chats yet</div>
                        )}
                        {[...chats].reverse().map((chat) => (
                            <div
                                key={chat.id}
                                className={`sidebar-chat-item ${chat.id === activeChatId && activePage === "chat" ? "active" : ""}`}
                                onClick={() => handleSelectChat(chat.id)}
                            >
                                <span className="sidebar-chat-title">{chat.title}</span>
                                <button
                                    className="sidebar-delete-btn"
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        onDeleteChat(chat.id)
                                    }}
                                >
                                    ✕
                                </button>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </div>
    )
}