// volunteer.js — Volunteer Dashboard (100% live data, zero hardcoded values)
console.log("volunteer.js loaded");

const BASE = "";  // same-origin Flask server

// ─────────────────────────────────────────────────────────────
// UTILS
// ─────────────────────────────────────────────────────────────

function showToast(msg, color = "#142b1e") {
  const t = document.createElement("div");
  t.textContent = msg;
  Object.assign(t.style, {
    position: "fixed", bottom: "24px", left: "50%",
    transform: "translateX(-50%)",
    background: color, color: "#fff",
    padding: "12px 28px", borderRadius: "30px",
    fontSize: "13px", zIndex: 9999,
    boxShadow: "0 4px 20px rgba(0,0,0,0.25)",
  });
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

function toggleTheme() {
  const body = document.body;
  const newTheme = body.classList.contains("dark") ? "light" : "dark";

  body.classList.remove("dark", "light");
  body.classList.add(newTheme);
  localStorage.setItem("theme", newTheme);
}

function statusBadge(status) {
  const map = {
    "Pending":    { bg: "#fff3e0", color: "#e65c00" },
    "In Progress":{ bg: "#e3f0ff", color: "#1565c0" },
    "Delivered":  { bg: "#e8f5e9", color: "#1b5e20" },
    "Completed":  { bg: "#e8f5e9", color: "#1b5e20" },
    "Available":  { bg: "#e8f5e9", color: "#2e7d32" },
    "Busy":       { bg: "#fce4ec", color: "#b71c1c" },
  };
  const s = map[status] || { bg: "#f5f5f5", color: "#555" };
  return `<span style="background:${s.bg};color:${s.color};padding:3px 12px;border-radius:20px;font-size:12px;font-weight:600;">${status || "—"}</span>`;
}

function setCounter(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val ?? 0;
}

function setValue(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val || "";
}

// ─────────────────────────────────────────────────────────────
// TABS
// ─────────────────────────────────────────────────────────────

function switchTab(name, el) {
  document.querySelectorAll(".tab-section").forEach(s => s.style.display = "none");
  const section = document.getElementById("tab-" + name);
  if (section) section.style.display = "block";
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  if (el) el.classList.add("active");

  if (name === "pickups") loadMyPickups();
  if (name === "profile") loadVolunteerProfile();
}

// ─────────────────────────────────────────────────────────────
// HEADER — show logged-in name
// ─────────────────────────────────────────────────────────────

async function loadWelcome() {
  try {
    const res  = await fetch(`${BASE}/api/me`, { credentials: "include" });
    const data = await res.json();
    if (data.error) { window.location.href = "/login"; return; }
    const el = document.getElementById("welcomeName");
    if (el) el.textContent = data.user_name;
  } catch (e) { console.error(e); }
}

// ─────────────────────────────────────────────────────────────
// VOLUNTEER STATS — loads actual counts from DB, shows 0 for new volunteers
// ─────────────────────────────────────────────────────────────

async function loadVolunteerStats() {
  try {
    const res  = await fetch(`${BASE}/api/volunteer/stats`, { credentials: "include" });
    const data = await res.json();
    if (!data.success) return;
    const s = data.stats;
    setCounter("statTotal",      s.total       ?? 0);
    setCounter("statPending",    s.pending     ?? 0);
    setCounter("statInProgress", s.in_progress ?? 0);
    setCounter("statDelivered",  s.delivered   ?? 0);
    // Keep pickups tab badge in sync
    setCounter("pickupsCount",   s.total       ?? 0);
  } catch (e) { console.error("Volunteer stats error:", e); }
}

// ─────────────────────────────────────────────────────────────
// VOLUNTEER PROFILE — load
// ─────────────────────────────────────────────────────────────

async function loadVolunteerProfile() {
  try {
    const res  = await fetch(`${BASE}/api/volunteer/profile`, { credentials: "include" });
    const data = await res.json();
    if (data.error) return;

    setValue("vol_name",             data.name);
    setValue("contact_no",           data.contact_no);
    setValue("vehicle_type",         data.vehicle_type);
    setValue("availability_status",  data.availability_status);

    // Show availability badge if element exists
    const statusEl = document.getElementById("availabilityBadge");
    if (statusEl) statusEl.innerHTML = statusBadge(data.availability_status);
  } catch (e) { console.error("Profile load error:", e); }
}

// ─────────────────────────────────────────────────────────────
// VOLUNTEER PROFILE — save
// ─────────────────────────────────────────────────────────────

async function saveVolunteerProfile() {
  const nameEl = document.getElementById("vol_name");
  if (!nameEl || !nameEl.value.trim()) {
    showToast("Name cannot be empty.", "#c62828"); return;
  }

  const payload = {
    name:                 document.getElementById("vol_name")?.value.trim(),
    contact_no:           document.getElementById("contact_no")?.value.trim(),
    vehicle_type:         document.getElementById("vehicle_type")?.value.trim(),
    availability_status:  document.getElementById("availability_status")?.value.trim()
  };

  try {
    const res    = await fetch(`${BASE}/api/volunteer/update`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showToast("Profile saved ✅");
      const el = document.getElementById("welcomeName");
      if (el) el.textContent = payload.name;
    } else {
      showToast("Save failed: " + (result.error || "unknown"), "#c62828");
    }
  } catch (e) {
    console.error(e);
    showToast("Network error.", "#c62828");
  }
}

// ─────────────────────────────────────────────────────────────
// MY PICKUPS — assigned pickups with full donor + NGO details
// ─────────────────────────────────────────────────────────────

async function loadMyPickups() {
  try {
    const res  = await fetch(`${BASE}/api/volunteer/pickups`, { credentials: "include" });
    const data = await res.json();

    const tbody = document.getElementById("pickupsTableBody");
    const empty = document.getElementById("noPickupsMsg");
    if (!tbody) return;

    const pickups = data.data || [];

    if (pickups.length === 0) {
      tbody.innerHTML = "";
      if (empty) empty.style.display = "block";
      setCounter("pickupsCount", 0);
      return;
    }
    if (empty) empty.style.display = "none";
    setCounter("pickupsCount", pickups.length);

    tbody.innerHTML = pickups.map(p => {
      // Determine which action buttons to show based on current status
      let actionBtn = "";
      if (p.status === "Pending") {
        actionBtn = `<button class="btn-sm primary" onclick="updatePickup(${p.pickup_id}, 'In Progress')">Start Pickup</button>`;
      } else if (p.status === "In Progress") {
        actionBtn = `<button class="btn-sm success" onclick="updatePickup(${p.pickup_id}, 'Delivered')">Mark Delivered</button>`;
      } else {
        actionBtn = `<span style="color:#888;font-size:12px;">Done</span>`;
      }

      return `
        <tr>
          <td>#${p.pickup_id}</td>
          <td>${p.food_type}</td>
          <td>${p.quantity}</td>
          <td>
            <b>${p.donor_name || "—"}</b><br>
            <span style="font-size:11px;color:#666;">${p.donor_contact || ""}</span><br>
            <span style="font-size:11px;color:#888;">${p.donor_address || ""}</span>
          </td>
          <td>
            <b>${p.ngo_name || "—"}</b><br>
            <span style="font-size:11px;color:#666;">${p.ngo_contact || ""}</span><br>
            <span style="font-size:11px;color:#888;">${p.ngo_address || ""}</span>
          </td>
          <td>${statusBadge(p.status)}</td>
          <td>${statusBadge(p.delivery_status)}</td>
          <td style="font-weight:700;letter-spacing:2px;">${p.otp_code || "—"}</td>
          <td>${actionBtn}</td>
        </tr>`;
    }).join("");

  } catch (e) { console.error("Pickups load error:", e); }
}

async function updatePickup(pickupId, status) {
  const label = status === "In Progress" ? "start this pickup" : "mark this delivery as done";
  if (!confirm(`Are you sure you want to ${label}?`)) return;

  try {
    const res    = await fetch(`${BASE}/api/volunteer/update-pickup`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pickup_id: pickupId, status })
    });
    const result = await res.json();
    if (result.success) {
      showToast(result.message + " ✅");
      loadMyPickups();
      loadVolunteerStats();   // refresh stat cards after status change
    } else {
      showToast(result.error || "Update failed.", "#c62828");
    }
  } catch (e) {
    console.error(e);
    showToast("Network error.", "#c62828");
  }
}

// ─────────────────────────────────────────────────────────────
// AUTO-REFRESH every 30 seconds
// ─────────────────────────────────────────────────────────────

let refreshTimer = null;

function startAutoRefresh() {
  refreshTimer = setInterval(() => {
    loadMyPickups();
    loadVolunteerStats();
  }, 30000);
}


// ─────────────────────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────────────────────

window.addEventListener("DOMContentLoaded", () => {
  loadWelcome();
  loadVolunteerProfile();
  loadVolunteerStats();      // load real stats on page load (0 for new volunteers)
  loadMyPickups();
  startAutoRefresh();

  const saveBtn = document.getElementById("saveBtn");
  if (saveBtn) saveBtn.addEventListener("click", saveVolunteerProfile);
});