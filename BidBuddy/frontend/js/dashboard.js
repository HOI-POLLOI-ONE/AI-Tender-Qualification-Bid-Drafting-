document.addEventListener("DOMContentLoaded", () => {
    window.uploadTender = async function() {
        const file = document.getElementById("tenderFile").files[0];
        if (!file) return alert("Please select a file");

        const result = await uploadTenderAPI(file);
        document.getElementById("uploadResult").textContent =
            JSON.stringify(result, null, 2);
    };

    window.saveCompany = async function() {
        const turnover = document.getElementById("turnover").value;
        const networth = document.getElementById("networth").value;

        await saveCompanyAPI({
            turnover,
            net_worth: networth
        });

        alert("Company profile saved!");
    };

    window.checkCompliance = async function() {
        const data = await checkComplianceAPI();
        const score = data?.score || 0;

        animateScore(score);
    };
});

function animateScore(score) {
    const circle = document.getElementById("progressCircle");
    const text = document.getElementById("scoreText");

    const circumference = 339;
    const offset = circumference - (score / 100) * circumference;

    circle.style.strokeDashoffset = offset;

    let current = 0;
    const interval = setInterval(() => {
        if (current >= score) {
            clearInterval(interval);
        } else {
            current++;
            text.innerText = current + "%";
        }
    }, 15);
}
<script></script>
const fileInput = document.getElementById("fileInput");
const resultsSection = document.getElementById("resultsSection");
const uploadCard = document.getElementById("uploadCard");

fileInput.addEventListener("change", async () => {

  const file = fileInput.files[0];
  if (!file) return;

  uploadCard.innerHTML = "<h3>Analyzing Tender...</h3>";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("http://127.0.0.1:8000/analyze", {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    resultsSection.innerHTML = `
      <div class="result-card">
        <h3>Eligibility Score</h3>
        <div class="score">${data.score}%</div>
      </div>

      <div class="result-card">
        <h3>Key Requirements</h3>
        <ul>
          ${data.requirements.map(r => `<li>✔ ${r}</li>`).join("")}
        </ul>
      </div>
    `;

    resultsSection.style.display = "grid";
    uploadCard.style.display = "none";

  } catch (error) {
    uploadCard.innerHTML = "<h3>Error analyzing file.</h3>";
    console.error(error);
  }
});
