/**
 * CampusBell - Frontend Controller
 * Real-time Timetable & Mobile Reminder System
 */

// Application State
const state = {
  timetable: [],
  byDay: {},
  clubbedByDay: {},
  clubbedTimetable: [],
  clubLabs: true,
  selectedDay: "Wednesday",
  activeFilter: "all",
  config: {},
  marks: { semesters: [] },
  scheduler: {
    is_running: true,
    next_daily_run: null
  },
  logs: []
};

// Days of the week in academic order
const WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const TIMETABLE_DRAFT_KEY = "campusbell_timetable_import_draft";

// DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initClock();
  setupEventListeners();
  restoreTimetableDraft();
  loadData();
});

// Theme Management
function initTheme() {
  const savedTheme = localStorage.getItem("campusbell_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeIcon(savedTheme);
}

function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
  const newTheme = currentTheme === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", newTheme);
  localStorage.setItem("campusbell_theme", newTheme);
  updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
  const icon = document.getElementById("theme-icon");
  if (icon) {
    icon.textContent = theme === "dark" ? "🌙" : "☀️";
  }
}

// Clock & Real-time Countdown
function initClock() {
  updateClock();
  setInterval(updateClock, 1000);
}

function updateClock() {
  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
  const dayName = now.toLocaleDateString('en-US', { weekday: 'long' });
  const dateStr = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  const clockEl = document.getElementById("clock-time");
  const dayEl = document.getElementById("clock-day");
  const phoneClock = document.getElementById("phone-clock");

  if (clockEl) clockEl.textContent = timeStr;
  if (dayEl) dayEl.textContent = `${dayName}, ${dateStr}`;
  if (phoneClock) phoneClock.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });

  // Update spotlight countdown
  updateSpotlightCountdown(now);
}

function updateSpotlightCountdown(now) {
  const todayName = now.toLocaleDateString('en-US', { weekday: 'long' });
  const currentDayClasses = state.clubLabs ? (state.clubbedByDay[todayName] || []) : (state.byDay[todayName] || []);
  const todayClasses = currentDayClasses;

  const subjectTitle = document.getElementById("next-subject-title");
  const nextTime = document.getElementById("next-time-val");
  const nextType = document.getElementById("next-type-val");
  const nextVenue = document.getElementById("next-venue-val");
  const countdownDigits = document.getElementById("countdown-digits");
  const spotlightLabel = document.querySelector(".spotlight-label");

  if (!todayClasses.length) {
    if (subjectTitle) subjectTitle.textContent = "No Classes Today! 🎉";
    if (nextTime) nextTime.textContent = "Enjoy your day off!";
    if (nextType) nextType.style.display = "none";
    if (nextVenue) nextVenue.style.display = "none";
    if (countdownDigits) countdownDigits.textContent = "Weekend / Holiday";
    if (spotlightLabel) spotlightLabel.textContent = "TODAY'S STATUS";
    return;
  }

  // Find next class or current class
  const currentMinutes = now.getHours() * 60 + now.getMinutes();
  const currentSeconds = now.getSeconds();

  let upcomingClass = null;
  let inProgressClass = null;

  for (const c of todayClasses) {
    if (!c.start24) continue;
    const [sh, sm] = c.start24.split(":").map(Number);
    const [eh, em] = (c.end24 || c.start24).split(":").map(Number);

    const startTotal = sh * 60 + sm;
    const endTotal = eh * 60 + em;

    if (currentMinutes >= startTotal && currentMinutes < endTotal) {
      inProgressClass = c;
      break;
    } else if (currentMinutes < startTotal) {
      if (!upcomingClass) {
        upcomingClass = c;
      }
    }
  }

  if (nextType) nextType.style.display = "inline-flex";
  if (nextVenue) nextVenue.style.display = "inline-flex";

  if (inProgressClass) {
    if (spotlightLabel) spotlightLabel.textContent = "CURRENTLY IN SESSION";
    if (subjectTitle) subjectTitle.textContent = inProgressClass.subject;
    if (nextTime) nextTime.textContent = `⏰ ${inProgressClass.startTime} – ${inProgressClass.endTime}`;
    if (nextType) {
      nextType.textContent = inProgressClass.classType === "Lab" ? "🔬 Lab" : "📝 Theory";
      nextType.className = `meta-item type ${inProgressClass.classType.toLowerCase()}`;
    }
    if (nextVenue) nextVenue.textContent = `📍 Venue: ${inProgressClass.venue}`;
    
    // Time until end
    const [eh, em] = inProgressClass.end24.split(":").map(Number);
    const endSecs = (eh * 60 + em) * 60;
    const nowSecs = (now.getHours() * 60 + now.getMinutes()) * 60 + currentSeconds;
    const diffSecs = Math.max(0, endSecs - nowSecs);
    const mins = Math.floor(diffSecs / 60);
    const secs = diffSecs % 60;
    if (countdownDigits) countdownDigits.textContent = `Ends in: ${String(mins).padStart(2, '0')}m ${String(secs).padStart(2, '0')}s`;

  } else if (upcomingClass) {
    if (spotlightLabel) spotlightLabel.textContent = "NEXT UPCOMING CLASS";
    if (subjectTitle) subjectTitle.textContent = upcomingClass.subject;
    if (nextTime) nextTime.textContent = `⏰ ${upcomingClass.startTime} – ${upcomingClass.endTime}`;
    if (nextType) {
      nextType.textContent = upcomingClass.classType === "Lab" ? "🔬 Lab" : "📝 Theory";
      nextType.className = `meta-item type ${upcomingClass.classType.toLowerCase()}`;
    }
    if (nextVenue) nextVenue.textContent = `📍 Venue: ${upcomingClass.venue}`;

    const [sh, sm] = upcomingClass.start24.split(":").map(Number);
    const startSecs = (sh * 60 + sm) * 60;
    const nowSecs = (now.getHours() * 60 + now.getMinutes()) * 60 + currentSeconds;
    const diffSecs = Math.max(0, startSecs - nowSecs);
    const hrs = Math.floor(diffSecs / 3600);
    const mins = Math.floor((diffSecs % 3600) / 60);
    const secs = diffSecs % 60;
    if (countdownDigits) {
      countdownDigits.textContent = hrs > 0 
        ? `${String(hrs).padStart(2, '0')}h ${String(mins).padStart(2, '0')}m ${String(secs).padStart(2, '0')}s`
        : `${String(mins).padStart(2, '0')}m ${String(secs).padStart(2, '0')}s`;
    }

  } else {
    if (spotlightLabel) spotlightLabel.textContent = "DAY COMPLETED";
    if (subjectTitle) subjectTitle.textContent = "All classes finished for today!";
    if (nextTime) nextTime.textContent = "Great job today! Relax & recharge.";
    if (nextType) nextType.style.display = "none";
    if (nextVenue) nextVenue.style.display = "none";
    if (countdownDigits) countdownDigits.textContent = "See you tomorrow! 🌟";
  }
}

