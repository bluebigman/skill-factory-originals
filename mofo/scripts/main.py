test2_input = "今天开会讨论了 #项目进度 @产品组 @开发组"
result2 = process_single(test2_input)
assert 'tags' in result2.fields, "E006: 标签提取失败"
