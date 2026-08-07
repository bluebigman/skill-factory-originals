def validate_package(pkg: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = []
    
    for field in REQUIRED_FIELDS:
        value = pkg.get(field, "")
        if not value or value.startswith("[需核实:"):
            errors.append(f"必填字段缺失或未确定: {field}")
