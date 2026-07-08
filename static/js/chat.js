const chatWindow = document.getElementById("chatWindow");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const clearChat = document.getElementById("clearChat");
const downloadChat = document.getElementById("downloadChat");

let history = JSON.parse(localStorage.getItem("gameverse-chat") || "[]");

function saveHistory() {
    localStorage.setItem("gameverse-chat", JSON.stringify(history));
}

function renderMessage(item) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${item.role}`;
    const content = document.createElement("div");
    content.className = "message-content";
    content.innerHTML = item.role === "assistant" && window.marked
        ? marked.parse(item.content)
        : escapeHtml(item.content).replace(/\n/g, "<br>");
    wrapper.appendChild(content);

    if (item.role === "assistant") {
        const tools = document.createElement("div");
        tools.className = "message-tools";
        const button = document.createElement("button");
        button.className = "btn btn-outline-light btn-sm";
        button.type = "button";
        button.textContent = "Copy";
        button.addEventListener("click", () => navigator.clipboard.writeText(item.content));
        tools.appendChild(button);
        wrapper.appendChild(tools);
    }
    chatWindow.appendChild(wrapper);
}

function render() {
    chatWindow.innerHTML = "";
    if (!history.length) {
        renderMessage({ role: "assistant", content: "Ask me about a game in the database, compare titles, request recommendations, or check specs." });
    } else {
        history.forEach(renderMessage);
    }
    chatWindow.scrollTop = chatWindow.scrollHeight;
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

function addTyping() {
    const typing = document.createElement("div");
    typing.className = "message assistant typing";
    typing.id = "typingIndicator";
    typing.textContent = "GameVerse AI is thinking...";
    chatWindow.appendChild(typing);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function removeTyping() {
    const typing = document.getElementById("typingIndicator");
    if (typing) typing.remove();
}

chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;
    history.push({ role: "user", content: message });
    chatInput.value = "";
    saveHistory();
    render();
    addTyping();

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, history })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Chat request failed");
        history.push({ role: "assistant", content: data.reply });
    } catch (error) {
        history.push({ role: "assistant", content: `Request failed: ${error.message}` });
    } finally {
        removeTyping();
        saveHistory();
        render();
    }
});

chatInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        chatForm.requestSubmit();
    }
});

clearChat.addEventListener("click", () => {
    history = [];
    saveHistory();
    render();
});

downloadChat.addEventListener("click", () => {
    const text = history.map((item) => `${item.role.toUpperCase()}: ${item.content}`).join("\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "gameverse-chat.txt";
    link.click();
    URL.revokeObjectURL(url);
});

render();
