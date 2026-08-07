#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SkillPack — 本地AI技能打包与团队部署工具

本脚本依据功能规格独立实现（clean-room），仅使用标准库。
支持技能打包、依赖清单生成、部署配置生成、版本校验、批量处理。
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
MAX_PACK_SIZE = 500 * 1024 * 1024  # 500MB 上限
SUPPORTED_CONFIG_NAMES = ["skill.json", "skill.yaml", "skill.yml", "SKILL.md", "skill.md"]
DEFAULT_INDEX_NAME = "index.json"
DEFAULT_MANIFEST_NAME = "manifest.json"
DEFAULT_DEPLOY_CONFIG_NAME = "deploy_config.json"
ERROR_CODES = {
    "E001": "参数错误或缺少必要参数",
    "E002": "技能目录不存在或不可读",
    "E003": "技能包超过500MB大小限制",
    "E004": "技能包文件不存在或无法读取",
    "E005": "技能包格式无效（非zip）",
    "E006": "技能包内缺少必要配置文件",
    "E007": "版本校验失败或不兼容",
    "E008": "写入输出文件失败",
    "E009": "批量处理中部分任务失败",
    "E010": "内部逻辑错误",
}

# ---------------------------------------------------------------------------
# 异常与错误处理
# ---------------------------------------------------------------------------
class SkillPackError(Exception):
    """技能打包工具的自定义异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def _raise(code: str, **kwargs) -> None:
    """根据错误码抛出标准异常。"""
    template = ERROR_CODES.get(code, "未知错误")
    detail = "；".join(f"{k}={v}" for k, v in kwargs.items())
    msg = f"{template}。{detail}" if detail else template
    raise SkillPackError(code, msg)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _safe_filename(name: str) -> str:
    """将字符串转换为安全的文件名。"""
    return re.sub(r'[^A-Za-z0-9._-]', '_', name)


def _read_json(path: Path) -> Optional[Dict]:
    """读取 JSON 文件，失败时返回 None。"""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, data: Dict) -> None:
    """写入 JSON 文件，失败时抛出 E008。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as exc:
        _raise("E008", path=str(path), reason=str(exc))


def _compute_sha256(file_path: Path) -> str:
    """计算文件的 SHA256 哈希。"""
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _scan_dependencies(skill_dir: Path) -> List[str]:
    """
    扫描技能目录，提取依赖清单。
    支持 requirements.txt 和配置文件中的依赖字段。
    """
    deps: List[str] = []
    req_file = skill_dir / "requirements.txt"
    if req_file.exists():
        for line in req_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                deps.append(line)

    # 扫描配置文件中的依赖字段
    for cfg_name in SUPPORTED_CONFIG_NAMES:
        cfg_path = skill_dir / cfg_name
        if not cfg_path.exists():
            continue
        if cfg_path.suffix == ".json":
            data = _read_json(cfg_path)
            if data and "dependencies" in data:
                deps.extend(data["dependencies"])
        elif cfg_path.suffix in (".yaml", ".yml"):
            # 简单 YAML 解析（仅提取 dependencies 字段，不引入第三方库）
            try:
                in_deps = False
                for line in cfg_path.read_text(encoding="utf-8").splitlines():
                    stripped = line.strip()
                    if stripped.startswith("dependencies:"):
                        in_deps = True
                        continue
                    if in_deps:
                        if stripped.startswith("- "):
                            deps.append(stripped[2:].strip())
                        elif stripped and not stripped.startswith(("#", " ")):
                            in_deps = False
            except Exception:
                pass
        elif cfg_path.name.lower() == "skill.md":
            # 从 Markdown 中提取依赖信息
            try:
                content = cfg_path.read_text(encoding="utf-8")
                # 查找依赖部分
                dep_section = re.search(r'##?\s*依赖|##?\s*Dependencies', content, re.IGNORECASE)
                if dep_section:
                    section_content = content[dep_section.end():]
                    # 查找下一个二级标题作为结束
                    next_section = re.search(r'##\s+', section_content)
                    if next_section:
                        section_content = section_content[:next_section.start()]
                    # 提取列表项
                    for line in section_content.splitlines():
                        stripped = line.strip()
                        if stripped.startswith("- ") or stripped.startswith("* "):
                            dep = stripped[2:].strip()
                            if dep and not dep.startswith("#"):
                                deps.append(dep)
            except Exception:
                pass

    # 去重并保持顺序
    seen = set()
    unique_deps = []
    for dep in deps:
        if dep not in seen:
            seen.add(dep)
            unique_deps.append(dep)
    
    return unique_deps