// Fetch Initial Data
async function loadData() {
  try {
    const [timetableRes, statusRes, configRes, marksRes] = await Promise.all([
      fetch("/api/timetable").then(r => r.json()),
      fetch("/api/status").then(r => r.json()),
      fetch("/api/config").then(r => r.json()),
      fetch("/api/marks").then(r => r.json())
    ]);

    state.timetable = timetableRes.timetable || [];
    state.byDay = timetableRes.by_day || {};
    state.clubbedByDay = timetableRes.clubbed_by_day || timetableRes.by_day || {};
    state.clubbedTimetable = timetableRes.clubbed_timetable || timetableRes.timetable || [];
    state.config = configRes || {};
    state.marks = marksRes || { semesters: [] };
    state.scheduler = statusRes.scheduler || {};
    state.logs = statusRes.recent_logs || [];

    // Detect today and select it
    const todayName = new Date().toLocaleDateString('en-US', { weekday: 'long' });
    if (WEEK_DAYS.includes(todayName)) {
      state.selectedDay = todayName;
    } else {
      state.selectedDay = "Monday"; // default to Monday on weekend
    }

    renderHeaderBadges(todayName);
    renderDayTabs();
    renderSchedule();
    renderConfigForm();
    renderLogs();
    updatePhonePreview(state.selectedDay);
    renderMarks();

  } catch (error) {
    console.error("Failed to load initial app data:", error);
    showToast("Failed to connect to backend server.", "error");
  }
}

// Render Header / Hero Badges
function renderHeaderBadges(todayName) {
  const todayBadge = document.getElementById("today-name-badge");
  const countBadge = document.getElementById("today-class-count-badge");
  const channelBadge = document.getElementById("active-channel-badge");
  const nextBriefing = document.getElementById("next-briefing-time");
  const schedulerDot = document.getElementById("scheduler-dot");
  const schedulerLabel = document.getElementById("scheduler-status-text");

  const todayClasses = (state.clubLabs ? state.clubbedByDay : state.byDay)[todayName] || [];
  if (todayBadge) todayBadge.textContent = `${todayName} Schedule`;
  if (countBadge) countBadge.textContent = `${todayClasses.length} ${state.clubLabs ? 'Session' : 'Class'}${todayClasses.length !== 1 ? 's' : ''} Today`;

  const channelNames = {
    "callmebot_whatsapp": "WhatsApp (CallMeBot)",
    "ntfy_push": "Mobile Push (ntfy)",
    "twilio_whatsapp": "Twilio WhatsApp",
    "twilio_sms": "Twilio SMS",
    "telegram": "Telegram Bot",
    "simulation": "Simulation Mode"
  };
  const activeChan = state.config.active_channel || "simulation";
  if (channelBadge) channelBadge.textContent = `📡 Channel: ${channelNames[activeChan] || activeChan}`;

  if (nextBriefing && state.scheduler.next_daily_run) {
    nextBriefing.textContent = state.scheduler.next_daily_run;
  }

  if (schedulerDot && schedulerLabel) {
    if (state.scheduler.is_running) {
      schedulerDot.className = "status-dot active";
      schedulerLabel.textContent = "Scheduler: Active";
    } else {
      schedulerDot.className = "status-dot";
      schedulerLabel.textContent = "Scheduler: Paused";
    }
  }
}

