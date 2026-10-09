// ngo.js — NGO Dashboard (100% live data, zero hardcoded values)
console.log("ngo.js loaded");

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
    "Accepted":   { bg: "#e8f5e9", color: "#2e7d32" },
    "In Progress":{ bg: "#e3f0ff", color: "#1565c0" },
    "Completed":  { bg: "#e8f5e9", color: "#1b5e20" },
    "Delivered":  { bg: "#e8f5e9", color: "#1b5e20" },
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

  if (name === "available") loadAvailableDonations();
  if (name === "orders")    loadNgoOrders();
  if (name === "profile")   loadNgoProfile();
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
// NGO STATS — loads actual counts from DB, shows 0 for new NGOs
// ─────────────────────────────────────────────────────────────

async function loadNgoStats() {
  try {
    const res  = await fetch(`${BASE}/api/ngo/stats`, { credentials: "include" });
    const data = await res.json();
    if (!data.success) return;
    const s = data.stats;
    setCounter("statTotal",     s.total     ?? 0);
    setCounter("statPending",   s.pending   ?? 0);
    setCounter("statDelivered", s.delivered ?? 0);
    setCounter("statAvailable", s.available ?? 0);
  } catch (e) { console.error("NGO stats error:", e); }
}

// ─────────────────────────────────────────────────────────────
// NGO PROFILE — load
// ─────────────────────────────────────────────────────────────

async function loadNgoProfile() {
  try {
    const res  = await fetch(`${BASE}/api/ngo/profile`, { credentials: "include" });
    const data = await res.json();
    if (data.error) return;

    setValue("ngo_name",       data.ngo_name);
    setValue("contact_no",     data.contact_no);
    setValue("address",        data.address);
    setValue("capacity",       data.capacity);
    setValue("priority_level", data.priority_level);
  } catch (e) { console.error("NGO profile load error:", e); }
}

// ─────────────────────────────────────────────────────────────
// NGO PROFILE — save
// ─────────────────────────────────────────────────────────────

async function saveNgoProfile() {
  const nameEl = document.getElementById("ngo_name");
  if (!nameEl || !nameEl.value.trim()) {
    showToast("NGO name cannot be empty.", "#c62828"); return;
  }

  const payload = {
    ngo_name:       document.getElementById("ngo_name")?.value.trim(),
    contact_no:     document.getElementById("contact_no")?.value.trim(),
    address:        document.getElementById("address")?.value.trim(),
    capacity:       document.getElementById("capacity")?.value.trim(),
    priority_level: document.getElementById("priority_level")?.value.trim()
  };

  try {
    const res    = await fetch(`${BASE}/api/ngo/update`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showToast("Profile saved ✅");
      const el = document.getElementById("welcomeName");
      if (el) el.textContent = payload.ngo_name;
    } else {
      showToast("Save failed: " + (result.error || "unknown"), "#c62828");
    }
  } catch (e) {
    console.error(e);
    showToast("Network error.", "#c62828");
  }
}

// ─────────────────────────────────────────────────────────────
// AVAILABLE DONATIONS — all Pending donations in the system
// ─────────────────────────────────────────────────────────────

async function loadAvailableDonations() {
  try {
    const res  = await fetch(`${BASE}/api/ngo/available-donations`, { credentials: "include" });
    const data = await res.json();

    const tbody = document.getElementById("availableTableBody");
    const empty = document.getElementById("noAvailableMsg");
    if (!tbody) return;

    const donations = data.data || [];

    if (donations.length === 0) {
      tbody.innerHTML = "";
      if (empty) empty.style.display = "block";
      setCounter("availableCount", 0);
      return;
    }
    if (empty) empty.style.display = "none";
    setCounter("availableCount", donations.length);

    tbody.innerHTML = donations.map(d => `
      <tr>
        <td>#${d.donation_id}</td>
        <td>${d.food_type}</td>
        <td>${d.quantity}</td>
        <td>${d.donor_name || "—"}</td>
        <td>${d.donor_contact || "—"}</td>
        <td>${d.donor_address || "—"}</td>
        <td>${d.date_of_donation || "—"}</td>
        <td>
          <button class="btn-sm success" onclick="acceptDonation(${d.donation_id}, ${d.quantity})">Accept</button>
        </td>
      </tr>`
    ).join("");

  } catch (e) { console.error("Available donations load error:", e); }
}