def _validate_skill_dir(skill_dir: Path) -> None:
    """验证技能目录是否存在且包含必要配置。"""
    if not skill_dir.exists() or not skill_dir.is_dir():
        _raise("E002", path=str(skill_dir))
    
    has_config = any((skill_dir / name).exists() for name in SUPPORTED_CONFIG_NAMES)
    if not has_config:
        _raise("E006", path=str(skill_dir))


def _create_manifest(skill_dir: Path, include_hashes: bool = True) -> Dict:
    """创建技能清单。"""
    manifest = {
        "name": skill_dir.name,
        "version": "1.0.0",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "files": [],
        "dependencies": _scan_dependencies(skill_dir)
    }
    
    # 收集文件信息
    for root, dirs, files in os.walk(skill_dir):
        # 跳过隐藏目录和 __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.startswith('.'):
                continue
            file_path = Path(root) / file
            rel_path = file_path.relative_to(skill_dir).as_posix()
            file_info = {
                "path": rel_path,
                "size": file_path.stat().st_size
            }
            if include_hashes:
                file_info["sha256"] = _compute_sha256(file_path)
            manifest["files"].append(file_info)
    
    return manifest


def _create_deploy_config(skill_dir: Path, target_env: str) -> Dict:
    """创建部署配置。"""
    return {
        "skill_name": skill_dir.name,
        "target_environment": target_env,
        "deploy_time": datetime.utcnow().isoformat() + "Z",
        "strategy": "copy",
        "backup": True,
        "dependencies_install": True
    }


def _create_index(skills: List[Dict]) -> Dict:
    """创建技能索引。"""
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_skills": len(skills),
        "skills": skills
    }


def _package_skill(skill_dir: Path, output_path: Path, target_env: str = "production") -> Path:
    """
    打包单个技能目录为 zip 包。
    返回生成的包文件路径。
    """
    _validate_skill_dir(skill_dir)
    
    # 检查目录大小
    total_size = sum(f.stat().st_size for f in skill_dir.rglob('*') if f.is_file())
    if total_size > MAX_PACK_SIZE:
        _raise("E003", path=str(skill_dir), size=str(total_size))
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # 生成清单和部署配置
        manifest = _create_manifest(skill_dir)
        deploy_config = _create_deploy_config(skill_dir, target_env)
        
        # 写入清单和部署配置
        _write_json(tmp_path / DEFAULT_MANIFEST_NAME, manifest)
        _write_json(tmp_path / DEFAULT_DEPLOY_CONFIG_NAME, deploy_config)
        
        # 复制技能文件
        for root, dirs, files in os.walk(skill_dir):
            # 跳过隐藏目录和 __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.startswith('.'):
                    continue
                src = Path(root) / file
                rel_path = src.relative_to(skill_dir)
                dst = tmp_path / "skill" / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        
        # 创建 zip 包
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(tmp_path):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(tmp_path).as_posix()
                    zf.write(file_path, arcname)
    
    return output_path


def _unpack_skill(pack_path: Path, output_dir: Path) -> Path:
    """
    解包技能 zip 到指定目录。
    返回技能目录路径。
    """
    if not pack_path.exists():
        _raise("E004", path=str(pack_path))
    
    if not zipfile.is_zipfile(pack_path):
        _raise("E005", path=str(pack_path))
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with zipfile.ZipFile(pack_path, 'r') as zf:
            # 检查是否包含必要文件
            names = zf.namelist()
            has_manifest = DEFAULT_MANIFEST_NAME in names
            has_config = any(name in names for name in SUPPORTED_CONFIG_NAMES)
            if not has_manifest or not has_config:
                _raise("E006", path=str(pack_path))
            
            # 解压
            zf.extractall(output_dir)
    except SkillPackError:
        raise
    except Exception as exc:
        _raise("E010", reason=str(exc))
    
    # 返回技能目录（通常在 skill/ 子目录）
    skill_subdir = output_dir / "skill"
    if skill_subdir.exists():
        return skill_subdir
    return output_dir


