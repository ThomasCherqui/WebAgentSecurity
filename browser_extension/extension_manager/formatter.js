function normalizeContent(content) {
  if (typeof content === "string") {
    return [
      {
        type: "text",
        text: content
      }
    ];
  }

  return Array.isArray(content) ? content : [];
}

function extractText(content) {
  if (typeof content === "string") {
    return content;
  }

  if (!Array.isArray(content)) {
    return "";
  }

  return content
    .filter(
      block =>
        block &&
        typeof block === "object" &&
        block.type === "text"
    )
    .map(block => block.text ?? "")
    .filter(Boolean)
    .join("\n");
}

function isInjectedContext(text) {
  return (
    text.startsWith("<system-reminder>") ||
    text.startsWith("<system>") ||
    text.includes("availableTabs")
  );
}

export function formatTask(messages) {
  const task = {
    user_input: null,
    injected_context: [],
    steps: [],
    final_output: null
  };

  const actionsById = new Map();
  let pendingAssistantText = null;

  for (const message of messages ?? []) {
    const role = message?.role;
    const blocks = normalizeContent(message?.content);

    for (const block of blocks) {
      if (!block || typeof block !== "object") {
        continue;
      }

      const type = block.type;

      if (role === "user" && type === "text") {
        const text = String(block.text ?? "").trim();

        if (!text) {
          continue;
        }

        if (isInjectedContext(text)) {
          task.injected_context.push(text);
        } else if (!task.user_input) {
          task.user_input = text;
        }

        continue;
      }

      if (role === "assistant" && type === "text") {
        const text = String(block.text ?? "").trim();

        if (text) {
          pendingAssistantText = text;
        }

        continue;
      }

      if (role === "assistant" && type === "tool_use") {
        const actionId = block.id ?? null;

        const step = {
          step_id: task.steps.length + 1,
          observable_reasoning: pendingAssistantText,
          action: {
            id: actionId,
            tool: block.name ?? null,
            input: block.input ?? {}
          },
          observation: null
        };

        task.steps.push(step);

        if (actionId) {
          actionsById.set(actionId, step);
        }

        pendingAssistantText = null;
        continue;
      }

      if (role === "user" && type === "tool_result") {
        const actionId = block.tool_use_id ?? null;
        const matchingStep = actionsById.get(actionId);

        const observation = {
          tool_use_id: actionId,
          content: extractText(block.content),
          is_error: Boolean(block.is_error)
        };

        if (matchingStep) {
          matchingStep.observation = observation;
        } else {
          task.steps.push({
            step_id: task.steps.length + 1,
            observable_reasoning: null,
            action: {
              id: actionId,
              tool: null,
              input: null
            },
            observation
          });
        }
      }
    }
  }

  /*
   * Un texte assistant non suivi d'un tool_use peut être une réponse finale.
   * Ce n'est qu'une heuristique.
   */
  if (pendingAssistantText) {
    task.final_output = pendingAssistantText;
  }

  return task;
}

export function validateTask(task) {
  const errors = [];
  const warnings = [];
  const actionIds = new Set();

  if (!task.user_input) {
    errors.push("Missing user_input");
  }

  if (!Array.isArray(task.steps)) {
    errors.push("steps must be an array");
    return { errors, warnings };
  }

  for (const [index, step] of task.steps.entries()) {
    const number = index + 1;

    if (!step.action) {
      errors.push(`Step ${number}: missing action`);
      continue;
    }

    if (!step.action.tool) {
      warnings.push(`Step ${number}: missing tool name`);
    }

    const actionId = step.action.id;

    if (actionId) {
      if (actionIds.has(actionId)) {
        errors.push(
          `Step ${number}: duplicate action id ${actionId}`
        );
      }

      actionIds.add(actionId);
    }

    if (!step.observation) {
      warnings.push(`Step ${number}: missing observation`);
    }
  }

  if (!task.final_output) {
    warnings.push("No final output extracted");
  }

  return { errors, warnings };
}