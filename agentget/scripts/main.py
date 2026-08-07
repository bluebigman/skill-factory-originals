#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agentget - 从 GitHub 仓库安装 AI 代理、指令、技能和规则到项目/全局环境
版本: 1.0.0
作者: skill-factory-auto
许可证: MIT
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "网络请求失败",
    "E007": "仓库解析失败",
    "E008": "文件操作失败",
    "E009": "安装目标不存在",
    "E010": "权限不足",
}


class AgentGetError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 数据模型
# ============================================================
@dataclass
class InstallItem:
    """待安装的组件项"""

    name: str
    source_path: str
    target_path: str
    item_type: str  # agent / instruction / skill / rule
    content: str = ""
    confidence: float = 1.0


@dataclass
class InstallResult:
    """安装结果"""

    success: bool = False
    installed: List[InstallItem] = field(default_factory=list)
    failed: List[Tuple[str, str]] = field(default_factory=list)  # (item_name, error)
    warnings: List[str] = field(default_factory=list)


# ============================================================
# 核心配置
# ============================================================
# 支持的组件目录
SUPPORTED_DIRS = {
    "agents": "agent",
    "instructions": "instruction",
    "skills": "skill",
    "rules": "rule",
}

# 配置文件
CONFIG_FILENAME = "agentget.json"
CONFIG_SCHEMA_VERSION = "1.0.0"

# 默认安装根目录（相对于用户主目录）
DEFAULT_INSTALL_ROOT = ".agentget"


# ============================================================
# 工具函数
# ============================================================
def normalize_github_url(url: str) -> str:
    """
    将各种 GitHub URL 格式规范化为标准格式
    支持: https://github.com/user/repo, 
          git@github.com:user/repo.git,
          user/repo 简写
    """
    if not url or not url.strip():
        raise AgentGetError("E001", "GitHub 仓库 URL 不能为空")

    url = url.strip()

    # 处理 git@ 格式
    if url.startswith("git@"):
        match = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
        if match:
            return f"https://github.com/{match.group(1)}/{match.group(2)}"

    # 处理 https:// 格式
    if url.startswith("https://github.com/"):
        parts = url.rstrip("/").split("/")
        if len(parts) >= 5:
            return f"https://github.com/{parts[3]}/{parts[4]}"
        raise AgentGetError("E003", f"无法解析 GitHub 仓库 URL: {url}")

    # 处理 user/repo 简写
    if "/" in url and not url.startswith(("http://", "git@")):
        parts = url.split("/")
        if len(parts) == 2:
            return f"https://github.com/{parts[0]}/{parts[1]}"
        raise AgentGetError("E003", f"无法解析 GitHub 仓库 URL: {url}")

    raise AgentGetError("E003", f"不支持的 GitHub URL 格式: {url}")


def download_repo_zip(repo_url: str, target_dir: Path) -> Path:
    """
    从 GitHub 下载仓库 zip 包并解压
    返回解压后的目录路径
    """
    try:
        # 转换为下载 URL
        zip_url = f"{repo_url}/archive/refs/heads/main.zip"
        zip_path = target_dir / "repo.zip"

        # 下载
        print(f"正在下载: {zip_url}")
        urllib.request.urlretrieve(zip_url, zip_path)

        # 解压
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)

        # 找到解压后的目录
        extracted_dirs = [d for d in target_dir.iterdir() if d.is_dir()]
        if not extracted_dirs:
            raise AgentGetError("E007", "仓库解压后未找到目录")

        return extracted_dirs[0]

    except AgentGetError:
        raise
    except Exception as e:
        raise AgentGetError("E006", f"下载仓库失败: {str(e)}")


def parse_repo_config(repo_dir: Path) -> Dict:
    """
    解析仓库中的 agentget.json 配置文件
    """
    config_path = repo_dir / CONFIG_FILENAME
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        if not isinstance(config, dict):
            raise AgentGetError("E003", f"配置文件格式错误: {CONFIG_FILENAME}")
        return config

    except json.JSONDecodeError as e:
        raise AgentGetError("E003", f"配置文件 JSON 解析失败: {str(e)}")
    except AgentGetError:
        raise
    except Exception as e:
        raise AgentGetError("E003", f"读取配置文件失败: {str(e)}")