// Render Day Tabs
function renderDayTabs() {
  const tabsContainer = document.getElementById("day-selector-tabs");
  if (!tabsContainer) return;

  tabsContainer.querySelectorAll(".tab-btn").forEach(btn => {
    const day = btn.getAttribute("data-day");
    if (day === state.selectedDay) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  const sendDaySelect = document.getElementById("send-day-select");
  if (sendDaySelect && WEEK_DAYS.includes(state.selectedDay)) {
    sendDaySelect.value = state.selectedDay;
  }
  updateSendDayButton();
}

function updateSendDayButton() {
  const button = document.getElementById("btn-send-selected-day");
  const select = document.getElementById("send-day-select");
  if (button && select) {
    button.innerHTML = `<span class="btn-icon">📤</span><span>Send ${select.value} Timetable</span>`;
  }
}

// Render Timetable Cards
function renderSchedule() {
  const container = document.getElementById("schedule-cards-container");
  if (!container) return;

  const activeSourceByDay = state.clubLabs ? state.clubbedByDay : state.byDay;
  const activeSourceTimetable = state.clubLabs ? state.clubbedTimetable : state.timetable;

  let classesToDisplay = [];
  if (state.selectedDay === "ALL") {
    classesToDisplay = [...activeSourceTimetable];
  } else {
    classesToDisplay = [...(activeSourceByDay[state.selectedDay] || [])];
  }

  // Filter by Type (Lab / Theory)
  const countAll = classesToDisplay.length;
  const countLab = classesToDisplay.filter(c => c.classType.toLowerCase() === "lab").length;
  const countTheory = classesToDisplay.filter(c => c.classType.toLowerCase() === "theory").length;

  document.getElementById("count-all").textContent = countAll;
  document.getElementById("count-lab").textContent = countLab;
  document.getElementById("count-theory").textContent = countTheory;

  if (state.activeFilter === "lab") {
    classesToDisplay = classesToDisplay.filter(c => c.classType.toLowerCase() === "lab");
  } else if (state.activeFilter === "theory") {
    classesToDisplay = classesToDisplay.filter(c => c.classType.toLowerCase() === "theory");
  }

  if (classesToDisplay.length === 0) {
    container.innerHTML = `
      <div class="empty-classes-card">
        <div class="empty-classes-icon">🏖️</div>
        <h3>No Classes Found</h3>
        <p>No lectures or labs scheduled for this selection.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = classesToDisplay.map(c => {
    const isLab = c.classType.toLowerCase() === "lab";
    const isClubbed = !!c.isClubbed;
    let badgeHtml = '';
    if (isClubbed) {
      badgeHtml = `<span class="type-badge clubbed">🔬 2-Period Lab</span>`;
    } else if (isLab) {
      badgeHtml = `<span class="type-badge lab">🔬 Lab</span>`;
    } else {
      badgeHtml = `<span class="type-badge theory">📝 Theory</span>`;
    }

    return `
      <div class="class-card ${isLab ? 'card-lab' : 'card-theory'}">
        <div class="class-main-info">
          <div class="class-time-row">
            <span class="class-time">⏰ ${c.startTime} – ${c.endTime}</span>
            ${state.selectedDay === "ALL" ? `<span class="class-day-tag">${c.day}</span>` : ''}
          </div>
          <h3 class="class-title">${c.subject}</h3>
          <div class="class-badges-row">
            ${badgeHtml}
            <span class="venue-badge">
              📍 ${c.venue}
            </span>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// Render Configuration Form
function renderConfigForm() {
  const phoneInput = document.getElementById("input-mobile-number");
  const timeInput = document.getElementById("input-reminder-time");
  const preClassSelect = document.getElementById("input-preclass-minutes");
  const providerDetailsBox = document.getElementById("provider-details-box");

  if (phoneInput && state.config.mobile_number) {
    phoneInput.value = state.config.mobile_number;
  }
  if (timeInput && state.config.daily_reminder_time) {
    timeInput.value = state.config.daily_reminder_time;
  }
  if (preClassSelect && state.config.pre_class_reminder_minutes !== undefined) {
    preClassSelect.value = state.config.pre_class_reminder_enabled ? String(state.config.pre_class_reminder_minutes) : "0";
  }

  // Radio button
  const channel = state.config.active_channel || "simulation";
  const radio = document.querySelector(`input[name="channel_radio"][value="${channel}"]`);
  if (radio) radio.checked = true;

  renderProviderDetails(channel);
}

function renderMarks() {
  const container = document.getElementById("marks-semesters-container");
  if (!container) return;

  if (!state.marks.semesters.length) {
    container.innerHTML = `<div class="marks-empty-state">No semesters added yet. Add a semester to start entering marks.</div>`;
    return;
  }

  container.innerHTML = state.marks.semesters.map((semester, semesterIndex) => `
    <article class="semester-card" data-semester-index="${semesterIndex}">
      <div class="semester-card-header">
        <input class="semester-name-input form-control" data-field="semester-name" value="${escapeHtml(semester.name || `Semester ${semesterIndex + 1}`)}" placeholder="Semester name">
        <button class="icon-action danger" type="button" data-action="remove-semester" title="Remove semester" aria-label="Remove semester">✕</button>
      </div>
      <div class="marks-table-wrap">
        <table class="marks-table">
          <thead><tr><th>Subject</th><th>Total Marks</th><th>Cat1</th><th>Cat2</th><th>FAT</th><th></th></tr></thead>
          <tbody>
            ${(semester.subjects || []).map((subject, subjectIndex) => `
              <tr data-subject-index="${subjectIndex}">
                <td><input class="form-control" data-field="subject" value="${escapeHtml(subject.name || "")}" placeholder="Subject name"></td>
                <td><input class="form-control marks-number" data-field="total" type="number" min="0" value="${subject.total ?? ""}" placeholder="100"></td>
                <td><input class="form-control marks-number" data-field="cat1" type="number" min="0" value="${subject.cat1 ?? ""}" placeholder="-" ></td>
                <td><input class="form-control marks-number" data-field="cat2" type="number" min="0" value="${subject.cat2 ?? ""}" placeholder="-" ></td>
                <td><input class="form-control marks-number" data-field="fat" type="number" min="0" value="${subject.fat ?? ""}" placeholder="-" ></td>
                <td><button class="icon-action danger" type="button" data-action="remove-subject" title="Remove subject" aria-label="Remove subject">✕</button></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
      <button class="btn-text-action add-subject-btn" type="button" data-action="add-subject">＋ Add Subject</button>
    </article>
  `).join("");
}

function addSemester() {
  state.marks.semesters.push({ name: `Semester ${state.marks.semesters.length + 1}`, subjects: [{ name: "", total: "", cat1: "", cat2: "", fat: "" }] });
  renderMarks();
}

function collectMarksFromForm() {
  return [...document.querySelectorAll(".semester-card")].map((card, semesterIndex) => ({
    name: card.querySelector('[data-field="semester-name"]')?.value.trim() || `Semester ${semesterIndex + 1}`,
    subjects: [...card.querySelectorAll("tbody tr")].map(row => ({
      name: row.querySelector('[data-field="subject"]')?.value.trim() || "",
      total: row.querySelector('[data-field="total"]')?.value || "",
      cat1: row.querySelector('[data-field="cat1"]')?.value || "",
      cat2: row.querySelector('[data-field="cat2"]')?.value || "",
      fat: row.querySelector('[data-field="fat"]')?.value || ""
    }))
  }));
}

async function saveMarks() {
  const button = document.getElementById("btn-save-marks");
  const semesters = collectMarksFromForm();
  if (semesters.some(semester => !semester.name || semester.subjects.some(subject => !subject.name))) {
    showToast("Enter a name for every semester and subject.", "error");
    return;
  }
  if (button) button.disabled = true;
  try {
    const response = await fetch("/api/marks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ semesters })
    });
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.detail || "Marks could not be saved.");
    state.marks = { semesters };
    showToast("Marks saved successfully.");
  } catch (error) {
    showToast(error.message || "Network error while saving marks.", "error");
  } finally {
    if (button) button.disabled = false;
  }
}

function setActiveSection(section) {
  const marksVisible = section === "marks";
  document.getElementById("marks-section")?.toggleAttribute("hidden", !marksVisible);
  ["hero-section", "timetable-section", "logs-section"].forEach(id => document.getElementById(id)?.toggleAttribute("hidden", marksVisible));
  document.getElementById("tab-marks")?.classList.toggle("active", marksVisible);
  document.getElementById("tab-timetable")?.classList.toggle("active", !marksVisible);
}

// Render Dynamic Provider Inputs based on selected channel
function renderProviderDetails(channel) {
  const box = document.getElementById("provider-details-box");
  if (!box) return;

  if (channel === "simulation") {
    box.innerHTML = `
      <div class="guide-box">
        <strong>🧪 Simulation / Local Test Mode</strong><br>
        Generates and logs the reminder instantly without sending external SMS or requiring API keys. Perfect for testing and viewing previews.
      </div>
    `;
  } else if (channel === "callmebot_whatsapp") {
    const cb = state.config.callmebot || {};
    box.innerHTML = `
      <div class="guide-box">
        <strong>🟢 CallMeBot Free WhatsApp Setup (1 Minute):</strong><br>
        1. Save <code>+34 644 10 55 84</code> to your phone contacts as CallMeBot.<br>
        2. Send WhatsApp message: <code>I allow callmebot to send me messages</code><br>
        3. You'll receive your free API key in 5 seconds. Enter it below:
      </div>
      <div class="form-group">
        <label class="form-label">CallMeBot API Key</label>
        <input type="text" id="input-callmebot-key" class="form-control" placeholder="e.g. 123456" value="${cb.api_key || ''}">
      </div>
    `;
  } else if (channel === "ntfy_push") {
    const ntfy = state.config.ntfy || {};
    const topic = ntfy.topic || "campusbell_schedule";
    box.innerHTML = `
      <div class="guide-box">
        <strong>📲 Free Mobile Push Notifications (Instant Lock Screen Alerts):</strong><br>
        1. Install free <strong>ntfy</strong> app on your Android or iPhone from App Store / Google Play.<br>
        2. Tap <strong>+</strong> and subscribe to topic: <code>${topic}</code>.<br>
        You'll get instant notifications with sound, emojis, and venues on your phone!
      </div>
      <div class="form-group">
        <label class="form-label">ntfy Topic Name</label>
        <input type="text" id="input-ntfy-topic" class="form-control" placeholder="my_secret_topic_name" value="${topic}">
      </div>
    `;
  } else if (channel === "twilio_whatsapp" || channel === "twilio_sms") {
    const tw = state.config.twilio || {};
    const isWa = channel === "twilio_whatsapp";
    box.innerHTML = `
      <div class="guide-box">
        <strong>${isWa ? '💬 Twilio WhatsApp' : '✉️ Twilio SMS'} API Credentials:</strong><br>
        Enter your Twilio Account SID, Auth Token, and Sender number.
      </div>
      <div class="form-group">
        <label class="form-label">Twilio Account SID</label>
        <input type="text" id="input-twilio-sid" class="form-control" placeholder="ACxxxxxxxxxxxxxx" value="${tw.account_sid || ''}">
      </div>
      <div class="form-group">
        <label class="form-label">Twilio Auth Token</label>
        <input type="password" id="input-twilio-token" class="form-control" placeholder="••••••••••••••" value="${tw.auth_token || ''}">
      </div>
      <div class="form-group">
        <label class="form-label">${isWa ? 'Twilio WhatsApp Sender' : 'Twilio Phone Number'}</label>
        <input type="text" id="input-twilio-from" class="form-control" placeholder="${isWa ? 'whatsapp:+14155238886' : '+1xxxxxxxxxx'}" value="${isWa ? (tw.whatsapp_sender || 'whatsapp:+14155238886') : (tw.phone_number || '')}">
      </div>
    `;
  } else if (channel === "telegram") {
    const tg = state.config.telegram || {};
    box.innerHTML = `
      <div class="guide-box">
        <strong>✈️ Telegram Mobile Alerts:</strong><br>
        1. Create a bot using <code>@BotFather</code> on Telegram.<br>
        2. Get your Chat ID using <code>@userinfobot</code>.<br>
        3. Enter the details below:
      </div>
      <div class="form-group">
        <label class="form-label">Telegram Bot Token</label>
        <input type="text" id="input-telegram-token" class="form-control" placeholder="123456789:ABCDefgh..." value="${tg.bot_token || ''}">
      </div>
      <div class="form-group">
        <label class="form-label">Telegram Chat ID</label>
        <input type="text" id="input-telegram-chat" class="form-control" placeholder="123456789" value="${tg.chat_id || ''}">
      </div>
    `;
  }
}

// Update Phone Screen Mockup Preview
async function updatePhonePreview(day) {
  const bubble = document.getElementById("mockup-message-bubble");
  if (!bubble) return;

  const targetDay = (day && day !== "ALL") ? day : (new Date().toLocaleDateString('en-US', { weekday: 'long' }));
  
  try {
    const res = await fetch("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ day: targetDay })
    });
    const data = await res.json();
    
    // Parse formatting: *bold* -> <strong>bold</strong>
    let text = data.formatted_message || "";
    let html = escapeHtml(text).replace(/\*(.*?)\*/g, "<strong>$1</strong>");
    bubble.innerHTML = html;
  } catch (err) {
    bubble.textContent = "Unable to load preview.";
  }
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
}

// Render Delivery Logs Table
function renderLogs() {
  const tbody = document.getElementById("logs-tbody");
  if (!tbody) return;

  if (!state.logs || state.logs.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="empty-state">No reminders sent yet. Click "Send Today's Timetable to Mobile" above to test!</td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = state.logs.map(log => {
    const isSuccess = log.status === "SUCCESS";
    return `
      <tr>
        <td><strong>${log.timestamp}</strong></td>
        <td>
          <span class="status-badge ${isSuccess ? 'success' : 'failed'}">
            ${isSuccess ? '✓ Delivered' : '✕ Failed'}
          </span>
        </td>
        <td><code>${log.channel}</code></td>
        <td>${log.recipient}</td>
        <td><small>${log.type}</small></td>
        <td title="${escapeHtml(log.full_message || '')}">${escapeHtml(log.preview)}</td>
      </tr>
    `;
  }).join("");
}

// Event Listeners
function setupEventListeners() {
  document.getElementById("tab-timetable")?.addEventListener("click", () => setActiveSection("timetable"));
  document.getElementById("tab-marks")?.addEventListener("click", () => setActiveSection("marks"));
  document.getElementById("btn-add-semester")?.addEventListener("click", addSemester);
  document.getElementById("btn-save-marks")?.addEventListener("click", saveMarks);

  document.getElementById("marks-semesters-container")?.addEventListener("click", (event) => {
    const action = event.target.closest("[data-action]")?.dataset.action;
    const card = event.target.closest(".semester-card");
    if (!action || !card) return;
    state.marks.semesters = collectMarksFromForm();
    const semesterIndex = Number(card.dataset.semesterIndex);
    if (action === "remove-semester") {
      state.marks.semesters.splice(semesterIndex, 1);
    } else if (action === "add-subject") {
      state.marks.semesters[semesterIndex].subjects.push({ name: "", total: "", cat1: "", cat2: "", fat: "" });
    } else if (action === "remove-subject") {
      const subjectIndex = Number(event.target.closest("tr")?.dataset.subjectIndex);
      state.marks.semesters[semesterIndex].subjects.splice(subjectIndex, 1);
    }
    renderMarks();
  });

  // Theme Toggle
  const themeBtn = document.getElementById("btn-theme-toggle");
  if (themeBtn) themeBtn.addEventListener("click", toggleTheme);

  // Scheduler Pill Toggle
  const schedulerBtn = document.getElementById("btn-toggle-scheduler");
  if (schedulerBtn) schedulerBtn.addEventListener("click", toggleScheduler);

  // Day Selector Tabs
  const tabsContainer = document.getElementById("day-selector-tabs");
  if (tabsContainer) {
    tabsContainer.addEventListener("click", (e) => {
      const tab = e.target.closest(".tab-btn");
      if (!tab) return;
      const day = tab.getAttribute("data-day");
      state.selectedDay = day;
      renderDayTabs();
      renderSchedule();
      updatePhonePreview(day);
    });
  }

  // Filter Chips (All, Lab, Theory)
  const filterChips = document.querySelector(".filter-chips");
  if (filterChips) {
    filterChips.addEventListener("click", (e) => {
      const chip = e.target.closest(".chip");
      if (!chip) return;
      filterChips.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      state.activeFilter = chip.getAttribute("data-filter");
      renderSchedule();
    });
  }

  // Club Consecutive Labs Toggle
  const btnToggleClub = document.getElementById("btn-toggle-club");
  if (btnToggleClub) {
    btnToggleClub.addEventListener("click", () => {
      state.clubLabs = !state.clubLabs;
      btnToggleClub.classList.toggle("active", state.clubLabs);
      btnToggleClub.textContent = state.clubLabs ? "✨ Club Continuous Labs (On)" : "✨ Club Continuous Labs (Off)";
      renderSchedule();
      const todayName = new Date().toLocaleDateString('en-US', { weekday: 'long' });
      renderHeaderBadges(todayName);
      showToast(state.clubLabs ? "Continuous Labs are now clubbed together!" : "Showing individual lab periods separately.");
    });
  }

  // Channel Radio Change
  const channelGrid = document.querySelector(".channel-options-grid");
  if (channelGrid) {
    channelGrid.addEventListener("change", (e) => {
      if (e.target.name === "channel_radio") {
        renderProviderDetails(e.target.value);
      }
    });
  }

  // Settings Form Submit
  const form = document.getElementById("settings-form");
  if (form) {
    form.addEventListener("submit", handleSaveSettings);
  }

  // Mobile reminder settings drawer
  const settingsDrawer = document.getElementById("settings-drawer");
  const settingsTab = document.getElementById("settings-drawer-tab");
  const settingsBackdrop = document.getElementById("settings-backdrop");
  const settingsClose = document.getElementById("drawer-close-btn");
  const timetableDrawer = document.getElementById("timetable-drawer");
  const timetableTab = document.getElementById("timetable-drawer-tab");
  const timetableClose = document.getElementById("timetable-close-btn");

  const setDrawerOpen = (drawer, tab, closeButton, isOpen) => {
    if (!drawer || !tab) return;

    drawer.classList.toggle("is-open", isOpen);
    settingsBackdrop?.classList.toggle("is-open", isOpen);
    tab.classList.toggle("drawer-open", isOpen);
    tab.setAttribute("aria-expanded", String(isOpen));
    document.body.classList.toggle("settings-drawer-open", isOpen);

    if (isOpen) {
      closeButton?.focus();
    } else {
      tab.focus();
    }
  };

  settingsTab?.addEventListener("click", () => {
    setDrawerOpen(settingsDrawer, settingsTab, settingsClose, !settingsDrawer?.classList.contains("is-open"));
  });
  settingsClose?.addEventListener("click", () => setDrawerOpen(settingsDrawer, settingsTab, settingsClose, false));
  timetableTab?.addEventListener("click", () => {
    setDrawerOpen(timetableDrawer, timetableTab, timetableClose, !timetableDrawer?.classList.contains("is-open"));
  });
  timetableClose?.addEventListener("click", () => setDrawerOpen(timetableDrawer, timetableTab, timetableClose, false));
  settingsBackdrop?.addEventListener("click", () => {
    setDrawerOpen(settingsDrawer, settingsTab, settingsClose, false);
    setDrawerOpen(timetableDrawer, timetableTab, timetableClose, false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (settingsDrawer?.classList.contains("is-open")) setDrawerOpen(settingsDrawer, settingsTab, settingsClose, false);
      if (timetableDrawer?.classList.contains("is-open")) setDrawerOpen(timetableDrawer, timetableTab, timetableClose, false);
    }
  });

  const timetableFileInput = document.getElementById("timetable-file-input");
  const timetableTextInput = document.getElementById("timetable-text-input");
  timetableFileInput?.addEventListener("change", handleTimetableFileSelect);
  timetableTextInput?.addEventListener("input", () => {
    saveTimetableDraft();
    updateTimetableImportPreview();
  });
  document.getElementById("timetable-import-form")?.addEventListener("submit", handleTimetableImport);

  const sendDaySelect = document.getElementById("send-day-select");
  sendDaySelect?.addEventListener("change", () => {
    state.selectedDay = sendDaySelect.value;
    renderDayTabs();
    renderSchedule();
    updatePhonePreview(state.selectedDay);
  });

  // Send Now Hero Button
  const btnSendNow = document.getElementById("btn-send-now");
  if (btnSendNow) {
    btnSendNow.addEventListener("click", handleSendNow);
  }

  // Send Selected Day Button
  const btnSendSelected = document.getElementById("btn-send-selected-day");
  if (btnSendSelected) {
    btnSendSelected.addEventListener("click", handleSendSelectedDay);
  }

  // Preview Button
  const btnPreview = document.getElementById("btn-preview-phone");
  if (btnPreview) {
    btnPreview.addEventListener("click", () => {
      const mockupCard = document.getElementById("phone-mockup-card");
      if (mockupCard) {
        mockupCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        mockupCard.style.boxShadow = "0 0 30px rgba(99, 102, 241, 0.6)";
        setTimeout(() => mockupCard.style.boxShadow = "", 1500);
      }
    });
  }

  // Refresh Logs Button
  const btnRefreshLogs = document.getElementById("btn-refresh-logs");
  if (btnRefreshLogs) {
    btnRefreshLogs.addEventListener("click", refreshLogs);
  }
}

function saveTimetableDraft() {
  const textarea = document.getElementById("timetable-text-input");
  if (textarea) localStorage.setItem(TIMETABLE_DRAFT_KEY, textarea.value);
}

function restoreTimetableDraft() {
  const textarea = document.getElementById("timetable-text-input");
  const savedDraft = localStorage.getItem(TIMETABLE_DRAFT_KEY);
  if (textarea && savedDraft) {
    textarea.value = savedDraft;
    updateTimetableImportPreview();
  }
}

function updateTimetableImportPreview() {
  const textarea = document.getElementById("timetable-text-input");
  const preview = document.getElementById("timetable-import-preview");
  if (!textarea || !preview) return;

  const lines = textarea.value.trim().split(/\r?\n/).filter(Boolean);
  preview.textContent = lines.length > 1
    ? `${lines.length - 1} timetable row${lines.length === 2 ? "" : "s"} ready to import.`
    : "Add a CSV or TSV header and at least one timetable row.";
}

function handleTimetableFileSelect(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = () => {
    const textarea = document.getElementById("timetable-text-input");
    if (textarea) textarea.value = String(reader.result || "");
    saveTimetableDraft();
    updateTimetableImportPreview();
  };
  reader.onerror = () => showToast("Unable to read the timetable file.", "error");
  reader.readAsText(file);
}

async function handleTimetableImport(event) {
  event.preventDefault();
  const textarea = document.getElementById("timetable-text-input");
  const button = document.getElementById("btn-import-timetable");
  const content = textarea?.value.trim() || "";
  const rows = content.split(/\r?\n/).filter(Boolean);

  if (rows.length < 2) {
    showToast("Add a header and at least one timetable row first.", "error");
    return;
  }

  saveTimetableDraft();

  if (button) button.disabled = true;
  try {
    const response = await fetch("/api/timetable/text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content })
    });
    const result = await response.json();
    if (!response.ok || !result.success) {
      throw new Error(result.detail || "Timetable import failed.");
    }

    await loadData();
    showToast(`Timetable imported successfully: ${result.count} rows applied.`);
  } catch (error) {
    showToast(error.message || "Network error while importing timetable.", "error");
  } finally {
    if (button) button.disabled = false;
  }
}

// Toggle Scheduler
async function toggleScheduler() {
  try {
    const res = await fetch("/api/scheduler/toggle", { method: "POST" });
    const data = await res.json();
    state.scheduler.is_running = data.is_running;
    
    const todayName = new Date().toLocaleDateString('en-US', { weekday: 'long' });
    renderHeaderBadges(todayName);
    showToast(data.is_running ? "🟢 Background scheduler started!" : "🛑 Background scheduler paused.");
  } catch (err) {
    showToast("Failed to toggle scheduler.", "error");
  }
}

// Save Settings Handler
async function handleSaveSettings(e) {
  e.preventDefault();
  
  const phone = document.getElementById("input-mobile-number")?.value.trim();
  const time = document.getElementById("input-reminder-time")?.value;
  const preClassMins = parseInt(document.getElementById("input-preclass-minutes")?.value || "15", 10);
  const activeRadio = document.querySelector('input[name="channel_radio"]:checked');
  const channel = activeRadio ? activeRadio.value : "simulation";

  const updatedConfig = {
    ...state.config,
    mobile_number: phone,
    active_channel: channel,
    daily_reminder_time: time,
    daily_reminder_enabled: true,
    pre_class_reminder_enabled: preClassMins > 0,
    pre_class_reminder_minutes: preClassMins
  };

  // Collect provider-specific values
  if (channel === "callmebot_whatsapp") {
    const apiKey = document.getElementById("input-callmebot-key")?.value.trim();
    updatedConfig.callmebot = { phone: phone, api_key: apiKey };
  } else if (channel === "ntfy_push") {
    const topic = document.getElementById("input-ntfy-topic")?.value.trim();
    updatedConfig.ntfy = { topic: topic, server: "https://ntfy.sh" };
  } else if (channel === "twilio_whatsapp" || channel === "twilio_sms") {
    const sid = document.getElementById("input-twilio-sid")?.value.trim();
    const token = document.getElementById("input-twilio-token")?.value.trim();
    const fromVal = document.getElementById("input-twilio-from")?.value.trim();
    updatedConfig.twilio = {
      ...state.config.twilio,
      account_sid: sid,
      auth_token: token,
      [channel === "twilio_whatsapp" ? 'whatsapp_sender' : 'phone_number']: fromVal
    };
  } else if (channel === "telegram") {
    const botToken = document.getElementById("input-telegram-token")?.value.trim();
    const chatId = document.getElementById("input-telegram-chat")?.value.trim();
    updatedConfig.telegram = { bot_token: botToken, chat_id: chatId };
  }

  const saveBtn = document.getElementById("btn-save-settings");
  if (saveBtn) saveBtn.disabled = true;

  try {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updatedConfig)
    });
    const result = await res.json();
    if (result.success) {
      state.config = updatedConfig;
      showToast("✅ Settings saved successfully! Mobile reminders configured.");
      renderHeaderBadges(new Date().toLocaleDateString('en-US', { weekday: 'long' }));
    } else {
      showToast(result.detail || "Failed to save settings", "error");
    }
  } catch (err) {
    showToast("Network error while saving settings.", "error");
  } finally {
    if (saveBtn) saveBtn.disabled = false;
  }
}

// Send Now Handler (Today)
async function handleSendNow() {
  const btn = document.getElementById("btn-send-now");
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="btn-icon">⏳</span> Dispatching reminder...`;

  try {
    const res = await fetch("/api/send-now", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await res.json();
    
    if (data.success) {
      const msg = data.result?.simulated 
        ? "📱 Reminder dispatched in Simulation Mode (Logged below)!" 
        : "🚀 Timetable reminder sent to your mobile phone!";
      showToast(msg);
    } else {
      showToast(`Delivery notice: ${data.result?.error || 'Failed to dispatch'}`, "error");
    }
    
    await refreshLogs();
  } catch (err) {
    showToast("Failed to communicate with reminder engine.", "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

// Send Selected Day Handler
async function handleSendSelectedDay() {
  const targetDay = document.getElementById("send-day-select")?.value || state.selectedDay;
  const btn = document.getElementById("btn-send-selected-day");
  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Sending...";

  try {
    const res = await fetch("/api/send-now", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ day: targetDay })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`📱 ${targetDay}'s schedule dispatched to mobile!`);
    } else {
      showToast(`Failed: ${data.result?.error}`, "error");
    }
    await refreshLogs();
  } catch (err) {
    showToast("Network error dispatching reminder.", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

// Refresh Delivery Logs
async function refreshLogs() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    state.logs = data.recent_logs || [];
    renderLogs();
  } catch (err) {
    console.error("Failed to refresh logs:", err);
  }
}

// Toast Notifications
function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${type === 'success' ? '🎉' : '⚠️'}</span>
    <span class="toast-message">${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "toast-in 0.3s cubic-bezier(0.16, 1, 0.3, 1) reverse";
    setTimeout(() => toast.remove(), 280);
  }, 4500);
}
