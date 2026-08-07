def _check_missing(self, record: ParsedRecord) -> bool:
    existing = {f.name for f in record.fields}
    missing = False

    for req in self.REQUIRED_FIELDS:
        if req not in existing:
            record.fields.append(ParsedField(
                name=req,
                value=f"[需核实:{req}]",
                confidence="low",
                source="missing"
            ))
            missing = True

    return missing