def discover_items(repo_dir: Path, config: Dict) -> List[InstallItem]:
    """
    发现仓库中所有可安装的组件
    """
    items = []

    # 从配置文件中读取自定义映射
    custom_mappings = config.get("mappings", {}) if config else {}

    # 遍历支持的目录
    for dir_name, item_type in SUPPORTED_DIRS.items():
        source_dir = repo_dir / dir_name
        if source_dir.exists() and source_dir.is_dir():
            for file_path in source_dir.glob("*"):
                if file_path.is_file():
                    items.append(
                        InstallItem(
                            name=file_path.stem,
                            source_path=str(file_path),
                            target_path="",
                            item_type=item_type,
                        )
                    )

    # 处理自定义映射
    for source, target in custom_mappings.items():
        src_path = repo_dir / source
        if src_path.exists():
            items.append(
                InstallItem(
                    name=Path(source).stem,
                    source_path=str(src_path),
                    target_path=target,
                    item_type="custom",
                )
            )

    return items


def calculate_confidence(item: InstallItem) -> float:
    """
    计算组件置信度
    基于文件大小、内容完整性等
    """
    confidence = 1.0

    try:
        # 检查文件是否存在
        if not os.path.exists(item.source_path):
            return 0.0

        # 检查文件大小
        file_size = os.path.getsize(item.source_path)
        if file_size < 10:  # 文件太小可能不完整
            confidence -= 0.3
        elif file_size < 100:
            confidence -= 0.1

        # 检查内容
        with open(item.source_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            item.content = content

        # 检查是否包含关键字段
        if item.item_type == "agent" and "name" not in content:
            confidence -= 0.1
        if item.item_type == "skill" and "description" not in content:
            confidence -= 0.1

        # 检查是否有明显的截断
        if content and not content.endswith(("\n", "}", "]", ")", ">")):
            confidence -= 0.05

    except Exception:
        confidence = 0.5

    # 确保置信度在合理范围
    confidence = max(0.0, min(1.0, confidence))
    item.confidence = confidence
    return confidence


def install_item(item: InstallItem, install_root: Path) -> None:
    """
    安装单个组件到目标位置
    """
    # 确定目标路径
    if not item.target_path:
        # 根据类型确定默认目录
        type_dir_map = {
            "agent": "agents",
            "instruction": "instructions",
            "skill": "skills",
            "rule": "rules",
            "custom": "custom",
        }
        target_dir = install_root / type_dir_map.get(item.item_type, "misc")
        item.target_path = str(target_dir / f"{item.name}.md")

    target_path = Path(item.target_path)
    if not target_path.is_absolute():
        target_path = install_root / target_path

    # 创建目标目录
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # 复制文件
    try:
        shutil.copy2(item.source_path, target_path)
    except Exception as e:
        raise AgentGetError("E008", f"复制文件失败: {str(e)}")


def process_repo(repo_url: str, install_root: Path, dry_run: bool = False) -> InstallResult:
    """
    处理单个 GitHub 仓库的安装
    """
    result = InstallResult()
    temp_dir = None

    try:
        # 规范化 URL
        normalized_url = normalize_github_url(repo_url)
        print(f"处理仓库: {normalized_url}")

        # 创建临时目录
        temp_dir = Path(tempfile.mkdtemp(prefix="agentget_"))

        if dry_run:
            # 模拟模式，不实际下载
            print("[模拟模式] 跳过下载")
            # 生成模拟组件
            repo_name = normalized_url.rstrip("/").split("/")[-1]
            items = [
                InstallItem(
                    name=f"sample_{repo_name}",
                    source_path="",
                    target_path="",
                    item_type="skill",
                    content="sample content",
                    confidence=0.9,
                )
            ]
        else:
            # 下载并解压仓库
            repo_dir = download_repo_zip(normalized_url, temp_dir)

            # 解析配置
            config = parse_repo_config(repo_dir)

            # 发现组件
            items = discover_items(repo_dir, config)

        if not items:
            result.warnings.append("未发现可安装的组件")
            return result

        # 计算置信度并安装
        for item in items:
            try:
                confidence = calculate_confidence(item)
                if confidence < 0.5:
                    result.warnings.append(f"{item.name}: 置信度过低 ({confidence:.0%})")
                    continue

                if not dry_run:
                    install_item(item, install_root)

                result.installed.append(item)
                print(f"  安装: {item.name} ({item.item_type}) [{confidence:.0%}]")

            except AgentGetError as e:
                result.failed.append((item.name, str(e)))
                print(f"  失败: {item.name} - {e}")

        result.success = len(result.installed) > 0
        return result

    except AgentGetError as e:
        raise
    finally:
        # 清理临时目录
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    内置自检函数，使用硬编码样例数据验证核心逻辑
    不依赖外部文件、网络或当前工作目录
    """
    print("=" * 60)
    print("运行自检...")
    print("=" * 60)

    all_passed = True

    # 测试 1: URL 规范化
    print("\n[测试 1] URL 规范化")
    test_cases = [
        ("https://github.com/user/repo", "https://github.com/user/repo"),
        ("https://github.com/user/repo/", "https://github.com/user/repo"),
        ("git@github.com:user/repo.git", "https://github.com/user/repo"),
        ("user/repo", "https://github.com/user/repo"),
    ]
    
    for input_url, expected in test_cases:
        try:
            result = normalize_github_url(input_url)
            # 严格验证：结果必须完全匹配预期
            assert result == expected, f"期望 {expected}，实际 {result}"
            print(f"  ✓ {input_url} -> {result}")
        except AssertionError as e:
            print(f"  ✗ {input_url} - {e}")
            all_passed = False
        except AgentGetError as e:
            print(f"  ✗ {input_url} - 异常: {e}")
            all_passed = False

    # 测试 2: 错误处理
    print("\n[测试 2] 错误处理")
    
    # 空 URL
    try:
        normalize_github_url("")
        print("  ✗ 空 URL 未抛出异常")
        all_passed = False
    except AgentGetError as e:
        if e.code == "E001":
            print(f"  ✓ 空 URL 返回 E001")
        else:
            print(f"  ✗ 空 URL 错误码不对: {e.code}")
            all_passed = False
    except Exception as e:
        print(f"  ✗ 空 URL 抛出未知异常: {e}")
        all_passed = False

    # 无效 URL
    try:
        normalize_github_url("invalid-url")
        print("  ✗ 无效 URL 未抛出异常")
        all_passed = False
    except AgentGetError as e:
        if e.code == "E003":
            print(f"  ✓ 无效 URL 返回 E003")
        else:
            print(f"  ✗ 无效 URL 错误码不对: {e.code}")
            all_passed = False
    except Exception as e:
        print(f"  ✗ 无效 URL 抛出未知异常: {e}")
        all_passed = False

    # 测试 3: 组件发现（模拟）
    print("\n[测试 3] 组件发现")
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = Path(tmpdir) / "repo"
        repo_dir.mkdir()

        # 创建模拟目录结构
        for dir_name in SUPPORTED_DIRS:
            (repo_dir / dir_name).mkdir(exist_ok=True)

        # 创建测试文件
        test_files = {
            "skills/test_skill.md": "# Test Skill\ndescription: 测试技能\nversion: 1.0.0\n",
            "agents/test_agent.md": "# Test Agent\nname: test_agent\ndescription: 测试代理\n",
            "rules/test_rule.md": "# Test Rule\nrule: 测试规则\n",
            "instructions/test_instruction.md": "# Test Instruction\ninstruction: 测试指令\n",
        }
        
        for file_path, content in test_files.items():
            full_path = repo_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        items = discover_items(repo_dir, {})
        assert len(items) >= 4, f"发现组件数量不足: {len(items)}"
        print(f"  ✓ 发现 {len(items)} 个组件")

        # 检查组件类型
        types = [item.item_type for item in items]
        expected_types = ["skill", "agent", "rule", "instruction"]
        for expected_type in expected_types:
            assert expected_type in types, f"缺少 {expected_type} 类型"
        print("  ✓ 组件类型正确")

    # 测试 4: 置信度计算
    print("\n[测试 4] 置信度计算")
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        good_file = Path(tmpdir) / "good.md"
        good_file.write_text("# Good\nname: test\ndescription: test\ncontent: " + "x" * 200 + "\n")

        bad_file = Path(tmpdir) / "bad.md"
        bad_file.write_text("")

        # 测试正常文件
        item = InstallItem(
            name="test",
            source_path=str(good_file),
            target_path="",
            item_type="agent",
        )
        confidence = calculate_confidence(item)
        assert confidence >= 0.5, f"正常文件置信度过低: {confidence}"
        print(f"  ✓ 正常文件置信度: {confidence:.2f}")

        # 测试空文件
        item = InstallItem(
            name="test",
            source_path=str(bad_file),
            target_path="",
            item_type="agent",
        )
        confidence = calculate_confidence(item)
        assert confidence <= 0.5, f"空文件置信度应该低: {confidence}"
        print(f"  ✓ 空文件置信度: {confidence:.2f}")

    # 测试 5: 安装流程（模拟）
    print("\n[测试 5] 安装流程")
    with tempfile.TemporaryDirectory() as tmpdir:
        install_root = Path(tmpdir) / "install"
        install_root.mkdir()

        # 创建源文件
        source = Path(tmpdir) / "source.md"
        source.write_text("# Test\ncontent: test content\n")

        item = InstallItem(
            name="test_item",
            source_path=str(source),
            target_path="",
            item_type="skill",
            content="# Test\ncontent: test content\n",
            confidence=0.9,
        )

        # 执行安装
        install_item(item, install_root)

        # 验证安装结果
        target = install_root / "skills" / "test_item.md"
        assert target.exists(), f"安装失败，目标文件不存在: {target}"
        content = target.read_text()
        assert "test content" in content, "安装内容不正确"
        print(f"  ✓ 安装成功: {target}")

    # 测试 6: 模拟仓库处理
    print("\n[测试 6] 模拟仓库处理")
    with tempfile.TemporaryDirectory() as tmpdir:
        install_root = Path(tmpdir) / "install"
        install_root.mkdir()

        result = process_repo("https://github.com/test/repo", install_root, dry_run=True)
        assert result.success, "模拟安装失败"
        assert len(result.installed) > 0, "没有安装任何组件"
        print(f"  ✓ 模拟安装成功，安装了 {len(result.installed)} 个组件")

    # 测试 7: 错误码完整性
    print("\n[测试 7] 错误码完整性")
    expected_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
    for code in expected_codes:
        assert code in ERROR_CODES, f"缺少错误码: {code}"
    print(f"  ✓ 错误码完整 ({len(expected_codes)} 个)")

    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自检通过: 所有测试均通过")
    else:
        print("自检失败: 部分测试未通过")
    print("=" * 60)

    return all_passed


# ============================================================
# 主程序
# ============================================================
def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="agentget - 从 GitHub 仓库安装 AI 代理、指令、技能和规则",
        epilog="示例: python main.py https://github.com/user/repo --install-dir ~/.agentget",
    )

    parser.add_argument(
        "repo_urls",
        nargs="*",
        help="GitHub 仓库 URL（支持多个）",
    )
    parser.add_argument(
        "--install-dir",
        type=str,
        default=None,
        help="安装目录（默认: ~/.agentget）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟运行，不实际下载和安装",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细信息",
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 检查是否有仓库 URL
    if not args.repo_urls:
        parser.print_help()
        print("\n错误: 请提供至少一个 GitHub 仓库 URL")
        print("示例: python main.py https://github.com/user/repo")
        sys.exit(1)

    # 确定安装目录
    if args.install_dir:
        install_root = Path(args.install_dir).expanduser()
    else:
        install_root = Path.home() / DEFAULT_INSTALL_ROOT

    try:
        # 创建安装目录
        install_root.mkdir(parents=True, exist_ok=True)

        # 处理每个仓库
        total_installed = 0
        total_failed = 0

        for repo_url in args.repo_urls:
            try:
                print(f"\n处理仓库: {repo_url}")
                result = process_repo(repo_url, install_root, args.dry_run)

                # 输出结果
                if result.installed:
                    print(f"成功安装 {len(result.installed)} 个组件:")
                    for item in result.installed:
                        print(f"  ✓ {item.name} ({item.item_type})")
                    total_installed += len(result.installed)

                if result.failed:
                    print(f"失败 {len(result.failed)} 个组件:")
                    for name, error in result.failed:
                        print(f"  ✗ {name}: {error}")
                    total_failed += len(result.failed)

                if result.warnings:
                    for warning in result.warnings:
                        print(f"  警告: {warning}")

            except AgentGetError as e:
                print(f"仓库处理失败: {e}")
                total_failed += 1
            except Exception as e:
                print(f"意外错误: {e}")
                total_failed += 1

        # 汇总
        print("\n" + "=" * 60)
        print(f"安装完成: 成功 {total_installed} 个，失败 {total_failed} 个")
        print(f"安装目录: {install_root}")
        print("=" * 60)

        # 根据结果设置退出码
        sys.exit(1 if total_failed > 0 else 0)

    except AgentGetError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"未预期的错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
