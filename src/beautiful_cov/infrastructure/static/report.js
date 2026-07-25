const search = document.querySelector("#content-search");

if (search) {
  const rows = [...document.querySelectorAll("#content-rows tr")];
  const emptyState = document.querySelector("#empty-state");

  search.addEventListener("input", () => {
    const query = search.value.trim().toLowerCase();
    let visible = 0;

    for (const row of rows) {
      const show = row.dataset.search.includes(query);
      row.hidden = !show;
      visible += Number(show);
    }

    emptyState.style.display = visible ? "none" : "block";
  });
}

const contextData = document.querySelector("#test-context-data");
let testContexts = [];

if (contextData) {
  try {
    testContexts = JSON.parse(contextData.textContent);
  } catch {
    testContexts = [];
  }
}

function renderContextEvidence(contexts) {
  if (contexts.dataset.rendered === "true") {
    return;
  }

  const contextIds = contexts.dataset.contextIds
    .split(",")
    .filter(Boolean)
    .map(Number);
  const hiddenContexts = Number(contexts.dataset.hiddenContexts);
  const totalContexts = contextIds.length + hiddenContexts;
  const inner = document.createElement("div");
  const heading = document.createElement("strong");
  const list = document.createElement("ul");

  inner.className = "line-contexts-inner";
  heading.textContent =
    `Covered by ${totalContexts} ${totalContexts === 1 ? "test" : "tests"}`;
  inner.append(heading);

  for (const contextId of contextIds) {
    const context = testContexts[contextId];
    if (typeof context !== "string") {
      continue;
    }

    const item = document.createElement("li");
    const code = document.createElement("code");
    code.textContent = context;
    item.append(code);
    list.append(item);
  }

  inner.append(list);

  if (hiddenContexts) {
    const remainder = document.createElement("p");
    remainder.textContent =
      `${hiddenContexts} additional ` +
      `${hiddenContexts === 1 ? "context" : "contexts"}`;
    inner.append(remainder);
  }

  contexts.append(inner);
  contexts.dataset.rendered = "true";
}

for (const toggle of document.querySelectorAll("[data-context-toggle]")) {
  toggle.addEventListener("click", () => {
    const contextId = toggle.getAttribute("aria-controls");
    const contexts = document.getElementById(contextId);
    const expanded = toggle.getAttribute("aria-expanded") === "true";

    if (!expanded) {
      renderContextEvidence(contexts);
    }

    toggle.setAttribute("aria-expanded", String(!expanded));
    contexts.hidden = expanded;
  });
}

const missingLines = [
  ...document.querySelectorAll('[data-line-status="missing"]'),
];

for (const control of document.querySelectorAll("[data-missing-nav]")) {
  control.addEventListener("click", () => {
    if (!missingLines.length) {
      return;
    }

    const currentHash = window.location.hash;
    const currentIndex = missingLines.findIndex(
      (line) => `#${line.id}` === currentHash,
    );
    const direction = control.dataset.missingNav === "next" ? 1 : -1;
    const fallback = direction > 0 ? -1 : 0;
    const nextIndex =
      (currentIndex === -1 ? fallback : currentIndex) + direction;
    const wrappedIndex =
      (nextIndex + missingLines.length) % missingLines.length;
    const target = missingLines[wrappedIndex];

    window.location.hash = target.id;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}
