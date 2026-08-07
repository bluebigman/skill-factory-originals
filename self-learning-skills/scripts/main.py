# 测试用例 6：低置信度场景
test6 = {"title": "", "content": ""}
result6 = process_input(test6)
assert result6["status"] == "error", "测试6失败: 应该报错（空字段）"
print("  [OK] 测试6: 低置信度场景")
