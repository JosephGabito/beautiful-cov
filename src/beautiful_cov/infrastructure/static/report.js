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
