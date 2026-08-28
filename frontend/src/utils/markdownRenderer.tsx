import React from "react"

interface MarkdownNode {
    type: "text" | "bold" | "italic" | "code" | "header" | "list" | "paragraph" | "codeblock"
    content?: string
    children?: MarkdownNode[]
    level?: number
}

// Simple markdown parser
export function parseMarkdown(text: string): MarkdownNode[] {
    const nodes: MarkdownNode[] = []
    const lines = text.split("\n")
    let i = 0

    while (i < lines.length) {
        const line = lines[i]

        // Code blocks
        if (line.trim().startsWith("```")) {
            const codeLines: string[] = []
            i++
            while (i < lines.length && !lines[i].trim().startsWith("```")) {
                codeLines.push(lines[i])
                i++
            }
            i++ // skip closing ```
            nodes.push({
                type: "codeblock",
                content: codeLines.join("\n"),
            })
            continue
        }

        // Headers
        const headerMatch = line.match(/^(#{1,6})\s+(.+)$/)
        if (headerMatch) {
            nodes.push({
                type: "header",
                level: headerMatch[1].length,
                content: headerMatch[2],
            })
            i++
            continue
        }

        // Lists
        if (line.match(/^[-*]\s+/)) {
            const listItems: string[] = []
            while (i < lines.length && lines[i].match(/^[-*]\s+/)) {
                listItems.push(lines[i].replace(/^[-*]\s+/, ""))
                i++
            }
            nodes.push({
                type: "list",
                children: listItems.map((item) => ({ type: "text" as const, content: item })),
            })
            continue
        }

        // Paragraphs with inline formatting
        if (line.trim()) {
            nodes.push({
                type: "paragraph",
                children: parseInline(line),
            })
        }

        i++
    }

    return nodes
}

// Parse inline formatting (bold, italic, code)
function parseInline(text: string): MarkdownNode[] {
    const nodes: MarkdownNode[] = []
    let currentText = ""
    let i = 0

    while (i < text.length) {
        // Bold
        if (text[i] === "*" && text[i + 1] === "*") {
            if (currentText) {
                nodes.push({ type: "text", content: currentText })
                currentText = ""
            }
            i += 2
            let boldContent = ""
            while (i < text.length && !(text[i] === "*" && text[i + 1] === "*")) {
                boldContent += text[i]
                i++
            }
            if (i < text.length) i += 2
            nodes.push({ type: "bold", content: boldContent })
            continue
        }

        // Inline code
        if (text[i] === "`") {
            if (currentText) {
                nodes.push({ type: "text", content: currentText })
                currentText = ""
            }
            i++
            let codeContent = ""
            while (i < text.length && text[i] !== "`") {
                codeContent += text[i]
                i++
            }
            if (i < text.length) i++
            nodes.push({ type: "code", content: codeContent })
            continue
        }

        currentText += text[i]
        i++
    }

    if (currentText) {
        nodes.push({ type: "text", content: currentText })
    }

    return nodes
}

// Render markdown nodes to React components
export function renderMarkdown(nodes: MarkdownNode[]): React.ReactNode {
    return nodes.map((node, idx) => renderNode(node, idx))
}

function renderNode(node: MarkdownNode, key: number): React.ReactNode {
    switch (node.type) {
        case "header": {
            const level = node.level || 3
            const headerProps = { className: "markdown-header" }
            if (level === 1) return <h1 key={key} {...headerProps}>{node.content}</h1>
            if (level === 2) return <h2 key={key} {...headerProps}>{node.content}</h2>
            if (level === 3) return <h3 key={key} {...headerProps}>{node.content}</h3>
            if (level === 4) return <h4 key={key} {...headerProps}>{node.content}</h4>
            if (level === 5) return <h5 key={key} {...headerProps}>{node.content}</h5>
            if (level === 6) return <h6 key={key} {...headerProps}>{node.content}</h6>
            return <h3 key={key} {...headerProps}>{node.content}</h3>
        }

        case "paragraph":
            return (
                <p key={key} className="markdown-paragraph">
                    {node.children && renderMarkdown(node.children)}
                </p>
            )

        case "bold":
            return (
                <strong key={key} className="markdown-bold" style={{ fontWeight: 700, color: "#e8d5b7" }}>
                    {node.content}
                </strong>
            )

        case "italic":
            return (
                <em key={key} className="markdown-italic">
                    {node.content}
                </em>
            )

        case "code":
            return (
                <code key={key} className="markdown-code" style={{ backgroundColor: "#2a2a2a", padding: "2px 6px", borderRadius: "3px" }}>
                    {node.content}
                </code>
            )

        case "codeblock":
            return (
                <pre key={key} className="markdown-codeblock" style={{ backgroundColor: "#1a1a1a", padding: "12px", borderRadius: "4px", overflow: "auto" }}>
                    <code>{node.content}</code>
                </pre>
            )

        case "list":
            return (
                <ul key={key} className="markdown-list" style={{ marginLeft: "20px" }}>
                    {node.children?.map((item, idx) => (
                        <li key={idx} className="markdown-list-item">
                            {renderMarkdown([item])}
                        </li>
                    ))}
                </ul>
            )

        case "text":
        default:
            return <span key={key}>{node.content}</span>
    }
}
