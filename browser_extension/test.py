import json
from pathlib import Path
from typing import Any


HAR_PATH = Path("browser_extension/fcoeoabgfenejglbffodgkkbkcdhcgfn.har")
OUTPUT_PATH = Path("formatted_task.json")


def parse_json_body(entry: dict[str, Any]) -> dict[str, Any] | None:
    post_data = entry.get("request", {}).get("postData", {})
    raw_text = post_data.get("text")

    if not raw_text:
        return None

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return None


def extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []

        for item in content:
            if not isinstance(item, dict):
                continue

            if item.get("type") == "text":
                text = item.get("text")
                if text:
                    parts.append(text)

        return "\n".join(parts)

    return ""


def content_signature(role: str, block: dict[str, Any]) -> str:
    return json.dumps(
        {
            "role": role,
            "block": block,
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def format_messages(messages: list[dict[str, Any]]) -> dict[str, Any]:
    task: dict[str, Any] = {
        "user_input": None,
        "steps": [],
        "final_output": None,
    }

    seen_blocks: set[str] = set()
    pending_actions: dict[str, dict[str, Any]] = {}
    latest_reasoning: str | None = None

    for message in messages:
        role = message.get("role")
        content = message.get("content", [])

        if isinstance(content, str):
            content = [{"type": "text", "text": content}]

        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue

            signature = content_signature(role, block)

            if signature in seen_blocks:
                continue

            seen_blocks.add(signature)

            block_type = block.get("type")

            if role == "user" and block_type == "text":
                text = block.get("text", "").strip()

                # Ignore le contexte technique injecté.
                if text and not text.startswith("<system-reminder>"):
                    if task["user_input"] is None:
                        task["user_input"] = text

            elif role == "assistant" and block_type == "text":
                text = block.get("text", "").strip()

                if text:
                    latest_reasoning = text

            elif role == "assistant" and block_type == "tool_use":
                tool_use_id = block.get("id")

                step = {
                    "step_id": len(task["steps"]) + 1,
                    "observable_reasoning": latest_reasoning,
                    "action": {
                        "id": tool_use_id,
                        "tool": block.get("name"),
                        "input": block.get("input", {}),
                    },
                    "observation": None,
                }

                task["steps"].append(step)

                if tool_use_id:
                    pending_actions[tool_use_id] = step

                latest_reasoning = None

            elif role == "user" and block_type == "tool_result":
                tool_use_id = block.get("tool_use_id")
                step = pending_actions.get(tool_use_id)

                observation = {
                    "tool_use_id": tool_use_id,
                    "content": extract_text(block.get("content")),
                    "is_error": block.get("is_error", False),
                }

                if step:
                    step["observation"] = observation

            elif role == "assistant" and block_type == "text":
                pass

    # Si le dernier texte assistant n'est associé à aucune action,
    # on le considère provisoirement comme output final.
    if latest_reasoning:
        task["final_output"] = latest_reasoning

    return task


def find_latest_messages(har: dict[str, Any]) -> list[dict[str, Any]]:
    best_messages: list[dict[str, Any]] = []

    entries = har.get("log", {}).get("entries", [])

    for entry in entries:
        body = parse_json_body(entry)

        if not body:
            continue

        messages = body.get("messages")

        if not isinstance(messages, list):
            continue

        # Le dernier payload contient normalement l'historique le plus complet.
        if len(messages) > len(best_messages):
            best_messages = messages

    return best_messages


def validate_task(task: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if not task.get("user_input"):
        errors.append("Missing user_input")

    steps = task.get("steps")

    if not isinstance(steps, list) or not steps:
        errors.append("No steps extracted")
        return errors

    action_ids: set[str] = set()

    for index, step in enumerate(steps, start=1):
        action = step.get("action")

        if not action:
            errors.append(f"Step {index}: missing action")
            continue

        action_id = action.get("id")

        if action_id:
            if action_id in action_ids:
                errors.append(f"Step {index}: duplicate action id {action_id}")

            action_ids.add(action_id)

        if not action.get("tool"):
            errors.append(f"Step {index}: missing tool name")

        if step.get("observation") is None:
            errors.append(f"Step {index}: missing observation")

    return errors


def main() -> None:
    with HAR_PATH.open("r", encoding="utf-8") as file:
        har = json.load(file)

    messages = find_latest_messages(har)
    task = format_messages(messages)
    errors = validate_task(task)

    OUTPUT_PATH.write_text(
        json.dumps(task, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Formatted task written to: {OUTPUT_PATH}")
    print(f"Input: {task['user_input']}")
    print(f"Steps: {len(task['steps'])}")
    print(f"Final output present: {task['final_output'] is not None}")

    if errors:
        print("\nValidation errors:")
        for error in errors:
            print(f"- {error}")
    else:
        print("\nFormatting validation passed.")


if __name__ == "__main__":
    main()