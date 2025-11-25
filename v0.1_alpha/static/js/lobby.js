// static/js/lobby.js
const language = "en";

async function fetch_skills() {
  try {
    const response = await fetch(`/api/localization/${language}/skills`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching skills:", error);
    throw error;
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const skills = await fetch_skills();

  const skillsContainer = document.getElementById("skills-container");
  Object.entries(skills).forEach(([key, value]) => {
    const btn = document.createElement("button");
    btn.className =
      "skill-btn p-2 border rounded m-2 flex flex-col items-center hover:bg-blue-100";
    btn.dataset.skill = key;
    btn.innerHTML = `
      <img src="${value.icon}" alt="${value.name}" class="w-12 h-12 mb-2">
      <p class="font-bold">${value.name}</p>
      <p class="text-sm text-center">${value.description}</p>
    `;
    if (key == "none") btn.classList.add("bg-blue-200");
    skillsContainer.appendChild(btn);
  });

  const form = document.querySelector("form");
  let selectedSkill = "none";
  skillsContainer.addEventListener("click", (e) => {
    const btn = e.target.closest(".skill-btn");
    if (btn) {
      document
        .querySelectorAll(".skill-btn")
        .forEach((b) => b.classList.remove("bg-blue-200"));
      btn.classList.add("bg-blue-200");
      selectedSkill = btn.dataset.skill;
    }
  });
  form.addEventListener("submit", (e) => {
    if (!selectedSkill) {
      e.preventDefault();
      alert("Please select a skill");
    } else {
      document.getElementById("selected-skill").value = selectedSkill;
    }
  });
});
