const statusElement =
  document.getElementById("status");

function showStatus(message, isError = false) {
  statusElement.textContent = message;
  statusElement.style.color =
    isError ? "red" : "black";
}

async function sendMessage(message) {
  const response =
    await chrome.runtime.sendMessage(message);

  if (!response?.ok) {
    throw new Error(
      response?.error ?? "Unknown extension error"
    );
  }

  return response;
}

async function refreshStatus() {
  try {
    const status = await sendMessage({
      type: "GET_STATUS"
    });

    showStatus(
      [
        `Monitoring: ${
          status.monitoredTabId !== null
            ? "yes"
            : "no"
        }`,
        `Tab: ${status.monitoredTabId ?? "-"}`,
        `Captured requests: ${
          status.capturedRequests ?? 0
        }`,
        `Messages: ${status.messageCount ?? 0}`,
        `Destination: ${
          status.latestDestination ?? "-"
        }`
      ].join("\n")
    );
  } catch (error) {
    showStatus(error.message, true);
  }
}

document
  .getElementById("start")
  .addEventListener("click", async () => {
    try {
      const [tab] = await chrome.tabs.query({
        active: true,
        currentWindow: true
      });

      if (!tab?.id) {
        throw new Error(
          "Could not identify the active tab."
        );
      }

      await sendMessage({
        type: "START_MONITORING",
        tabId: tab.id
      });

      await refreshStatus();
    } catch (error) {
      showStatus(error.message, true);
    }
  });

document
  .getElementById("export")
  .addEventListener("click", async () => {
    try {
      const result = await sendMessage({
        type: "EXPORT_TASK"
      });

      showStatus(
        [
          "JSON exported.",
          `Steps: ${result.stepCount}`,
          `Errors: ${
            result.validation.errors.length
          }`,
          `Warnings: ${
            result.validation.warnings.length
          }`,
          ...result.validation.errors,
          ...result.validation.warnings
        ].join("\n")
      );
    } catch (error) {
      showStatus(error.message, true);
    }
  });

document
  .getElementById("stop")
  .addEventListener("click", async () => {
    try {
      await sendMessage({
        type: "STOP_MONITORING"
      });

      await refreshStatus();
    } catch (error) {
      showStatus(error.message, true);
    }
  });

refreshStatus();