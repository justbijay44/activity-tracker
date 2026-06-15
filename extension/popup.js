let domain = ""

chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    domain = new URL(tabs[0].url).hostname.replace("www.", "")
    document.getElementById("domain").textContent = domain
})

function addRule(label) {
    fetch("http://localhost:8000/rules", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({domain: domain, label: label})
    })
    .then(res => res.json())
    .then(data => {
        const status = document.getElementById("status")
        status.textContent = data.status === "created" ? "✅ Rule saved!" : "⚠️ Rule already exists"
        status.className = data.status === "created" ? "status success" : "status warning"
    })
}

document.getElementById("btn-productive").addEventListener("click", () => addRule("productive"))
document.getElementById("btn-unproductive").addEventListener("click", () => addRule("unproductive"))
document.getElementById("btn-neutral").addEventListener("click", () => addRule("neutral"))