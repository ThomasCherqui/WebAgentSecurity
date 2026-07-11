import {
  formatTask,
  validateTask
} from "./formatter.js";

const DEBUGGER_VERSION = "1.3";

async function getState() {
  const result = await chrome.storage.local.get({
    monitoredTabId: null,
    latestMessages: [],
    latestDestination: null,
    capturedRequests: 0
  });

  return result;
}

async function updateState(patch) {
  await chrome.storage.local.set(patch);
}

async function startMonitoring(tabId) {
  const state = await getState();

  if (state.monitoredTabId !== null) {
    throw new Error(
      `Already monitoring tab ${state.monitoredTabId}`
    );
  }

  await chrome.debugger.attach(
    { tabId },
    DEBUGGER_VERSION
  );

  await chrome.debugger.sendCommand(
    { tabId },
    "Network.enable",
    {
      maxTotalBufferSize: 100_000_000,
      maxResourceBufferSize: 10_000_000,
      maxPostDataSize: 10_000_000
    }
  );

  await updateState({
    monitoredTabId: tabId,
    latestMessages: [],
    latestDestination: null,
    capturedRequests: 0
  });

  console.log("Monitoring started on tab", tabId);
}

async function stopMonitoring() {
  const state = await getState();

  if (state.monitoredTabId === null) {
    return;
  }

  try {
    await chrome.debugger.detach({
      tabId: state.monitoredTabId
    });
  } catch (error) {
    console.warn("Debugger detach failed:", error);
  }

  await updateState({
    monitoredTabId: null
  });

  console.log("Monitoring stopped");
}

function safeJsonParse(value) {
  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function looksLikeLlmPayload(body) {
  return (
    body &&
    typeof body === "object" &&
    Array.isArray(body.messages)
  );
}

async function retrieveRequestBody(tabId, params) {
  if (params.request.postData) {
    return params.request.postData;
  }

  if (!params.request.hasPostData) {
    return null;
  }

  try {
    const result = await chrome.debugger.sendCommand(
      { tabId },
      "Network.getRequestPostData",
      {
        requestId: params.requestId
      }
    );

    return result?.postData ?? null;
  } catch (error) {
    console.warn(
      "Could not retrieve request body:",
      error
    );

    return null;
  }
}

async function handleRequest(tabId, params) {
  const request = params.request;

  if (!["POST", "PUT", "PATCH"].includes(request.method)) {
    return;
  }

  const rawBody = await retrieveRequestBody(
    tabId,
    params
  );

  const body = safeJsonParse(rawBody);

  if (!looksLikeLlmPayload(body)) {
    return;
  }

  const state = await getState();
  const previousMessages = state.latestMessages ?? [];
  const newMessages = body.messages;

  /*
   * Les appels agentiques sont souvent cumulatifs.
   * On garde donc le payload ayant le plus de messages.
   */
  if (newMessages.length >= previousMessages.length) {
    await updateState({
      latestMessages: newMessages,
      latestDestination: request.url,
      capturedRequests:
        Number(state.capturedRequests ?? 0) + 1
    });

    console.log(
      "LLM payload captured:",
      request.url,
      `${newMessages.length} messages`
    );
  }
}

chrome.debugger.onEvent.addListener(
  async (source, method, params) => {
    const state = await getState();

    if (
      source.tabId !== state.monitoredTabId ||
      method !== "Network.requestWillBeSent"
    ) {
      return;
    }

    try {
      await handleRequest(source.tabId, params);
    } catch (error) {
      console.error("Request processing failed:", error);
    }
  }
);

chrome.debugger.onDetach.addListener(
  async source => {
    const state = await getState();

    if (source.tabId === state.monitoredTabId) {
      await updateState({
        monitoredTabId: null
      });
    }
  }
);

async function exportFormattedTask() {
  const state = await getState();

  if (!state.latestMessages?.length) {
    throw new Error(
      "No LLM messages captured. Start monitoring and run a task first."
    );
  }

  const formattedTask = formatTask(
    state.latestMessages
  );

  const validation = validateTask(formattedTask);

  const exportPayload = {
    metadata: {
      exported_at: new Date().toISOString(),
      destination: state.latestDestination,
      captured_requests: state.capturedRequests,
      validation
    },
    task: formattedTask
  };

  console.log(
    "FORMATTED TASK",
    JSON.stringify(exportPayload, null, 2)
  );

  const json = JSON.stringify(
    exportPayload,
    null,
    2
  );

  const dataUrl =
    "data:application/json;charset=utf-8," +
    encodeURIComponent(json);

  await chrome.downloads.download({
    url: dataUrl,
    filename: `formatted-task-${Date.now()}.json`,
    saveAs: true
  });

  return exportPayload;
}

chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {
    const run = async () => {
      if (message.type === "START_MONITORING") {
        await startMonitoring(message.tabId);

        return {
          ok: true
        };
      }

      if (message.type === "STOP_MONITORING") {
        await stopMonitoring();

        return {
          ok: true
        };
      }

      if (message.type === "EXPORT_TASK") {
        const result = await exportFormattedTask();

        return {
          ok: true,
          validation: result.metadata.validation,
          stepCount: result.task.steps.length
        };
      }

      if (message.type === "GET_STATUS") {
        const state = await getState();

        return {
          ok: true,
          ...state,
          latestMessages: undefined,
          messageCount:
            state.latestMessages?.length ?? 0
        };
      }

      throw new Error(
        `Unknown message type: ${message.type}`
      );
    };

    run()
      .then(sendResponse)
      .catch(error => {
        console.error(error);

        sendResponse({
          ok: false,
          error: error.message
        });
      });

    return true;
  }
);