import { ChatMessage } from "../types"

interface Props {
    history: ChatMessage[]
    onSelect: (msg: ChatMessage) => void
    onClear: () => void
}

function formatTime(iso: string) {
    return new Date(iso).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
    })
}


// onSelect and onClear: callback functions passed in from parent
// [...history].reverse(): spread the array into a new one before reversing, so we don't mess with the og one
// item.task.slice(0, 48) + "...": truncates long questions so they fit in the panel
export default function HistoryPanel({ history, onSelect, onClear }: Props) {
    return (
        <div className="history-panel">
            <div className="panel-label">
                History
                {history.length > 0 && (
                <button className="clear-btn" onClick={onClear}>Clear</button>
                )}
            </div>

            <div className="history-list">
                {history.length === 0 && (
                    <div className="empty-state small">
                        <p>Past conversations will appear here.</p>
                    </div>
                )}

                {[...history].reverse().map((item) => (
                    <button
                        key={item.id}
                        className="history-item"
                        onClick={() => onSelect(item)}
                    >
                        <span className="history-task">
                            {item.task.length > 48
                                ? item.task.slice(0, 48) + "…"
                                : item.task}
                        </span>
                        <span className="history-time">{formatTime(item.timestamp)}</span>
                    </button>
                ))}
            </div>
        </div>
    )
}