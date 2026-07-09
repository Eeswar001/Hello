const chatWindow = document.getElementById("chatWindow");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const clearChat = document.getElementById("clearChat");
const downloadChat = document.getElementById("downloadChat");
const stopChat = document.getElementById("stopChat");
const sendChat = document.getElementById("sendChat");

const historyKey = "gameverse-chat";
const sessionKey = "gameverse-chat-session";

let history = JSON.parse(localStorage.getItem(historyKey) || "[]");
let sessionId = localStorage.getItem(sessionKey) || crypto.randomUUID();
let activeController = null;

localStorage.setItem(sessionKey, sessionId);

if (window.marked) {
    marked.setOptions({
        breaks: true,
        highlight(code, language) {
            if (!window.hljs) return code;
            if (language && hljs.getLanguage(language)) {
                return hljs.highlight(code, { language }).value;
            }
            return hljs.highlightAuto(code).value;
        }
    });
}

function saveHistory() {
    localStorage.setItem(historyKey, JSON.stringify(history.slice(-80)));
}

function formatTime(value) {
    return new Intl.DateTimeFormat(undefined, {
        hour: "numeric",
        minute: "2-digit"
    }).format(new Date(value));
}

function renderMarkdown(value) {
    const raw = window.marked ? marked.parse(value || "") : escapeHtml(value || "").replace(/\n/g, "<br>");
    return window.DOMPurify ? DOMPurify.sanitize(raw) : raw;
}

