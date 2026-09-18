/**
 * Chrome Extension Backup Pro - Background Service Worker (Manifest V3)
 * Bridges extension UI requests to the Windows Native Messaging Host ("com.extbackup.pro"),
 * manages periodic alarms, change monitoring, and Windows notifications.
 */

const NATIVE_HOST_NAME = "com.extbackup.pro";

// Handle installation & startup
chrome.runtime.onInstalled.addListener((details) => {
  console.log("[Service Worker] Extensão instalada/atualizada:", details.reason);
  // Setup alarm for periodic change detection (every 60 minutes)
  chrome.alarms.create("check_extension_changes", { periodInMinutes: 60 });
});

// Periodic alarm handler
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "check_extension_changes") {
    try {
      const response = await sendNativeMessageToHost({ action: "check_for_changes", payload: {} });
      if (response && response.changes_detected && response.changes.length > 0) {
        const change = response.changes[0];
        chrome.notifications.create({
          type: "basic",
          iconUrl: chrome.runtime.getURL("ui/icons/icon128.png"),
          title: "Alteração de Extensão Detetada",
          message: change.message || `A extensão ${change.name} foi atualizada. Deseja criar um novo backup?`,
          priority: 1
        });
      }
    } catch (e) {
      console.warn("[Service Worker] Erro no check de alterações agendado:", e);
    }
  }
});

// Send native message helper wrapped in Promise
function sendNativeMessageToHost(message) {
  return new Promise((resolve, reject) => {
    try {
      chrome.runtime.sendNativeMessage(NATIVE_HOST_NAME, message, (response) => {
        if (chrome.runtime.lastError) {
          return reject(new Error(chrome.runtime.lastError.message));
        }
        resolve(response);
      });
    } catch (err) {
      reject(err);
    }
  });
}

// Runtime message listener from UI pages (popup / full-tab dashboard)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // Handle opening full tab
  if (request.action === "open_full_tab") {
    chrome.tabs.create({ url: chrome.runtime.getURL("ui/index.html") });
    sendResponse({ success: true });
    return true;
  }

  // Handle native notification request from UI
  if (request.action === "show_notification") {
    const { title, message, type } = request.payload || {};
    chrome.notifications.create({
      type: "basic",
      iconUrl: chrome.runtime.getURL("ui/icons/icon128.png"),
      title: title || "Chrome Extension Backup Pro",
      message: message || "",
      priority: type === "error" ? 2 : 1
    });
    sendResponse({ success: true });
    return true;
  }

  // Forward native command to Native Host
  sendNativeMessageToHost(request)
    .then((response) => {
      sendResponse(response);
    })
    .catch((error) => {
      sendResponse({
        success: false,
        error: {
          code: "NT-0001",
          title: "Erro de Comunicação com Componente Local",
          description: error.message || "Não foi possível comunicar com o Native Messaging Host com.extbackup.pro.",
          solution: "Execute o ficheiro 'install_host.bat' no Windows para registar o componente local."
        }
      });
    });

  return true; // Keep message channel open for async sendResponse
});
