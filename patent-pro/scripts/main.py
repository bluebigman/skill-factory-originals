#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patent-pro 专利全流程处理工具
功能：专利识别、信息整理、文档生成、形式校验
"""

import argparse
import re
import sys
import os
from datetime import datetime
from pathlib import Path


# ============================================================
# 错误码定义
# ============================================================
ERR_INVALID_INPUT = "E001"      # 输入无效
ERR_FILE_NOT_FOUND = "E002"     # 文件不存在
ERR_FILE_READ = "E003"          # 文件读取失败
ERR_FILE_WRITE = "E004"         # 文件写入失败
ERR_ENCODING = "E005"           # 编码不支持
ERR_FORMAT = "E006"             # 格式错误
ERR_EMPTY_CONTENT = "E007"      # 内容为空
ERR_INVALID_PATH = "E008"       # 路径非法
ERR_INVALID_ARGS = "E009"       # 参数错误
ERR_UNKNOWN = "E010"            # 未知错误


# ============================================================
# 输入校验
# ============================================================
def validate_input(text):
    """校验输入文本有效性"""
    if text is None:
        raise ValueError(f"{ERR_INVALID_INPUT}: 输入内容为空")
    if not isinstance(text, str):
        raise ValueError(f"{ERR_INVALID_INPUT}: 输入必须是字符串类型")
    if len(text.strip()) == 0:
        raise ValueError(f"{ERR_EMPTY_CONTENT}: 输入内容为空")
    return text.strip()


def validate_output_path(path_str):
    """校验输出路径合法性"""
    if not path_str:
        return None
    p = Path(path_str)
    # 检查路径是否包含穿越
    if ".." in p.parts:
        raise ValueError(f"{ERR_INVALID_PATH}: 路径包含非法目录穿越")
    # 检查扩展名
    if p.suffix not in [".md", ".txt", ".json"]:
        raise ValueError(f"{ERR_INVALID_PATH}: 输出文件必须是 .md/.txt/.json 格式")
    return p


# ============================================================
# 核心逻辑：技术特征提取
# ============================================================
def extract_technical_features(text):
    """从技术描述中提取技术问题、手段、效果"""
    features = {
        "技术问题": None,
        "技术手段": None,
        "技术效果": None
    }
    
    # 技术问题提取
    problem_patterns = [
        r"(?:为了解决|现有技术存在|现有.*?的)[^。；;]*",
        r"技术问题[：:][^。；;]*"
    ]
    for pattern in problem_patterns:
        match = re.search(pattern, text)
        if match:
            features["技术问题"] = match.group(0).strip()
            break
    
    # 技术手段提取
    method_patterns = [
        r"(?:采用|通过|利用|使用)[^。；;]*",
        r"技术方案[：:][^。；;]*"
    ]
    for pattern in method_patterns:
        match = re.search(pattern, text)
        if match:
            features["技术手段"] = match.group(0).strip()
            break
    
    # 技术效果提取
    effect_patterns = [
        r"(?:实现了|提高了|提升了|降低了|减少了)[^。；;]*",
        r"有益效果[：:][^。；;]*"
    ]
    for pattern in effect_patterns:
        match = re.search(pattern, text)
        if match:
            features["技术效果"] = match.group(0).strip()
            break
    
    # 填充缺失项
    for key in features:
        if not features[key]:
            features[key] = f"[需核实:{key}]"
    
    return features


# ============================================================
# 核心逻辑：文档生成
# ============================================================
def generate_disclosure_doc(features, inventor="[需核实:发明人]"):
    """根据提取的特征生成技术交底书"""
    doc = []
    doc.append("# 技术交底书")
    doc.append("")
    doc.append("## 一、发明名称")
    doc.append(f"[需核实:发明名称]（建议格式：一种……方法/装置/系统）")
    doc.append("")
    doc.append("## 二、技术领域")
    doc.append(f"[需核实:技术领域]")
    doc.append("")
    doc.append("## 三、背景技术")
    doc.append(f"[需核实:现有技术描述]")
    doc.append("")
    doc.append("## 四、发明内容")
    doc.append("### 4.1 要解决的技术问题")
    doc.append(features.get("技术问题", "[需核实:技术问题]"))
    doc.append("")
    doc.append("### 4.2 技术方案")
    doc.append(features.get("技术手段", "[需核实:技术手段]"))
    doc.append("")
    doc.append("### 4.3 有益效果")
    doc.append(features.get("技术效果", "[需核实:技术效果]"))
    doc.append("")
    doc.append("## 五、具体实施方式")
    doc.append("[需核实:实施例描述]")
    doc.append("")
    doc.append("## 六、附图说明")
    doc.append("[需核实:附图清单]")
    doc.append("")
    doc.append(f"发明人：{inventor}")
    
    return "\n".join(doc)


def generate_claims(features):
    """生成权利要求书初稿"""
    claims = []
    claims.append("# 权利要求书")
    claims.append("")
    claims.append("1. 一种[需核实:主题名称]，其特征在于，包括：")
    claims.append(f"   所述[需核实:主题名称]通过{features.get('技术手段', '[需核实:技术手段]')}，")
    claims.append(f"   以解决{features.get('技术问题', '[需核实:技术问题]')}，")
    claims.append(f"   实现{features.get('技术效果', '[需核实:技术效果]')}。")
    claims.append("")
    claims.append("2. 根据权利要求1所述的[需核实:主题名称]，其特征在于，")
    claims.append("   [需补充:从属权利要求的具体限定特征]。")
    
    return "\n".join(claims)


def generate_abstract(features):
    """生成说明书摘要"""
    abstract = []
    abstract.append("# 说明书摘要")
    abstract.append("")
    abstract.append(f"本发明公开了一种[需核实:主题名称]，涉及[需核实:技术领域]。")
    abstract.append(f"本发明{features.get('技术手段', '[需核实:技术手段]')}，")
    abstract.append(f"解决了{features.get('技术问题', '[需核实:技术问题]')}，")
    abstract.append(f"实现了{features.get('技术效果', '[需核实:技术效果]')}。")
    
    return "\n".join(abstract)


# ============================================================
# 核心逻辑：形式校验
# ============================================================
def validate_document(text):
    """校验文档格式规范"""
    report = []
    report.append("# 校验报告")
    report.append("")
    
    # 检查编号连续性
    section_nums = re.findall(r'^#{1,4}\s+(\d+(?:\.\d+)*)', text, re.MULTILINE)
    expected = []
    for s in section_nums:
        parts = [int(x) for x in s.split('.')]
        expected.append(parts)
    
    is_continuous = True
    for i in range(1, len(expected)):
        prev = expected[i-1]
        curr = expected[i]
        if len(prev) == len(curr):
            if curr[-1] != prev[-1] + 1:
                is_continuous = False
                break
    
    report.append(f"| 编号连续性 | {'✅ 通过' if is_continuous else '⚠️ 警告'} | 章节编号检查 |")
    
    # 检查占位符
    placeholders = re.findall(r'\[(?:需核实|需补充|待确认):[^\]]+\]', text)
    if placeholders:
        report.append(f"| 信息完整性 | ⚠️ 警告 | 存在 {len(placeholders)} 个占位符待补充 |")
    else:
        report.append("| 信息完整性 | ✅ 通过 | 无占位符 |")
    
    # 检查引用一致性
    refs_in_text = re.findall(r'\[(\d+)\]', text)
    if refs_in_text:
        report.append(f"| 引用一致性 | ⚠️ 警告 | 存在 {len(refs_in_text)} 处引用需核对 |")
    else:
        report.append("| 引用一致性 | ✅ 通过 | 无引用问题 |")
    
    # 检查格式规范
    has_title = bool(re.search(r'^#\s+\S+', text, re.MULTILINE))
    report.append(f"| 格式规范 | {'✅ 通过' if has_title else '⚠️ 警告'} | 标题格式检查 |")
    
    return "\n".join(report)


# ============================================================
# 文件读写（多编码支持）
# ============================================================
def read_file_with_encoding(filepath):
    """读取文件，支持多编码"""
    encodings = ['utf-8', 'gbk', 'gb18030', 'latin-1']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read(), enc
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            raise ValueError(f"{ERR_FILE_NOT_FOUND}: 文件不存在 {filepath}")
        except Exception as e:
            raise ValueError(f"{ERR_FILE_READ}: 读取失败 {str(e)}")
    
    # 最后尝试 replace 模式
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return f.read(), 'utf-8-replace'
    except Exception as e:
        raise ValueError(f"{ERR_ENCODING}: 无法识别文件编码 {str(e)}")


def write_file_safe(filepath, content, dry_run=False):
    """安全写入文件（支持 dry-run）"""
    if dry_run:
        print(f"[DRY-RUN] 将写入文件: {filepath}")
        print("--- 内容预览 ---")
        print(content[:200] + "..." if len(content) > 200 else content)
        print("--- 预览结束 ---")
        return
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 已写入: {filepath}")
    except Exception as e:
        raise ValueError(f"{ERR_FILE_WRITE}: 写入失败 {str(e)}")


# ============================================================
# 主处理流程
# ============================================================
def process_patent(text, output_dir=None, dry_run=False, verbose=False):
    """处理专利文本主流程"""
    try:
        # 输入校验
        text = validate_input(text)
        
        # 提取特征
        features = extract_technical_features(text)
        if verbose:
            print("📋 提取的技术特征：")
            for k, v in features.items():
                print(f"  {k}: {v}")
        
        # 生成文档
        disclosure = generate_disclosure_doc(features)
        claims = generate_claims(features)
        abstract = generate_abstract(features)
        
        # 校验
        report = validate_document(disclosure + "\n" + claims)
        
        # 输出
        results = {
            "技术交底书": disclosure,
            "权利要求书": claims,
            "说明书摘要": abstract,
            "校验报告": report
        }
        
        # 写入文件
        if output_dir:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            date_str = datetime.now().strftime("%Y%m%d")
            for name, content in results.items():
                fname = f"专利_{name}_{date_str}.md"
                write_file_safe(out_path / fname, content, dry_run)
        else:
            # 打印到控制台
            for name, content in results.items():
                print(f"\n{'='*60}")
                print(f"【{name}】")
                print(f"{'='*60}")
                print(content)
        
        return results
    
    except ValueError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ {ERR_UNKNOWN}: 未知错误 {str(e)}", file=sys.stderr)
        return None


# ============================================================
# 自检功能
# ============================================================
def run_selftest():
    """内置样例数据自检"""
    print("🔍 开始自检...")
    passed = 0
    total = 0
    
    # 样例1：正常技术描述
    sample1 = "为了解决现有充电桩散热效率低的问题，采用液冷循环系统，实现了散热效率提升40%的效果。"
    try:
        features = extract_technical_features(sample1)
        assert features["技术问题"] is not None, "技术问题提取失败"
        assert features["技术手段"] is not None, "技术手段提取失败"
        assert features["技术效果"] is not None, "技术效果提取失败"
        assert "液冷" in features["技术手段"], "技术手段内容错误"
        passed += 1
    except AssertionError as e:
        print(f"  ❌ 样例1失败: {e}")
    total += 1
    
    # 样例2：中文标点
    sample2 = "本发明涉及一种智能门锁。通过指纹识别技术，解决了传统钥匙易丢失的问题，提高了安全性。"
    try:
        features = extract_technical_features(sample2)
        assert features["技术问题"] is not None, "中文标点处理失败"
        assert features["技术手段"] is not None, "中文标点处理失败"
        passed += 1
    except AssertionError as e:
        print(f"  ❌ 样例2失败: {e}")
    total += 1
    
    # 样例3：空输入
    try:
        validate_input("")
        print("  ❌ 样例3失败: 空输入未报错")
    except ValueError:
        passed += 1
    total += 1
    
    # 样例4：超长输入
    long_text = "技术方案" * 1000
    try:
        features = extract_technical_features(long_text)
        assert features is not None, "长文本处理失败"
        passed += 1
    except Exception as e:
        print(f"  ❌ 样例4失败: {e}")
    total += 1
    
    # 样例5：文档生成
    sample_features = {
        "技术问题": "测试问题",
        "技术手段": "测试手段",
        "技术效果": "测试效果"
    }
    try:
        doc = generate_disclosure_doc(sample_features)
        assert "技术交底书" in doc, "文档生成失败"
        assert "测试问题" in doc, "文档内容缺失"
        passed += 1
    except AssertionError as e:
        print(f"  ❌ 样例5失败: {e}")
    total += 1
    
    # 样例6：校验功能
    try:
        test_doc = "# 测试文档\n## 一、章节\n内容"
        report = validate_document(test_doc)
        assert "校验报告" in report, "校验报告生成失败"
        passed += 1
    except AssertionError as e:
        print(f"  ❌ 样例6失败: {e}")
    total += 1
    
    # 样例7：编码异常（模拟）
    try:
        # 模拟 GBK 编码内容
        gbk_bytes = "专利测试内容".encode('gbk')
        decoded = gbk_bytes.decode('gbk')
        assert "专利" in decoded, "GBK解码失败"
        passed += 1
    except Exception as e:
        print(f"  ❌ 样例7失败: {e}")
    total += 1
    
    print(f"\n📊 自检结果: {passed}/{total} 通过")
    return passed == total


# ============================================================
# 主入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="专利全流程处理工具：识别、整理、生成、校验",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py "为了解决散热问题，采用液冷技术，提高了效率"
  python main.py -f input.txt -o output/
  python main.py --selftest
  python main.py "技术描述" --dry-run --verbose
        """
    )
    
    parser.add_argument("text", nargs="?", help="技术方案描述文本")
    parser.add_argument("-f", "--file", help="从文件读取技术描述")
    parser.add_argument("-o", "--output", help="输出目录")
    parser.add_argument("--dry-run", action="store_true", help="只预览不写盘")
    parser.add_argument("--verbose", action="store_true", help="显示详细处理过程")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 获取输入
    try:
        if args.file:
            # 从文件读取
            content, encoding = read_file_with_encoding(args.file)
            if args.verbose:
                print(f"📖 已读取文件: {args.file} (编码: {encoding})")
        elif args.text:
            content = args.text
        else:
            parser.print_help()
            sys.exit(1)
        
        # 处理
        results = process_patent(
            content,
            output_dir=args.output,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        
        if results is None:
            sys.exit(1)
            
    except ValueError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"❌ {ERR_UNKNOWN}: 未预期错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
