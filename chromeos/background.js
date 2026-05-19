// Background service worker for Immortal Unzip ChromeOS extension.
// Handles file-open events and routes them to the main page.

chrome.action.onClicked.addListener(() => {
    chrome.tabs.create({ url: chrome.runtime.getURL('immortal-unzip.html') });
});
