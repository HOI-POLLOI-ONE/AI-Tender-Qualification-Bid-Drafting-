document.addEventListener("DOMContentLoaded", () => {

    window.generateDraft = async function() {
        const result = await generateDraftAPI({});
        document.getElementById("proposalText").value =
            result?.draft || "Draft generated.";
    };

    window.askAI = async function() {
        const input = document.getElementById("chatInput");
        const chatBox = document.getElementById("chatBox");

        const question = input.value.trim();
        if (!question) return;

        addMessage(chatBox, question, "user");

        const response = await askCopilotAPI(question);
        addMessage(chatBox, response?.answer || "No response", "ai");

        input.value = "";
        chatBox.scrollTop = chatBox.scrollHeight;
    };
});

function addMessage(container, text, type) {
    const div = document.createElement("div");
    div.className = type === "user" ? "chat-user" : "chat-ai";
    div.innerText = text;
    container.appendChild(div);
}
