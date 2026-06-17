let domain = ""

chrome.storage.local.get("token", (data) => {
    if (data.token) {
        showMain()
    } else {
        showLogin()
    }
})

function authHeaders(token) {
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
    }
}

function showLogin() {
    document.getElementById("login-section").style.display = "block"
    document.getElementById("main-section").style.display = "none"

    document.getElementById("btn-login").addEventListener("click", () => {
        const email = document.getElementById("login-email").value
        const password = document.getElementById("login-password").value

        fetch("http://localhost:8000/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ email, password })
        })
        .then(res => res.json())
        .then(data => {
            if (data.access_token) {
                chrome.storage.local.set({token: data.access_token})
                showMain()
            } else {
                document.getElementById("login-error").textContent = "Invalid Credentials"
            }
        })
    })
}

function showMain() {
    document.getElementById("main-section").style.display = "block"
    document.getElementById("login-section").style.display = "none"

    chrome.storage.local.get("token", (data) => {
        const token = data.token
        document.getElementById("dashboard-link").href = `http://localhost:8501?token=${token}`
        function formatUsage(minutes) {
            if (minutes < 1) return `${Math.round(minutes * 60)}s`
            return `${minutes.toFixed(1)} mins`
        }

        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            domain = new URL(tabs[0].url).hostname.replace("www.", "")
            document.getElementById("domain").textContent = domain

            fetch("http://localhost:8000/limits", {
                headers: authHeaders(token)
            })
            .then(res => res.json())
            .then(limits => {
                const rule = limits.find(l => l.domain === domain)
                if (rule) {
                    const usages = document.getElementById("usage-info")
                    const displayMinutes = Math.min(rule.usage_today_minutes, rule.daily_limits)
                    usages.textContent = `⏱ ${formatUsage(displayMinutes)} / ${rule.daily_limits} mins used`

                    const pct = rule.usage_today_minutes / rule.daily_limits
                    if (pct >= 0.8 && !rule.is_blocked) {
                        const notifykey = `notified_${domain}_${rule.created_at}`
                        chrome.storage.local.get(notifykey, (data) => {
                            if (!data[notifykey]) {
                                chrome.notifications.create({
                                    type: "basic",
                                    iconUrl: "icon.png",
                                    title: "Limit Warning",
                                    message: `You've used ${rule.usage_today_minutes} of your ${rule.daily_limits} min limit on ${domain}`
                                })
                                chrome.storage.local.set({ [notifykey]: true })
                            }
                        })
                    }
                }
            })
        })

        function addRule(label) {
            fetch("http://localhost:8000/rules", {
                method: "POST",
                headers: authHeaders(token),
                body: JSON.stringify({domain: domain, label: label})
            })
            .then(res => res.json())
            .then(data => {
                const status = document.getElementById("status")
                status.textContent = data.status === "created" ? "✅ Rule saved!" : "⚠️ Rule already exists"
                status.className = data.status === "created" ? "status success" : "status warning"
            })
        }

        function setLimit() {
            const minutes = parseInt(document.getElementById("limit-input").value)
            const unit = document.getElementById("limit-unit").value
            const finalMinutes = unit === "hrs" ? minutes * 60 : minutes

            if (!finalMinutes || finalMinutes < 1) return

            fetch("http://localhost:8000/limits", {
                method: "POST",
                headers: authHeaders(token),
                body: JSON.stringify({domain: domain, daily_limits: finalMinutes})
            })
            .then(res => res.json())
            .then(data => {
                const status = document.getElementById("status")
                status.textContent = data.status === "successfully created" ? "Limit Set!": "Limit Updated!"
                status.className = "status success"
            })
        }

        document.getElementById("btn-productive").addEventListener("click", () => addRule("productive"))
        document.getElementById("btn-unproductive").addEventListener("click", () => addRule("unproductive"))
        document.getElementById("btn-neutral").addEventListener("click", () => addRule("neutral"))
        document.getElementById("btn-set-limit").addEventListener("click", setLimit)
    })
}