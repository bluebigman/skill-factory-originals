assert "phones" in result.get("extracted_fields", {}), "应提取手机号"
assert "emails" in result.get("extracted_fields", {}), "应提取邮箱"
