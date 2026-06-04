let currentTab = null;
let startTime = null;

function saveCurrentTabChunk() {
    if (currentTab != null && startTime != null) {
        if (!currentTab.url || currentTab.url == "" || currentTab.title === "New Tab" ||
            currentTab.url.startsWith("chrome://")){
            startTime = null
            return
        }
        
        let timeSpent = (Date.now() - startTime) / 1000
        console.log(`[SAVE] ${currentTab.title} - ${timeSpent.toFixed(1)}s`)
        chrome.storage.local.get("sessions", (data) => {
            let sessions = data.sessions || []
            sessions.push({ title: currentTab.title, url: currentTab.url, timeSpent})
            chrome.storage.local.set({ sessions })
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

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === "complete" && tab.active) {
        saveCurrentTabChunk()
        currentTab = tab
        startTime = Date.now()
        console.log(`[NAVIGATE] ${tab.title}`)
    }
})

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name == "sendSessions") {
        saveCurrentTabChunk()
        startTime = Date.now()

        chrome.storage.local.get("sessions", (data) => {
            let sessions = data.sessions || []
            console.log(`[SEND] ${sessions.length} sessions`)
            if (sessions.length === 0) return
            fetch("http://localhost:8000/sessions", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(sessions)
            })
            .then(res => res.json())
            .then(data => console.log("Sent:", data))
            .catch(err => console.error("Failed to send:", err))
            chrome.storage.local.set({ sessions: [] })
        })
    }
})
