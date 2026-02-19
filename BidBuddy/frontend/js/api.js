const API = "http://localhost:8000";

async function uploadTender(){
  const file = document.getElementById("tenderFile").files[0];
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API}/tenders/upload`, {
    method:"POST",
    body:formData
  });

  const data = await res.json();
  document.getElementById("uploadResult").textContent =
    JSON.stringify(data,null,2);
}

async function saveCompany(){
  await fetch(`${API}/companies`,{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      turnover: turnover.value,
      net_worth: networth.value
    })
  });
}

async function checkCompliance(){
  const res = await fetch(`${API}/compliance/score`,{
    method:"POST"
  });

  const data = await res.json();
  let score = data.score || 75;

  const circle = document.getElementById("progressCircle");
  const offset = 339 - (339 * score)/100;
  circle.style.strokeDashoffset = offset;
  document.getElementById("scoreText").innerText = score+"%";
}

async function generateDraft(){
  const res = await fetch(`${API}/copilot/generate-draft`,{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({})
  });

  const data = await res.json();
  document.getElementById("proposalText").value =
    data.draft || "Generated";
}

async function askAI(){
  const input = document.getElementById("chatInput").value;
  const box = document.getElementById("chatBox");

  box.innerHTML += `<div class='user'>${input}</div>`;

  const res = await fetch(`${API}/copilot/ask`,{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({question:input})
  });

  const data = await res.json();
  box.innerHTML += `<div class='ai'>${data.answer}</div>`;

  chatInput.value="";
}