def _validate_version(pack_path: Path, min_version: str) -> bool:
    """
    验证技能包版本是否满足最低要求。
    简单版本比较（支持 x.y.z 格式）。
    """
    try:
        with zipfile.ZipFile(pack_path, 'r') as zf:
            if DEFAULT_MANIFEST_NAME not in zf.namelist():
                _raise("E006", path=str(pack_path))
            
            with zf.open(DEFAULT_MANIFEST_NAME) as f:
                manifest = json.loads(f.read().decode('utf-8'))
        
        version = manifest.get("version", "0.0.0")
        
        # 解析版本号
        def parse_version(v):
            parts = []
            for part in v.split('.'):
                try:
                    parts.append(int(part))
                except ValueError:
                    parts.append(0)
            # 补齐到 3 位
            while len(parts) < 3:
                parts.append(0)
            return tuple(parts[:3])
        
        current = parse_version(version)
        minimum = parse_version(min_version)
        
        return current >= minimum
    except SkillPackError:
        raise
    except Exception as exc:
        _raise("E010", reason=str(exc))


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------
def _cmd_pack(args) -> int:
    """打包命令处理。"""
    try:
        skill_dir = Path(args.skill_dir)
        output = Path(args.output)
        output_path = _package_skill(skill_dir, output, args.target_env)
        print(f"技能包已生成: {output_path}")
        return 0
    except SkillPackError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def _cmd_unpack(args) -> int:
    """解包命令处理。"""
    try:
        pack_path = Path(args.pack_path)
        output_dir = Path(args.output_dir)
        skill_dir = _unpack_skill(pack_path, output_dir)
        print(f"技能已解包到: {skill_dir}")
        return 0
    except SkillPackError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def _cmd_validate(args) -> int:
    """版本校验命令处理。"""
    try:
        pack_path = Path(args.pack_path)
        if not _validate_version(pack_path, args.min_version):
            print(f"版本校验失败: 不满足最低版本 {args.min_version}")
            return 1
        print("版本校验通过")
        return 0
    except SkillPackError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def _cmd_batch(args) -> int:
    """批量打包命令处理。"""
    try:
        input_dir = Path(args.input_dir)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 查找所有包含配置文件的子目录
        skill_dirs = []
        for item in input_dir.iterdir():
            if item.is_dir():
                has_config = any((item / name).exists() for name in SUPPORTED_CONFIG_NAMES)
                if has_config:
                    skill_dirs.append(item)
        
        if not skill_dirs:
            print(f"在 {input_dir} 中未找到技能目录")
            return 1
        
        success_count = 0
        fail_count = 0
        for skill_dir in skill_dirs:
            try:
                output_path = output_dir / f"{skill_dir.name}.skillpack"
                _package_skill(skill_dir, output_path, args.target_env)
                print(f"✓ 打包成功: {skill_dir.name}")
                success_count += 1
            except SkillPackError as e:
                print(f"✗ 打包失败: {skill_dir.name} - {e}", file=sys.stderr)
                fail_count += 1
        
        print(f"\n批量打包完成: 成功 {success_count}, 失败 {fail_count}")
        
        if fail_count > 0:
            return 1
        return 0
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def _cmd_selftest(args) -> int:
    """自测命令处理。"""
    print("运行自测...")
    try:
        # 创建临时测试目录
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # 1. 创建测试技能目录
            test_skill = tmp_path / "test_skill"
            test_skill.mkdir()
            
            # 创建配置文件
            (test_skill / "skill.json").write_text(
                json.dumps({
                    "name": "test_skill",
                    "version": "1.0.0",
                    "description": "测试技能",
                    "dependencies": ["numpy", "requests>=2.0"]
                }),
                encoding="utf-8"
            )
            
            # 创建一些文件
            (test_skill / "main.py").write_text("# test main\nprint('hello')\n", encoding="utf-8")
            (test_skill / "requirements.txt").write_text(
                "# 依赖\nflask==2.0.1\npandas\n", encoding="utf-8"
            )
            
            # 2. 测试打包
            pack_path = tmp_path / "test.skillpack"
            _package_skill(test_skill, pack_path, "production")
            assert pack_path.exists(), "打包文件未生成"
            print("✓ 打包功能正常")
            
            # 3. 测试解包
            unpack_dir = tmp_path / "unpacked"
            skill_dir = _unpack_skill(pack_path, unpack_dir)
            assert skill_dir.exists(), "解包目录不存在"
            print("✓ 解包功能正常")
            
            # 4. 测试版本校验
            assert _validate_version(pack_path, "1.0.0"), "版本校验应通过"
            assert not _validate_version(pack_path, "2.0.0"), "版本校验应失败"
            print("✓ 版本校验功能正常")
            
            # 5. 测试依赖扫描
            deps = _scan_dependencies(test_skill)
            assert "numpy" in deps, "依赖扫描缺少 numpy"
            assert "flask==2.0.1" in deps, "依赖扫描缺少 flask"
            print("✓ 依赖扫描功能正常")
            
            # 6. 测试错误处理
            try:
                _package_skill(tmp_path / "nonexistent", tmp_path / "x.skillpack")
                assert False, "应该抛出 E002 错误"
            except SkillPackError as e:
                assert e.code == "E002", f"错误码应为 E002, 实际为 {e.code}"
            print("✓ 错误处理正常")
            
            # 7. 测试安全文件名
            assert _safe_filename("test name!") == "test_name_", "安全文件名转换失败"
            print("✓ 工具函数正常")
            
            # 8. 测试批量打包
            batch_dir = tmp_path / "batch"
            batch_dir.mkdir()
            (batch_dir / "skill1").mkdir()
            (batch_dir / "skill1" / "skill.json").write_text(
                json.dumps({"name": "skill1", "version": "1.0.0"}),
                encoding="utf-8"
            )
            (batch_dir / "skill2").mkdir()
            (batch_dir / "skill2" / "skill.yaml").write_text(
                "name: skill2\nversion: 1.0.0\n",
                encoding="utf-8"
            )
            (batch_dir / "not_skill").mkdir()
            
            batch_out = tmp_path / "batch_out"
            batch_out.mkdir()
            
            # 使用内部函数测试批量打包
            success = 0
            for item in batch_dir.iterdir():
                if item.is_dir() and any((item / name).exists() for name in SUPPORTED_CONFIG_NAMES):
                    _package_skill(item, batch_out / f"{item.name}.skillpack", "production")
                    success += 1
            assert success == 2, f"应打包 2 个技能, 实际 {success}"
            print("✓ 批量打包功能正常")
            
            # 9. 测试 manifest 生成
            manifest = _create_manifest(test_skill)
            assert "files" in manifest, "manifest 缺少 files 字段"
            assert "dependencies" in manifest, "manifest 缺少 dependencies 字段"
            assert len(manifest["files"]) > 0, "manifest 文件列表为空"
            print("✓ manifest 生成正常")
            
            # 10. 测试 deploy config 生成
            deploy_config = _create_deploy_config(test_skill, "staging")
            assert deploy_config["target_environment"] == "staging", "部署环境错误"
            assert deploy_config["strategy"] == "copy", "部署策略错误"
            print("✓ deploy config 生成正常")
            
            # 11. 测试 index 生成
            index = _create_index([{"name": "test", "version": "1.0.0"}])
            assert index["total_skills"] == 1, "index 技能数量错误"
            print("✓ index 生成正常")
            
            # 12. 测试 SKILL.md 依赖提取
            skill_md_dir = tmp_path / "md_skill"
            skill_md_dir.mkdir()
            (skill_md_dir / "SKILL.md").write_text(
                "# 测试技能\n\n## 依赖\n- package1\n- package2>=1.0\n\n## 其他\n内容\n",
                encoding="utf-8"
            )
            md_deps = _scan_dependencies(skill_md_dir)
            assert "package1" in md_deps, "SKILL.md 依赖提取失败"
            assert "package2>=1.0" in md_deps, "SKILL.md 依赖提取失败"
            print("✓ SKILL.md 依赖提取正常")
            
            print("\n所有自测通过！")
            return 0
            
    except AssertionError as e:
        print(f"✗ 自测失败: {e}", file=sys.stderr)
        return 1
    except SkillPackError as e:
        print(f"✗ 自测失败: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ 自测失败: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="SkillPack - 本地AI技能打包与团队部署工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # pack 命令
    pack_parser = subparsers.add_parser("pack", help="打包技能目录")
    pack_parser.add_argument("skill_dir", help="技能目录路径")
    pack_parser.add_argument("-o", "--output", required=True, help="输出包文件路径")
    pack_parser.add_argument("-e", "--target-env", default="production", help="目标环境")
    pack_parser.set_defaults(func=_cmd_pack)
    
    # unpack 命令
    unpack_parser = subparsers.add_parser("unpack", help="解包技能包")
    unpack_parser.add_argument("pack_path", help="技能包文件路径")
    unpack_parser.add_argument("-o", "--output-dir", default=".", help="输出目录")
    unpack_parser.set_defaults(func=_cmd_unpack)
    
    # validate 命令
    validate_parser = subparsers.add_parser("validate", help="校验技能包版本")
    validate_parser.add_argument("pack_path", help="技能包文件路径")
    validate_parser.add_argument("--min-version", default="0.0.0", help="最低版本要求")
    validate_parser.set_defaults(func=_cmd_validate)
    
    # batch 命令
    batch_parser = subparsers.add_parser("batch", help="批量打包技能目录")
    batch_parser.add_argument("input_dir", help="包含多个技能目录的根目录")
    batch_parser.add_argument("-o", "--output-dir", required=True, help="输出目录")
    batch_parser.add_argument("-e", "--target-env", default="production", help="目标环境")
    batch_parser.set_defaults(func=_cmd_batch)
    
    # selftest 命令
    selftest_parser = subparsers.add_parser("selftest", help="运行自测")
    selftest_parser.set_defaults(func=_cmd_selftest)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
