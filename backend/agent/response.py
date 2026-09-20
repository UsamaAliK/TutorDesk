import json


def final_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
    return str(content)


def collect_sources(messages):
    sources = []
    for msg in messages:
        content = getattr(msg, "content", None)
        try:
            data = json.loads(content) if isinstance(content, str) else content
        except (json.JSONDecodeError, TypeError):
            continue

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("source"):
                    sources.append(str(item["source"]))
        elif isinstance(data, dict):
            sources.extend(
                str(s) for s in (data.get("sources") or [])
            )

    return list(dict.fromkeys(sources))