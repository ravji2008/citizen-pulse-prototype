const STATES = [
  "Uttar Pradesh", "Maharashtra", "Bihar", "West Bengal", "Madhya Pradesh",
  "Rajasthan", "Tamil Nadu", "Karnataka", "Gujarat", "Odisha", "Kerala",
  "Assam", "Punjab", "Jharkhand", "Chhattisgarh", "Delhi",
];

const I18N = {
  en: {
    tabSubmit: "Submit Feedback", tabDashboard: "Policy Dashboard",
    labelState: "State", labelDistrict: "District / City",
    labelText: "Describe the issue",
    placeholderText: "e.g. There has been no water supply in our area for 3 days...",
    voiceBtn: "Speak", submitBtn: "Submit Feedback",
    hotspotsHeading: "Top Priority Development Hotspots",
    thState: "State", thCategory: "Category", thCount: "Complaints",
    thUrgency: "Avg Urgency", thInfra: "Infra Index", thPriority: "Priority Score",
    resultPrefix: "Analyzed:",
    tagline: "AI-powered citizen feedback aggregation for Digital Public Infrastructure planning",
  },
  hi: {
    tabSubmit: "शिकायत दर्ज करें", tabDashboard: "नीति डैशबोर्ड",
    labelState: "राज्य", labelDistrict: "जिला / शहर",
    labelText: "समस्या बताएं",
    placeholderText: "जैसे: हमारे क्षेत्र में 3 दिनों से पानी नहीं आ रहा है...",
    voiceBtn: "बोलें", submitBtn: "शिकायत भेजें",
    hotspotsHeading: "प्राथमिकता वाले विकास क्षेत्र",
    thState: "राज्य", thCategory: "श्रेणी", thCount: "शिकायतें",
    thUrgency: "औसत तात्कालिकता", thInfra: "अवसंरचना सूचकांक", thPriority: "प्राथमिकता स्कोर",
    resultPrefix: "विश्लेषण:",
    tagline: "डिजिटल सार्वजनिक अवसंरचना योजना के लिए एआई-संचालित नागरिक फीडबैक एकत्रीकरण",
  },
};

let currentLang = "en";

function setLang(lang) {
  currentLang = lang;
  const t = I18N[lang];
  document.getElementById("tab-submit-btn").textContent = t.tabSubmit;
  document.getElementById("tab-dashboard-btn").textContent = t.tabDashboard;
  document.getElementById("label-state").textContent = t.labelState;
  document.getElementById("label-district").textContent = t.labelDistrict;
  document.getElementById("label-text").textContent = t.labelText;
  document.getElementById("text-input").placeholder = t.placeholderText;
  document.getElementById("voice-btn-label").textContent = t.voiceBtn;
  document.getElementById("submit-btn").textContent = t.submitBtn;
  document.getElementById("hotspots-heading").textContent = t.hotspotsHeading;
  document.getElementById("th-state").textContent = t.thState;
  document.getElementById("th-category").textContent = t.thCategory;
  document.getElementById("th-count").textContent = t.thCount;
  document.getElementById("th-urgency").textContent = t.thUrgency;
  document.getElementById("th-infra").textContent = t.thInfra;
  document.getElementById("th-priority").textContent = t.thPriority;
  document.getElementById("tagline").textContent = t.tagline;
}

function showTab(tab) {
  document.getElementById("submit-tab").style.display = tab === "submit" ? "block" : "none";
  document.getElementById("dashboard-tab").style.display = tab === "dashboard" ? "block" : "none";
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
  document.getElementById(`tab-${tab}-btn`).classList.add("active");
  if (tab === "dashboard") loadDashboard();
}

function populateStates() {
  const sel = document.getElementById("state-select");
  STATES.forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    sel.appendChild(opt);
  });
}

// --- Voice input via the browser's Web Speech API (works in Chrome/Edge) ---
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
}

document.addEventListener("DOMContentLoaded", () => {
  populateStates();
  setLang("en");

  document.getElementById("voice-btn").addEventListener("click", () => {
    if (!recognition) {
      alert("Voice input isn't supported in this browser — try Chrome or Edge.");
      return;
    }
    recognition.lang = document.getElementById("voice-lang").value;
    recognition.start();
  });

  if (recognition) {
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      const box = document.getElementById("text-input");
      box.value += (box.value ? " " : "") + transcript;
    };
    recognition.onerror = (e) => console.error("Speech recognition error", e);
  }

  document.getElementById("feedback-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = document.getElementById("text-input").value.trim();
    const state = document.getElementById("state-select").value;
    const district = document.getElementById("district-input").value;
    if (!text) return;

    const resultBox = document.getElementById("result-box");
    resultBox.textContent = "...";

    try {
      const res = await fetch("/api/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, state, district, source: "web" }),
      });
      const data = await res.json();
      if (data.error) {
        resultBox.textContent = "Error: " + data.error;
        return;
      }
      const t = I18N[currentLang];
      const pct = Math.round((data.analysis.urgency_score || 0) * 100);
      resultBox.innerHTML =
        `<strong>${t.resultPrefix}</strong> ${data.analysis.category} · urgency ${pct}% · ${data.analysis.sentiment}`;
      document.getElementById("text-input").value = "";
    } catch (err) {
      resultBox.textContent = "Error submitting feedback: " + err.message;
    }
  });
});

async function loadDashboard() {
  const res = await fetch("/api/hotspots");
  const hotspots = await res.json();

  const tbody = document.querySelector("#hotspots-table tbody");
  tbody.innerHTML = "";
  hotspots.slice(0, 15).forEach((h) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${h.state}</td><td>${h.category}</td><td>${h.complaint_count}</td>
      <td>${h.avg_urgency}</td><td>${h.infra_index}</td><td>${h.priority_score}</td>`;
    tbody.appendChild(tr);
  });

  const catTotals = {};
  hotspots.forEach((h) => {
    catTotals[h.category] = (catTotals[h.category] || 0) + h.complaint_count;
  });

  const ctx = document.getElementById("categoryChart").getContext("2d");
  if (window._chart) window._chart.destroy();
  window._chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: Object.keys(catTotals),
      datasets: [{ label: "Complaints by Category", data: Object.values(catTotals), backgroundColor: "#2563eb" }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });
}