async function acceptDonation(donationId, availableQty) {
  let acceptedQty = availableQty;

  // Ask how much to accept — lets the NGO take less than the full amount
  const input = prompt(
    `How much would you like to accept? (Available: ${availableQty})`,
    availableQty
  );
  if (input === null) return; // cancelled

  acceptedQty = parseInt(input, 10);
  if (isNaN(acceptedQty) || acceptedQty <= 0 || acceptedQty > availableQty) {
    showToast(`Enter a quantity between 1 and ${availableQty}.`, "#c62828");
    return;
  }

  if (!confirm(`Accept ${acceptedQty} of ${availableQty}? A volunteer will be auto-assigned.`)) return;

  try {
    const res    = await fetch(`${BASE}/api/ngo/accept-donation`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ donation_id: donationId, accepted_qty: acceptedQty })
    });
    const result = await res.json();
    if (result.success) {
      showToast(result.message + (result.otp ? ` | OTP: ${result.otp}` : ""));
      loadAvailableDonations();
      loadNgoOrders();
      loadNgoStats();   // refresh stat cards after accept
    } else {
      showToast(result.error || "Failed to accept.", "#c62828");
    }
  } catch (e) {
    console.error(e);
    showToast("Network error.", "#c62828");
  }
}

// ─────────────────────────────────────────────────────────────
// NGO ORDERS — accepted deliveries (active + history)
// ─────────────────────────────────────────────────────────────

async function loadNgoOrders() {
  try {
    const res  = await fetch(`${BASE}/api/ngo/orders`, { credentials: "include" });
    const data = await res.json();

    const tbody = document.getElementById("ordersTableBody");
    const empty = document.getElementById("noOrdersMsg");
    if (!tbody) return;

    const orders = data.data || [];

    if (orders.length === 0) {
      tbody.innerHTML = "";
      if (empty) empty.style.display = "block";
      setCounter("ordersCount", 0);
      return;
    }
    if (empty) empty.style.display = "none";
    setCounter("ordersCount", orders.length);

    tbody.innerHTML = orders.map(o => {
      const isActive   = o.delivery_status !== "Delivered";
      const receiveBtn = isActive
        ? `<button class="btn-sm success" onclick="markReceived(${o.delivery_id}, ${o.pickup_id})">Mark Received</button>`
        : `<span style="color:#888;font-size:12px;">Completed</span>`;

      return `
        <tr>
          <td>#${o.delivery_id}</td>
          <td>${o.food_type}</td>
          <td>${o.quantity}</td>
          <td>${o.donor_name || "—"}</td>
          <td style="font-size:12px;">${o.donor_address || "—"}</td>
          <td>${o.volunteer_name || "<span style='color:#aaa'>Unassigned</span>"}</td>
          <td>${o.volunteer_contact || "—"}</td>
          <td>${statusBadge(o.pickup_status)}</td>
          <td>${statusBadge(o.delivery_status)}</td>
          <td>${o.otp_code || "—"}</td>
          <td>${receiveBtn}</td>
        </tr>`;
    }).join("");

  } catch (e) { console.error("Orders load error:", e); }
}

async function markReceived(deliveryId, pickupId) {
  if (!confirm("Confirm delivery received?")) return;
  try {
    const res    = await fetch(`${BASE}/api/ngo/mark-received`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ delivery_id: deliveryId, pickup_id: pickupId })
    });
    const result = await res.json();
    if (result.success) {
      showToast("Delivery marked as received ✅");
      loadNgoOrders();
      loadNgoStats();   // refresh stat cards after delivery
    } else {
      showToast("Failed: " + (result.error || "unknown"), "#c62828");
    }
  } catch (e) {
    console.error(e);
    showToast("Network error.", "#c62828");
  }
}

let ngoRating = 0;

function ngoRate(n){
  ngoRating = n;

  document.querySelectorAll("#ngoStarRow .star")
    .forEach((s,i) => {
      s.classList.toggle("active", i < n);
    });
}

async function submitNgoFeedback(){

  const comment = document.getElementById("ngo_comment").value;
  const hygiene = parseInt(document.getElementById("ngo_hygiene").value);

  if(!ngoRating){
    alert("Please select rating");
    return;
  }

  const donation_id = CURRENT_DONATION_ID;

  const res = await fetch("/api/ngo/feedback", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      donation_id: donation_id,
      rating: ngoRating,
      comments: comment,
      hygiene_score: hygiene
    })
  });

  const data = await res.json();

  if(data.success){
    alert("Feedback submitted successfully");
  } else {
    alert("Error submitting feedback");
  }
}
// ─────────────────────────────────────────────────────────────
// AUTO-REFRESH every 30 seconds
// ─────────────────────────────────────────────────────────────

let refreshTimer = null;

function startAutoRefresh() {
  refreshTimer = setInterval(() => {
    loadAvailableDonations();
    loadNgoOrders();
    loadNgoStats();
  }, 30000);
}


// ─────────────────────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────────────────────

window.addEventListener("DOMContentLoaded", () => {
  loadWelcome();
  loadNgoProfile();
  loadNgoStats();            // load real stats on page load (0 for new NGOs)
  loadAvailableDonations();
  loadNgoOrders();
  startAutoRefresh();

  const saveBtn = document.getElementById("saveBtn");
  if (saveBtn) saveBtn.addEventListener("click", saveNgoProfile);
});