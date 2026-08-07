# ---- 测试 4: 缺失关键信息触发 E002 ----
try:
    process_input({"title": "无数据点"})
    print("  [失败] 缺失数据点应触发 E002")
    return 1
except PlotSenseError as e:
    assert e.code == "E002", f"错误码应为 E002，实际 {e.code}"
    print("  [通过] 缺失关键信息错误处理 (E002)")
