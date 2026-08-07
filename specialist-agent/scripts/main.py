except ValueError as e:
    error_code = str(e).split(":")[0] if ":" in str(e) else "E006"