function renderMessage(item, index) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${item.role}`;
    wrapper.dataset.index = String(index);

    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = `${item.role === "assistant" ? "GameVerse AI" : "You"} - ${formatTime(item.timestamp || Date.now())}`;
    wrapper.appendChild(meta);

    const content = document.createElement("div");
    content.className = "message-content";
    content.innerHTML = item.role === "assistant"
        ? renderMarkdown(item.content)
        : escapeHtml(item.content).replace(/\n/g, "<br>");
    wrapper.appendChild(content);

    if (item.role === "assistant" && item.content) {
        wrapper.appendChild(messageTools(item));
    }

    chatWindow.appendChild(wrapper);
    enhanceCodeBlocks(wrapper);
}

function messageTools(item) {
    const tools = document.createElement("div");
    tools.className = "message-tools";

    const copy = document.createElement("button");
    copy.className = "btn btn-outline-light btn-sm";
    copy.type = "button";
    copy.textContent = "Copy";
    copy.addEventListener("click", () => navigator.clipboard.writeText(item.content));
    tools.appendChild(copy);

    const regenerate = document.createElement("button");
    regenerate.className = "btn btn-outline-light btn-sm";
    regenerate.type = "button";
    regenerate.textContent = "Regenerate";
    regenerate.addEventListener("click", () => regenerateLastResponse());
    tools.appendChild(regenerate);

    return tools;
}

function enhanceCodeBlocks(scope) {
    if (window.hljs) {
        scope.querySelectorAll("pre code").forEach((block) => hljs.highlightElement(block));
    }
    scope.querySelectorAll("pre").forEach((pre) => {
        if (pre.querySelector(".code-copy")) return;
        const button = document.createElement("button");
        button.className = "code-copy";
        button.type = "button";
        button.textContent = "Copy";
        button.addEventListener("click", () => navigator.clipboard.writeText(pre.innerText.replace(/^Copy\s*/, "")));
        pre.appendChild(button);
    });
}

function render() {
    chatWindow.innerHTML = "";
    if (!history.length) {
        renderMessage({
            role: "assistant",
            content: "Ask me anything about games, hardware, coding, tech, or whatever you are working through. I will keep the conversation in mind as we go.",
            timestamp: Date.now()
        }, 0);
    } else {
        history.forEach(renderMessage);
    }
    scrollToBottom();
}

function escapeHtml(value) {
    return value.replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    }[char]));
}

function scrollToBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function setGenerating(isGenerating) {
    stopChat.disabled = !isGenerating;
    sendChat.disabled = isGenerating;
    chatInput.disabled = isGenerating;
}

function createAssistantShell() {
    const item = { role: "assistant", content: "", timestamp: Date.now() };
    history.push(item);
    const index = history.length - 1;
    renderMessage(item, index);
    scrollToBottom();
    return { item, index };
}

function updateAssistantMessage(index, content) {
    const wrapper = chatWindow.querySelector(`[data-index="${index}"]`);
    if (!wrapper) return;
    const contentNode = wrapper.querySelector(".message-content");
    contentNode.innerHTML = content
        ? renderMarkdown(content)
        : "<span class=\"typing-dots\">Thinking<span>.</span><span>.</span><span>.</span></span>";
    enhanceCodeBlocks(wrapper);
    scrollToBottom();
}

async function streamAssistantResponse(message) {
    activeController = new AbortController();
    setGenerating(true);
    const assistant = createAssistantShell();

    try {
        const priorHistory = history.slice(0, -2).map(({ role, content }) => ({ role, content }));
        const response = await fetch("/api/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId, message, history: priorHistory }),
            signal: activeController.signal
        });

        if (!response.ok || !response.body) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.error || "Chat request failed");
        }

        await readEventStream(response.body, {
            token(payload) {
                assistant.item.content += payload.content || "";
                updateAssistantMessage(assistant.index, assistant.item.content);
            },
            meta(payload) {
                if (payload.session_id) {
                    sessionId = payload.session_id;
                    localStorage.setItem(sessionKey, sessionId);
                }
            },
            error(payload) {
                throw new Error(payload.error || "The AI provider returned an error");
            }
        });

        if (!assistant.item.content.trim()) {
            throw new Error("The AI provider returned an empty response");
        }
    } catch (error) {
        if (error.name === "AbortError") {
            assistant.item.content = assistant.item.content.trim() || "Generation stopped.";
        } else {
            assistant.item.content = `Request failed: ${error.message}`;
        }
        updateAssistantMessage(assistant.index, assistant.item.content);
    } finally {
        activeController = null;
        setGenerating(false);
        saveHistory();
        render();
        chatInput.focus();
    }
}

async function readEventStream(body, handlers) {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";
        for (const eventText of events) {
            const event = parseSseEvent(eventText);
            if (event && handlers[event.event]) {
                handlers[event.event](event.data);
            }
        }
    }
}

function parseSseEvent(text) {
    const lines = text.split("\n");
    const eventLine = lines.find((line) => line.startsWith("event:"));
    const dataLine = lines.find((line) => line.startsWith("data:"));
    if (!eventLine || !dataLine) return null;
    try {
        return {
            event: eventLine.replace("event:", "").trim(),
            data: JSON.parse(dataLine.replace("data:", "").trim())
        };
    } catch (error) {
        return null;
    }
}

chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = chatInput.value.trim();
    if (!message || activeController) return;

    history.push({ role: "user", content: message, timestamp: Date.now() });
    chatInput.value = "";
    saveHistory();
    render();
    await streamAssistantResponse(message);
});

stopChat.addEventListener("click", () => {
    if (activeController) activeController.abort();
});

function regenerateLastResponse() {
    if (activeController) return;
    let assistantIndex = history.length - 1;
    while (assistantIndex >= 0 && history[assistantIndex].role !== "assistant") {
        assistantIndex -= 1;
    }
    if (assistantIndex < 0) return;

    let userIndex = assistantIndex - 1;
    while (userIndex >= 0 && history[userIndex].role !== "user") {
        userIndex -= 1;
    }
    if (userIndex < 0) return;

    const message = history[userIndex].content;
    history = history.slice(0, assistantIndex);
    saveHistory();
    render();
    streamAssistantResponse(message);
}

chatInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        chatForm.requestSubmit();
    }
});

clearChat.addEventListener("click", () => {
    history = [];
    sessionId = crypto.randomUUID();
    localStorage.setItem(sessionKey, sessionId);
    saveHistory();
    render();
});

downloadChat.addEventListener("click", () => {
    const text = history.map((item) => {
        const time = item.timestamp ? ` [${new Date(item.timestamp).toLocaleString()}]` : "";
        return `${item.role.toUpperCase()}${time}: ${item.content}`;
    }).join("\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "gameverse-chat.txt";
    link.click();
    URL.revokeObjectURL(url);
});

render();
