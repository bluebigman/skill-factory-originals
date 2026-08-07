for line in lines:
    for field, keywords in KEY_FIELD_RULES.items():
        if fields[field]:
            # 已提取过该字段，跳过
            continue
        for kw in keywords:
            # 匹配行首关键词
            if line.startswith(kw) and len(line) > len(kw):
                value = line[len(kw):].lstrip(":：- \t")
                if value:
                    fields[field] = value
                    break
