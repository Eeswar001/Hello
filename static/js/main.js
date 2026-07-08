document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".game-card").forEach((card, index) => {
        card.style.animation = `riseIn .35s ease ${index * 35}ms both`;
    });
});

const style = document.createElement("style");
style.textContent = `
@keyframes riseIn {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}`;
document.head.appendChild(style);
