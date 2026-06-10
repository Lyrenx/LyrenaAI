let currentStatus = "standby";
let canvas = null;
let ctx = null;
let angle = 0;
let animationFrameId = null;
let pageReady = false;
let dragArmed = false;

function setAiState(state, text) {
    if (!pageReady) return;

    currentStatus = state || "standby";
    const statusText = document.getElementById("status-text");
    if (!statusText) return;

    const stateMap = {
        listening: { label: "LYRENA LISTENING", color: "#2fe37b" },
        thinking: { label: "LYRENA THINKING", color: "#00ffcc" },
        speaking: { label: "LYRENA SPEAKING", color: "#ff3333" },
        standby: { label: "LYRENA STANDBY", color: "#00ffcc" },
    };

    const current = stateMap[currentStatus] || stateMap.standby;
    statusText.innerText = (text || current.label).toUpperCase();
    statusText.style.color = current.color;
}

function updateTelemetry(cpu, ram, cpuTemp, ramUsed, ramTotal) {
    if (!pageReady) return;

    const cpuText = document.getElementById("cpu-text");
    const cpuBar = document.getElementById("cpu-bar");
    const ramText = document.getElementById("ram-text");
    const ramBar = document.getElementById("ram-bar");
    const tempText = document.getElementById("cpu-temp-text");
    const ramUsageText = document.getElementById("ram-usage-text");
    const summary = document.getElementById("system-summary");

    const cpuValue = Number.isFinite(cpu) ? cpu : 0;
    const ramValue = Number.isFinite(ram) ? ram : 0;

    if (cpuText) cpuText.innerText = cpuValue.toFixed(0) + "%";
    if (cpuBar) cpuBar.style.width = Math.max(0, Math.min(100, cpuValue)) + "%";
    if (ramText) ramText.innerText = ramValue.toFixed(0) + "%";
    if (ramBar) ramBar.style.width = Math.max(0, Math.min(100, ramValue)) + "%";
    if (tempText) tempText.innerText = Number.isFinite(cpuTemp) ? ("TEMP " + cpuTemp.toFixed(0) + "C") : "TEMP --";

    if (ramUsageText) {
        const used = Number.isFinite(ramUsed) ? ramUsed.toFixed(1) : "--";
        const total = Number.isFinite(ramTotal) ? ramTotal.toFixed(1) : "--";
        ramUsageText.innerText = used + " / " + total + " GB";
    }

    if (summary) {
        summary.innerText = [
            "CPU " + cpuValue.toFixed(0) + "%",
            "RAM " + ramValue.toFixed(0) + "%",
            Number.isFinite(cpuTemp) ? ("SICAKLIK " + cpuTemp.toFixed(0) + "C") : "SICAKLIK --",
        ].join("\n");
    }
}

function showWeather(city, temp, desc) {
    if (!pageReady) return;

    const wp = document.getElementById("weather-panel");
    if (!wp) return;

    wp.classList.remove("hidden");
    const cityEl = document.getElementById("weather-city");
    const tempEl = document.getElementById("weather-temp");
    const descEl = document.getElementById("weather-desc");

    if (cityEl) cityEl.innerText = (city || "--").toString();
    if (tempEl) tempEl.innerText = Number.isFinite(temp) ? (temp.toFixed(0) + "C") : "--C";
    if (descEl) descEl.innerText = (desc || "SCANNING...").toUpperCase();
}

function setPanelMode(mode) {
    if (!pageReady) return;

    const left = document.getElementById("left-hud");
    const right = document.getElementById("right-hud");
    const weather = document.getElementById("weather-panel");

    if (!left || !right || !weather) return;

    if (mode === "weather") {
        left.classList.remove("hidden");
        right.classList.add("hidden");
        weather.classList.remove("hidden");
    } else if (mode === "system") {
        left.classList.add("hidden");
        right.classList.remove("hidden");
        weather.classList.add("hidden");
    } else if (mode === "all") {
        left.classList.remove("hidden");
        right.classList.remove("hidden");
    } else {
        left.classList.add("hidden");
        right.classList.add("hidden");
        weather.classList.add("hidden");
    }
}

