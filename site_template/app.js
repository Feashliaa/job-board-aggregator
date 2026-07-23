const jobsElement = document.getElementById("jobs");
const statusElement = document.getElementById("status");
const searchElement = document.getElementById("search");

let jobs = [];

function text(value) {
  return value || "";
}

function render() {
  const query = searchElement.value.trim().toLowerCase();

  const visible = jobs.filter((job) =>
    `${text(job.title)} ${text(job.company)} ${text(job.location)}`
      .toLowerCase()
      .includes(query)
  );

  statusElement.textContent = `${visible.length.toLocaleString()} matching jobs`;

  jobsElement.innerHTML = visible.slice(0, 500).map((job) => `
    <a class="job" href="${job.url}" target="_blank" rel="noopener noreferrer">
      <div class="title">${text(job.title)}</div>
      <div class="meta">${text(job.company)} · ${text(job.location)} · ${text(job.ats)}</div>
    </a>
  `).join("");
}

fetch("jobs.json")
  .then((response) => response.json())
  .then((data) => {
    jobs = data;
    render();
  })
  .catch(() => {
    statusElement.textContent = "Could not load job data.";
  });

searchElement.addEventListener("input", render);