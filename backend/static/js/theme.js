console.log("theme.js loaded");

// APPLY THEME ON LOAD (ONLY ONCE)
(function () {
  const saved = localStorage.getItem("theme") || "dark";

  document.body.classList.remove("dark", "light");
  document.body.classList.add(saved);

  console.log("BODY CLASS:", document.body.className);
})();

// TOGGLE FUNCTION
function toggleTheme() {
  const body = document.body;

  if (body.classList.contains("dark")) {
    body.classList.replace("dark", "light");
    localStorage.setItem("theme", "light");
  } else {
    body.classList.replace("light", "dark");
    localStorage.setItem("theme", "dark");
  }
}

// Load saved theme
const savedTheme = localStorage.getItem("theme");
if (savedTheme) {
  document.body.classList.remove("dark", "light");
  document.body.classList.add(savedTheme);
}