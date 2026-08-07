# 测试 5: 错误处理
print("[5] 测试错误处理...")
try:
    parse_input([])
    assert False, "空输入应触发 E001"
except ValueError as e:
    assert str(e) == "E001", f"预期 E001，实际 {e}"
print("    通过")
