elif result.get("type") == "text":
    lines.append(f"  类型: 文本")
    lines.append(f"  行数: {result.get('lines', 0)}")
    lines.append(f"  字符数: {result.get('characters', 0)}")
    structured = result.get("structured", {})
    if structured.get("first_line"):
        lines.append(f"  首行: {structured['first_line'][:50]}")
    if structured.get("last_line"):
        lines.append(f"  末行: {structured['last_line'][:50]}")
