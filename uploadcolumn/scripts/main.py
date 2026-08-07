if value:
    result["字段"][field] = {
        "值": value,
        "置信度": confidence,
    }
else:
    # 缺失字段标注为需核实
    result["字段"][field] = {
        "值": f"[需核实:{field}]",
        "置信度": "low",
    }
