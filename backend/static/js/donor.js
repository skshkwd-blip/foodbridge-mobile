// donor.js — Donor Dashboard (100% live data, zero hardcoded values)
console.log("donor.js loaded");

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
function statusBadge(status) {
  let cls = "b-default";

  if (status === "Pending") cls = "b-pending";
  else if (status === "Accepted") cls = "b-accepted";
  else if (status === "In Progress") cls = "b-progress";
  else if (status === "Completed") cls = "b-completed";
  else if (status === "Delivered") cls = "b-completed";
  else if (status === "Wasted") cls = "b-wasted";

  return `<span class="badge ${cls}">${status || "—"}</span>`;
}

function setCounter(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val ?? 0;
}

function setValue(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val || "";
}

function toggleTheme() {
  const body = document.body;
  const newTheme = body.classList.contains("dark") ? "light" : "dark";

  body.classList.remove("dark", "light");
  body.classList.add(newTheme);
  localStorage.setItem("theme", newTheme);
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

  if (name === "history")  loadMyDonations();
  if (name === "profile")  loadDonorProfile();
  if (name === "donate")   loadDonorProfile();
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
// DONOR STATS — loads actual counts from DB, shows 0 for new users
// ─────────────────────────────────────────────────────────────

async function loadDonorStats() {
  try {
    const res  = await fetch(`${BASE}/api/donor/stats`, { credentials: "include" });
    const data = await res.json();
    if (!data.success) return;
    const s = data.stats;
    setCounter("statTotal",     s.total     ?? 0);
    setCounter("statPending",   s.pending   ?? 0);
    setCounter("statAccepted",  s.accepted  ?? 0);
    setCounter("statCompleted", s.completed ?? 0);
    // Keep donation tab badge in sync
    setCounter("donationCount", s.total ?? 0);
  } catch (e) { console.error("Stats load error:", e); }
}

// ─────────────────────────────────────────────────────────────
// DONOR PROFILE — load
// ─────────────────────────────────────────────────────────────

async function loadDonorProfile() {
  try {
    const res  = await fetch(`${BASE}/api/donor/profile`, { credentials: "include" });
    const data = await res.json();
    if (data.error) return;

    setValue("donor_name", data.donor_name);
    setValue("contact_no",  data.contact_no);
    setValue("address",     data.address);
    setValue("email",       data.email);

    const ratingEl = document.getElementById("hygiene_rating");
    if (ratingEl) ratingEl.textContent = data.hygiene_rating ?? 0;
  } catch (e) { console.error("Profile load error:", e); }
}

// ─────────────────────────────────────────────────────────────
// DONOR PROFILE — save
// ─────────────────────────────────────────────────────────────

async function saveDonorProfile() {
  const nameEl = document.getElementById("donor_name");
  if (!nameEl || !nameEl.value.trim()) {
    showToast("Name cannot be empty.", "#c62828"); return;
  }

  const payload = {
    donor_name: document.getElementById("donor_name")?.value.trim(),
    contact_no: document.getElementById("contact_no")?.value.trim(),
    address:    document.getElementById("address")?.value.trim(),
    email:      document.getElementById("email")?.value.trim()
  };

  try {
    const res    = await fetch(`${BASE}/api/donor/update`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showToast("Profile saved ✅");
      const el = document.getElementById("welcomeName");
      if (el) el.textContent = payload.donor_name;
    } else {
      showToast("Save failed: " + (result.error || "unknown"), "#c62828");
    }
  } catch (e) {
    console.error(e);
    showToast("Network error.", "#c62828");
  }
}

// ─────────────────────────────────────────────────────────────
// SUBMIT DONATION
// ─────────────────────────────────────────────────────────────

async function submitDonation() {
  const foodTypeEl = document.getElementById("food_type");
  const quantityEl = document.getElementById("quantity");
  const dateEl     = document.getElementById("date_of_donation");
  const timeEl     = document.getElementById("time");

  if (!foodTypeEl?.value.trim()) {
    showToast("Please enter food type.", "#c62828"); return;
  }
  if (!quantityEl?.value) {
    showToast("Please enter quantity.", "#c62828"); return;
  }

  const payload = {
    food_type:        foodTypeEl.value.trim(),
    quantity:         quantityEl.value,
    date_of_donation: dateEl?.value || new Date().toISOString().slice(0, 10),
    time:             timeEl?.value || null
  };

  try {
    const res    = await fetch(`${BASE}/api/donations`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showToast(`Donation #${result.donation_id} submitted ✅`);
      if (foodTypeEl) foodTypeEl.value = "";
      if (quantityEl) quantityEl.value = "";
      if (dateEl)     dateEl.value     = "";
      if (timeEl)     timeEl.value     = "";
      loadMyDonations();
      loadDonorStats();   // refresh stat cards after new donation
    } else {
      showToast("Failed to submit.", "#c62828");
    }
  } catch (e) {
    console.error(e);
    showToast("Network error.", "#c62828");
  }
}

// ─────────────────────────────────────────────────────────────
// MY DONATIONS — full status tracking
// ─────────────────────────────────────────────────────────────

async function loadMyDonations() {
  try {
    const res  = await fetch(`${BASE}/api/donor/donations`, { credentials: "include" });
    const data = await res.json();

    const tbody = document.getElementById("donationTableBody");
    const empty = document.getElementById("noDonationsMsg");
    if (!tbody) return;

    const donations = data.data || [];

    if (donations.length === 0) {
      tbody.innerHTML = "";
      if (empty) empty.style.display = "block";
      setCounter("donationCount", 0);
      return;
    }
    if (empty) empty.style.display = "none";

    tbody.innerHTML = donations.map(d => {
      const journey  = buildJourney(d);
      const canDelete = d.donation_status === "Pending";
      const deleteBtn = canDelete
        ? `<button class="btn-sm danger" onclick="deleteDonation(${d.donation_id})">Cancel</button>`
        : "";

      return `
        <tr>
          <td>#${d.donation_id}</td>
          <td>${d.food_type}</td>
          <td>${d.quantity}</td>
          <td>${statusBadge(d.donation_status)}</td>
          <td>${d.date_of_donation || "—"}</td>
          <td style="font-size:12px;line-height:1.6;">${journey}</td>
          <td>${deleteBtn}</td>
        </tr>`;
    }).join("");

  } catch (e) { console.error("Donations load error:", e); }
}

function buildJourney(d) {
  const lines = [];
  if (d.ngo_name)          lines.push(`🏠 <b>NGO:</b> ${d.ngo_name}`);
  if (d.volunteer_name)    lines.push(`🚴 <b>Volunteer:</b> ${d.volunteer_name}`);
  if (d.volunteer_contact) lines.push(`📞 ${d.volunteer_contact}`);
  if (d.pickup_status)     lines.push(`📦 Pickup: ${d.pickup_status}`);
  if (d.otp_code && d.pickup_status !== "Delivered")
                           lines.push(`🔑 <b>OTP:</b> ${d.otp_code}`);
  if (d.delivery_status)   lines.push(`🚚 Delivery: ${d.delivery_status}`);
  return lines.length ? lines.join("<br>") : "—";
}

async function deleteDonation(donationId) {
  if (!confirm("Cancel this donation?")) return;
  try {
    const res    = await fetch(`${BASE}/api/donations/${donationId}`, {
      method: "DELETE", credentials: "include"
    });
    const result = await res.json();
    if (result.success) {
      showToast("Donation cancelled.");
      loadMyDonations();
      loadDonorStats();   // refresh stat cards after cancel
    } else {
      showToast("Cannot cancel (already accepted).", "#c62828");
    }
  } catch (e) { console.error(e); }
}

// ─────────────────────────────────────────────────────────────
// AUTO-REFRESH every 30 seconds
// ─────────────────────────────────────────────────────────────

let refreshTimer = null;

function startAutoRefresh() {
  refreshTimer = setInterval(() => {
    loadMyDonations();
    loadDonorStats();
  }, 30000);
}


// ─────────────────────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────────────────────

window.addEventListener("DOMContentLoaded", () => {
  loadWelcome();
  loadDonorProfile();
  loadDonorStats();      // load real stats on page load (0 for new users)
  loadMyDonations();
  startAutoRefresh();

  const saveBtn   = document.getElementById("saveBtn");
  const donateBtn = document.getElementById("donateBtn");
  if (saveBtn)   saveBtn.addEventListener("click", saveDonorProfile);
  if (donateBtn) donateBtn.addEventListener("click", submitDonation);
});