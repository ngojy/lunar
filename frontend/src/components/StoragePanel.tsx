import { useEffect, useState, useRef } from "react"

interface StorageFile {
    name: string
    size: number
    uploadedAt: string
    type: string
    path: string
    doc_id?: number
}

interface Props {
    onClose?: () => void
}

export default function StoragePanel({ onClose: _onClose }: Props) {
    const [files, setFiles] = useState<StorageFile[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [search, setSearch] = useState("")
    const [filterType, setFilterType] = useState<string>("all")
    const [filterDate, setFilterDate] = useState<string>("all")
    const [uploading, setUploading] = useState(false)
    const [deleteConfirm, setDeleteConfirm] = useState<{ file: StorageFile; show: boolean }>({ file: null as any, show: false })
    const fileInputRef = useRef<HTMLInputElement>(null)

    // Fetch files on component mount
    useEffect(() => {
        fetchFiles()
    }, [])

    async function fetchFiles() {
        setLoading(true)
        setError(null)
        try {
            const response = await fetch("/api/storage/files")
            if (!response.ok) throw new Error("Failed to fetch files")
            const data = await response.json()
            setFiles(data.files || [])
        } catch (err) {
            setError(err instanceof Error ? err.message : "Unknown error")
        } finally {
            setLoading(false)
        }
    }

    async function handleDelete(file: StorageFile) {
        try {
            const response = await fetch("/api/storage/files", {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: file.path, doc_id: file.doc_id }),
            })
            if (!response.ok) throw new Error("Failed to delete file")
            setFiles(files.filter((f) => f.path !== file.path))
            setDeleteConfirm({ file: null as any, show: false })
        } catch (err) {
            setError(err instanceof Error ? err.message : "Delete failed")
        }
    }

    async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
        const fileList = event.currentTarget.files
        if (!fileList) return

        setUploading(true)
        setError(null)

        try {
            for (const file of Array.from(fileList)) {
                const formData = new FormData()
                formData.append("file", file)

                const response = await fetch("/api/storage/upload", {
                    method: "POST",
                    body: formData,
                })
                if (!response.ok) throw new Error(`Failed to upload ${file.name}`)
            }
            // Refresh file list after upload
            await fetchFiles()
        } catch (err) {
            setError(err instanceof Error ? err.message : "Upload failed")
        } finally {
            setUploading(false)
            // Reset file input using ref
            if (fileInputRef.current) {
                fileInputRef.current.value = ""
            }
        }
    }

    // Filter and search logic
    const filteredFiles = files.filter((file) => {
        const matchesSearch = !search || file.name.toLowerCase().includes(search.toLowerCase())

        const matchesType =
            filterType === "all" || file.type === filterType || file.name.endsWith(filterType)

        const matchesDate = filterDate === "all" || isRecentFile(file.uploadedAt, filterDate)

        return matchesSearch && matchesType && matchesDate
    })

    const uniqueTypes = Array.from(new Set(files.map((f) => f.type))).sort()

    function isRecentFile(dateStr: string, filter: string): boolean {
        const fileDate = new Date(dateStr)
        const now = new Date()
        const diffMs = now.getTime() - fileDate.getTime()
        const diffDays = diffMs / (1000 * 60 * 60 * 24)

        switch (filter) {
            case "today":
                return diffDays < 1
            case "week":
                return diffDays < 7
            case "month":
                return diffDays < 30
            default:
                return true
        }
    }

    function formatFileSize(bytes: number): string {
        if (bytes === 0) return "0 B"
        const k = 1024
        const sizes = ["B", "KB", "MB", "GB"]
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
    }

    function formatDate(dateStr: string): string {
        const date = new Date(dateStr)
        return date.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: date.getFullYear() !== new Date().getFullYear() ? "numeric" : undefined,
        })
    }

    return (
        <div className="storage-panel">
            <div className="storage-header">
                <h3 className="storage-title">File Storage</h3>
                <p className="storage-subtitle">Manage uploaded documents and files (.txt, .md, .pdf, .docx, .doc, .xlsx, .csv)</p>
            </div>

            {/* Upload Section */}
            <div className="storage-upload-section">
                <label className="storage-upload-btn">
                    <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        onChange={handleUpload}
                        disabled={uploading}
                        style={{ display: "none" }}
                        accept=".txt,.md,.pdf,.docx,.doc,.xlsx,.csv"
                    />
                    <span>{uploading ? "Uploading..." : "+ Upload Files"}</span>
                </label>
            </div>

            {/* Search and Filter Section */}
            <div className="storage-controls">
                <input
                    type="text"
                    placeholder="Search files..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="storage-search"
                />

                <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="storage-filter">
                    <option value="all">All Types</option>
                    {uniqueTypes.map((type) => (
                        <option key={type} value={type}>
                            {type || "No Extension"}
                        </option>
                    ))}
                </select>

                <select value={filterDate} onChange={(e) => setFilterDate(e.target.value)} className="storage-filter">
                    <option value="all">All Dates</option>
                    <option value="today">Today</option>
                    <option value="week">This Week</option>
                    <option value="month">This Month</option>
                </select>
            </div>

            {/* Error Display */}
            {error && <div className="storage-error">{error}</div>}

            {/* Files List */}
            <div className="storage-list">
                {loading && <div className="storage-loading">Loading files...</div>}

                {!loading && filteredFiles.length === 0 && (
                    <div className="storage-empty">
                        {files.length === 0 ? "No files uploaded yet" : "No files match your search"}
                    </div>
                )}

                {!loading && filteredFiles.length > 0 && (
                    <>
                        <div className="storage-list-header">
                            <div className="storage-col-name">Name</div>
                            <div className="storage-col-size">Size</div>
                            <div className="storage-col-type">Type</div>
                            <div className="storage-col-date">Uploaded</div>
                            <div className="storage-col-action"></div>
                        </div>

                        {filteredFiles.map((file, idx) => (
                            <div key={idx} className="storage-list-row">
                                <div className="storage-col-name" title={file.name}>
                                    {file.name}
                                </div>
                                <div className="storage-col-size">{formatFileSize(file.size)}</div>
                                <div className="storage-col-type">{file.type || "—"}</div>
                                <div className="storage-col-date">{formatDate(file.uploadedAt)}</div>
                                <div className="storage-col-action">
                                    <button
                                        className="storage-delete-btn"
                                        onClick={() => setDeleteConfirm({ file, show: true })}
                                        title="Delete file"
                                        aria-label="Delete file"
                                    >
                                        🗑
                                    </button>
                                </div>
                            </div>
                        ))}

                        <div className="storage-list-footer">
                            Showing {filteredFiles.length} of {files.length} files
                        </div>
                    </>
                )}
            </div>

            {/* Delete Confirmation Modal */}
            {deleteConfirm.show && (
                <div className="storage-modal-overlay" onClick={() => setDeleteConfirm({ file: null as any, show: false })}>
                    <div className="storage-modal" onClick={(e) => e.stopPropagation()}>
                        <h3 className="storage-modal-title">Confirm Deletion</h3>
                        <p className="storage-modal-message">
                            Are you sure you want to delete <strong>"{deleteConfirm.file?.name}"</strong>?
                        </p>
                        {deleteConfirm.file?.doc_id && (
                            <p className="storage-modal-warning">
                                ⚠️ This file has been indexed in the RAG database. Deleting it will remove both the file and all its associated embeddings and search data.
                            </p>
                        )}
                        <div className="storage-modal-actions">
                            <button
                                className="storage-modal-cancel"
                                onClick={() => setDeleteConfirm({ file: null as any, show: false })}
                            >
                                Cancel
                            </button>
                            <button
                                className="storage-modal-confirm"
                                onClick={() => handleDelete(deleteConfirm.file)}
                            >
                                Delete File & RAG Data
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