function toggleUIMode(isFullscreen) {
    if (!pageReady) return;

    const container = document.getElementById("app-container");
    const left = document.getElementById("left-hud");
    const right = document.getElementById("right-hud");

    if (!container || !left || !right) return;

    if (isFullscreen) {
        container.className = "fullscreen-mode";
        left.classList.remove("hidden");
        right.classList.remove("hidden");
    } else {
        container.className = "mini-mode";
        left.classList.add("hidden");
        right.classList.add("hidden");
    }
}

function draw() {
    if (!canvas || !ctx) {
        animationFrameId = requestAnimationFrame(draw);
        return;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const radius = 82;

    angle += 0.03;
    ctx.beginPath();

    const palette = {
        listening: "rgba(47, 227, 123, 0.85)",
        thinking: "rgba(0, 255, 204, 0.7)",
        speaking: "rgba(255, 51, 51, 0.82)",
        standby: "rgba(0, 255, 204, 0.35)",
    };

    const numLines = currentStatus === "speaking" ? 12 : currentStatus === "listening" ? 10 : 6;
    const stroke = palette[currentStatus] || palette.standby;
    ctx.strokeStyle = stroke;
    ctx.lineWidth = currentStatus === "speaking" ? 2.2 : 1.8;

    for (let j = 0; j < numLines; j++) {
        let started = false;
        for (let i = 0; i <= 360; i += 2) {
            const rad = (i * Math.PI) / 180;
            let offset = 0;

            if (currentStatus === "listening") {
                offset = Math.sin(angle + i * 0.05 + j) * 10;
            } else if (currentStatus === "thinking") {
                offset = Math.cos(angle * 2 + i * 0.1) * 5;
            } else if (currentStatus === "speaking") {
                offset = Math.sin(angle * 5 + i * 0.2) * (Math.random() * 16 + 4);
            } else {
                offset = Math.sin(angle + i * 0.02 + j) * 2;
            }

            const ringAngle = rad + (currentStatus === "thinking" ? angle * 0.5 : 0);
            const r = radius + offset;
            const x = cx + Math.cos(ringAngle) * r;
            const y = cy + Math.sin(ringAngle) * r;

            if (!started) {
                ctx.moveTo(x, y);
                started = true;
            } else {
                ctx.lineTo(x, y);
            }
        }
    }

    ctx.stroke();

    const clockEl = document.getElementById("digital-clock");
    if (clockEl) {
        const d = new Date();
        clockEl.innerText = d.toTimeString().split(" ")[0];
    }

    animationFrameId = requestAnimationFrame(draw);
}

function initQWebChannel() {
    if (typeof qt !== "undefined" && qt.webChannelTransport) {
        new QWebChannel(qt.webChannelTransport, function (channel) {
            window.pyBridge = channel.objects.pyBridge;
        });
    }
}

function triggerWake() {
    if (window.pyBridge) {
        window.pyBridge.trigger_manual_wake();
    }
}

function showTriggerButton(mode) {
    const btn = document.getElementById("re-listen-btn");
    if (!btn) return;

    btn.className = (mode === "mini") ? "tiny-btn" : "full-btn";
    btn.classList.remove("hidden");
}

function hideTriggerButtons() {
    const btn = document.getElementById("re-listen-btn");
    if (btn) {
        btn.classList.add("hidden");
    }
}

function bindDrag() {
    const container = document.getElementById("app-container");
    if (!container) return;

    let dragging = false;

    container.addEventListener("mousedown", function (ev) {
        if (ev.button !== 0) return;
        if (ev.target.closest("button")) return;
        dragging = true;
        if (window.pyBridge) {
            window.pyBridge.startDrag(ev.screenX, ev.screenY);
        }
    });

    window.addEventListener("mousemove", function (ev) {
        if (!dragging) return;
        if (window.pyBridge) {
            window.pyBridge.dragTo(ev.screenX, ev.screenY);
        }
    });

    window.addEventListener("mouseup", function () {
        if (!dragging) return;
        dragging = false;
        if (window.pyBridge) {
            window.pyBridge.endDrag();
        }
    });
}

document.addEventListener("DOMContentLoaded", function () {
    canvas = document.getElementById("lyrena-ring");
    if (canvas) {
        ctx = canvas.getContext("2d");
    }

    pageReady = true;
    initQWebChannel();
    bindDrag();
    draw();
    toggleUIMode(false);
    setPanelMode("none");
});
