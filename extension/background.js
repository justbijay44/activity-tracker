let currentTab = null;
let startTime = null;
let isSending = false
let blockedDomains = new Set()

function sendSessions() {
    if (isSending) return
    isSending = true
    chrome.storage.local.get("sessions", (data) => {
        let sessions = data.sessions || []
        if (sessions.length == 0) {
            isSending = false
            return
        }
        console.log(`[SEND] ${sessions.length} sessions`)
        fetch("http://localhost:8000/sessions", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(sessions)
        })
        .then(res => res.json())
        .then(data => {
            console.log("Sent:", data)
            chrome.storage.local.set({ sessions: [] })
            isSending = false
        })
        .catch(err => {
            console.error("Failed to send:", err)
            isSending = false
        })
    })
}

function saveCurrentTabChunk() {
    if (currentTab != null && startTime != null) {
        if (!currentTab.url || currentTab.url == "" || currentTab.title === "New Tab" ||
            currentTab.url.startsWith("chrome://")){
            startTime = null
            return
        }
        
        let timeSpent = (Date.now() - startTime) / 1000
        console.log(`[SAVE] ${currentTab.title} - ${timeSpent.toFixed(1)}s`)
        chrome.storage.local.get(["sessions", "limits"], (data) => {
            let sessions = data.sessions || []
            let limits = data.limits || []
            sessions.push({ title: currentTab.title, url: currentTab.url, timeSpent})
            chrome.storage.local.set({ sessions })

            try {
                const domain = new URL(currentTab.url).hostname.replace("www.", "")
                const hasLimit = limits.find(l => l.domain === domain && !l.is_blocked)
                if (hasLimit) sendSessions()
            } catch(e) {
                console.log("[SKIP] Invalid URL for limit check:", currentTab?.url)
            }
        })
        startTime = null
    }
}

// on tab switch
chrome.tabs.onActivated.addListener((activeInfo) => {
    saveCurrentTabChunk()
    chrome.tabs.get(activeInfo.tabId, (tab) => {
        currentTab = tab
        startTime = Date.now()
        console.log(`[START] ${tab.title}`)
    });

});

// window focus lost/gained
chrome.windows.onFocusChanged.addListener((windowId) => {
    if (windowId == chrome.windows.WINDOW_ID_NONE) {
        console.log("[PAUSE] Left Browser")
        saveCurrentTabChunk()
    } else {
        console.log("[RESUME] Back in Browser")
        startTime = Date.now()
    }
})

// alarm sends batch
chrome.alarms.get("sendSessions", (alarm) => {
    if (!alarm) {
        chrome.alarms.create("sendSessions", { periodInMinutes: 5 })
    }
})

chrome.alarms.get("refreshBlocked", (alarm) => {
    if (!alarm) {
        chrome.alarms.create("refreshBlocked", { periodInMinutes: 0.5})
    }
})

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === "complete" && tab.active) {
        saveCurrentTabChunk()
        currentTab = tab
        startTime = Date.now()
        console.log(`[NAVIGATE] ${tab.title}`)
    }
})

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name == "refreshBlocked") {
        updateBlockedDomains()
    }
    
    if (alarm.name == "sendSessions") {
        saveCurrentTabChunk()
        startTime = Date.now()
        sendSessions()    
    }
})

function updateBlockedDomains() {
    fetch("http://localhost:8000/limits/check", { method: "POST" })
        .then(res => res.json())
        .then(result => {
            result.blocked.forEach(d => blockedDomains.add(d))
            if (result.blocked.length > 0) {
                chrome.tabs.query({}, (tabs) => {
                    tabs.forEach(tab => {
                        try {
                            const domain = new URL(tab.url).hostname.replace("www.", "")
                            if (result.blocked.includes(domain)) {
                                chrome.tabs.reload(tab.id)
                            }
                        } catch(e) {}
                    })
                })
            }
            return fetch("http://localhost:8000/limits")
        })
        .then(res => res.json())
        .then(data => {
            blockedDomains = new Set(data.filter(l => l.is_blocked).map(l => l.domain))
            chrome.storage.local.set({ 
                blockedDomains: [...blockedDomains],
                limits: data
            })
        })
}

chrome.webNavigation.onBeforeNavigate.addListener((details) => {
    if (details.frameId !== 0 ) return

    try {
        let domain = new URL(details.url).hostname.replace("www.", "")
        if (blockedDomains.has(domain)) {
            chrome.tabs.update(details.tabId, { url: chrome.runtime.getURL("blocked.html") })
        }
    } catch(e) {}
})

chrome.storage.local.get("blockedDomains", (data) => {
    if (data.blockedDomains) {
        blockedDomains = new Set(data.blockedDomains)
    }
    updateBlockedDomains()
})
