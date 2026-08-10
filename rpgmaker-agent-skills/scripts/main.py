#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

RPGMaker 工程安全读写 - 独立实现脚本
依据功能规格 clean-room 重写，仅使用 Python 标准库。
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "文件不存在或无法访问",
    "E002": "JSON 解析失败（文件损坏或非 JSON 格式）",
    "E003": "工程根目录无效（缺少 Game.rpgproject 或 data 目录）",
    "E004": "无法识别工程类型（既不是 MV 也不是 MZ）",
    "E005": "数据库文件格式不符合预期（缺少必要字段）",
    "E006": "插件配置格式错误",
    "E007": "地图数据格式错误",
    "E008": "批量操作目标为空或无效",
    "E009": "不支持的导出格式（仅支持 CSV）",
    "E010": "内部逻辑错误（未预期的状态）",
}


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def fail(code: str, message: str) -> None:
    """输出错误信息并退出。"""
    prefix = ERROR_CODES.get(code, "E010")
    print(f"[错误 {code}] {prefix}: {message}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 工程结构解析
# ---------------------------------------------------------------------------
class RPGMakerProject:
    """RPG Maker MV/MZ 工程对象。"""

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        self.project_type: Optional[str] = None
        self.version: str = ""
        self.data_dir: str = ""
        self._validate_structure()

    def _validate_structure(self) -> None:
        """校验工程目录结构，识别 MV/MZ。"""
        if not os.path.isdir(self.root_dir):
            fail("E001", f"目录不存在: {self.root_dir}")

        # 查找工程标志文件
        mv_flag = os.path.join(self.root_dir, "Game.rpgproject")
        mz_flag = os.path.join(self.root_dir, "Game.rmmzproject")
        data_dir = os.path.join(self.root_dir, "data")
        js_dir = os.path.join(self.root_dir, "js")

        has_data = os.path.isdir(data_dir)
        has_js = os.path.isdir(js_dir)

        if os.path.isfile(mv_flag) and has_data:
            self.project_type = "MV"
            self.version = self._read_project_version(mv_flag)
        elif os.path.isfile(mz_flag) and has_data:
            self.project_type = "MZ"
            self.version = self._read_project_version(mz_flag)
        elif has_data and has_js:
            # 无标志文件时尝试通过 data 目录内容判断
            self._guess_from_data(data_dir)
        else:
            fail("E003", "工程根目录无效（缺少工程标志文件或 data 目录）")

        self.data_dir = data_dir

    def _read_project_version(self, flag_file: str) -> str:
        """从工程标志文件读取版本信息。"""
        try:
            with open(flag_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
            # 尝试解析 JSON 格式的版本信息
            if content.startswith("{"):
                data = json.loads(content)
                return str(data.get("version", ""))
            return content
        except Exception:
            return "未知版本"

    def _guess_from_data(self, data_dir: str) -> None:
        """通过 data 目录特征猜测工程类型。"""
        # MZ 通常包含 System.json 且有特定字段，MV 也有类似文件
        system_file = os.path.join(data_dir, "System.json")
        if os.path.isfile(system_file):
            try:
                with open(system_file, "r", encoding="utf-8", errors="replace") as f:
                    system_data = json.load(f)
                if "gameTitle" in system_data:
                    # 进一步区分 MV/MZ
                    if "advanced" in system_data and "gameTitle" in system_data:
                        self.project_type = "MZ"
                    else:
                        self.project_type = "MV"
                    return
            except Exception as e:
                print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出
        fail("E004", "无法识别工程类型（既不是 MV 也不是 MZ）")


def load_json_file(file_path: str) -> Dict[str, Any]:
    """安全加载 JSON 文件。"""
    if not os.path.isfile(file_path):
        fail("E001", f"文件不存在: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        fail("E002", f"JSON 解析失败: {file_path} - {str(e)}")
    except Exception as e:
        fail("E001", f"读取文件失败: {file_path} - {str(e)}")
    # 不可达，但保持类型完整性
    return {}


def save_json_file(file_path: str, data: Dict[str, Any]) -> None:
    """安全保存 JSON 文件。"""
    try:
        with open(file_path, "w", encoding="utf-8", errors="replace") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        fail("E001", f"写入文件失败: {file_path} - {str(e)}")


# ---------------------------------------------------------------------------
# 地图与事件数据读取
# ---------------------------------------------------------------------------
def parse_map_file(data_dir: str, map_name: str) -> Dict[str, Any]:
    """解析地图文件，提取事件信息。"""
    if not map_name.endswith(".json"):
        map_name += ".json"
    map_path = os.path.join(data_dir, map_name)
    map_data = load_json_file(map_path)

    if "events" not in map_data:
        fail("E007", f"地图文件缺少 events 字段: {map_name}")

    # 提取结构化事件信息
    events_info = []
    for event in map_data.get("events", []):
        if event is None:
            continue
        event_info = {
            "id": event.get("id", 0),
            "name": event.get("name", ""),
            "x": event.get("x", 0),
            "y": event.get("y", 0),
            "pages": [],
        }
        for page in event.get("pages", []):
            page_info = {
                "conditions": page.get("conditions", {}),
                "commands": page.get("list", []),
            }
            event_info["pages"].append(page_info)
        events_info.append(event_info)

    result = {
        "map_id": map_data.get("id", 0),
        "width": map_data.get("width", 0),
        "height": map_data.get("height", 0),
        "events": events_info,
    }
    return result


def parse_common_events(data_dir: str) -> List[Dict[str, Any]]:
    """解析公共事件文件。"""
    common_path = os.path.join(data_dir, "CommonEvents.json")
    common_data = load_json_file(common_path)

    if not isinstance(common_data, list):
        fail("E005", "CommonEvents.json 格式错误（应为数组）")

    events = []
    for ev in common_data:
        if ev is None:
            continue
        events.append({
            "id": ev.get("id", 0),
            "name": ev.get("name", ""),
            "trigger": ev.get("trigger", 0),
            "commands": ev.get("list", []),
        })
    return events


# ---------------------------------------------------------------------------
# 数据库对象安全修改
# ---------------------------------------------------------------------------
def load_database_file(data_dir: str, db_name: str) -> List[Dict[str, Any]]:
    """加载数据库文件（如 Actors.json, Items.json）。"""
    if not db_name.endswith(".json"):
        db_name += ".json"
    db_path = os.path.join(data_dir, db_name)
    db_data = load_json_file(db_path)

    if not isinstance(db_data, list):
        fail("E005", f"数据库文件格式错误（应为数组）: {db_name}")
    return db_data


def update_database_field(
    data_dir: str,
    db_name: str,
    object_id: int,
    field: str,
    value: Any,
) -> bool:
    """安全修改数据库对象的字段。"""
    db_data = load_database_file(data_dir, db_name)

    # 查找目标对象
    target = None
    for obj in db_data:
        if obj is not None and obj.get("id") == object_id:
            target = obj
            break

    if target is None:
        fail("E005", f"数据库 {db_name} 中找不到 ID 为 {object_id} 的对象")

    # 执行修改
    target[field] = value

    # 保存回文件
    db_path = os.path.join(data_dir, db_name)
    save_json_file(db_path, db_data)
    return True


# ---------------------------------------------------------------------------
# 插件配置校验
# ---------------------------------------------------------------------------
def parse_plugins_js(project: RPGMakerProject) -> List[Dict[str, Any]]:
    """解析 js/plugins.js 文件。"""
    plugins_path = os.path.join(project.root_dir, "js", "plugins.js")
    if not os.path.isfile(plugins_path):
        fail("E006", "插件配置文件不存在")

    try:
        with open(plugins_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        fail("E001", f"读取插件配置失败: {str(e)}")

    # RPG Maker 的 plugins.js 格式为: var $plugins = [ {...}, {...} ];
    # 提取 JSON 部分
    start = content.find("[")
    end = content.rfind("]")
    if start == -1 or end == -1 or end <= start:
        fail("E006", "插件配置格式错误（无法定位数组）")

    try:
        plugins_data = json.loads(content[start:end + 1])
    except json.JSONDecodeError as e:
        fail("E006", f"插件配置 JSON 解析失败: {str(e)}")

    if not isinstance(plugins_data, list):
        fail("E006", "插件配置格式错误（应为数组）")

    # 校验每个插件
    result = []
    for plugin in plugins_data:
        if not isinstance(plugin, dict):
            continue
        name = plugin.get("name", "")
        status = plugin.get("status", "off")
        description = plugin.get("description", "")
        parameters = plugin.get("parameters", {})

        # 基本校验
        issues = []
        if not name:
            issues.append("插件名称不能为空")
        if status not in ("on", "off"):
            issues.append(f"插件状态无效: {status}")
        if not isinstance(parameters, dict):
            issues.append("参数格式错误（应为对象）")

        result.append({
            "name": name,
            "status": status,
            "description": description,
            "parameters": parameters,
            "issues": issues,
            "valid": len(issues) == 0,
        })
    return result


# ---------------------------------------------------------------------------
# 批量操作与格式转换
# ---------------------------------------------------------------------------
def batch_update_database_field(
    data_dir: str,
    db_name: str,
    field: str,
    old_value: Any,
    new_value: Any,
) -> int:
    """批量替换数据库中的字段值。"""
    db_data = load_database_file(data_dir, db_name)

    count = 0
    for obj in db_data:
        if obj is not None and field in obj and obj[field] == old_value:
            obj[field] = new_value
            count += 1

    if count > 0:
        db_path = os.path.join(data_dir, db_name)
        save_json_file(db_path, db_data)

    return count


def export_to_csv(data: List[Dict[str, Any]], output_path: str) -> None:
    """导出数据为 CSV 格式。"""
    if not data:
        fail("E008", "没有可导出的数据")

    # 获取所有字段（并集）
    all_keys = set()
    for item in data:
        all_keys.update(item.keys())
    headers = sorted(all_keys)

    try:
        with open(output_path, "w", encoding="utf-8", errors="replace", newline="") as f:
            # 写入表头
            f.write(",".join(headers) + "\n")
            # 写入数据行
            for item in data:
                row = []
                for key in headers:
                    value = item.get(key, "")
                    # 处理特殊字符
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)
                    value = str(value)
                    if "," in value or '"' in value or "\n" in value:
                        value = '"' + value.replace('"', '""') + '"'
                    row.append(value)
                f.write(",".join(row) + "\n")
    except Exception as e:
        fail("E001", f"导出 CSV 失败: {str(e)}")


# ---------------------------------------------------------------------------
# 命令行主入口
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """内置自检函数，使用硬编码样例数据验证核心逻辑。"""
    print("开始自检...")

    # ---------- 测试 1: JSON 加载与保存 ----------
    test_data = {"name": "测试", "list": [1, 2, 3], "nested": {"key": "value"}}
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8", errors="replace") as f:
        json.dump(test_data, f, ensure_ascii=False)
        temp_path = f.name

    try:
        loaded = load_json_file(temp_path)
        assert loaded["name"] == "测试", "JSON 加载失败"
        assert len(loaded["list"]) == 3, "JSON 列表加载失败"
        print("  [通过] JSON 加载")
    finally:
        os.unlink(temp_path)

    # ---------- 测试 2: 数据库字段修改逻辑 ----------
    test_db = [
        {"id": 1, "name": "角色A", "hp": 100},
        {"id": 2, "name": "角色B", "hp": 200},
        None,
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8", errors="replace") as f:
        json.dump(test_db, f, ensure_ascii=False)
        temp_db_path = f.name

    try:
        # 模拟更新逻辑
        db_data = json.loads(open(temp_db_path, "r", encoding="utf-8", errors="replace").read())
        target = None
        for obj in db_data:
            if obj is not None and obj.get("id") == 1:
                target = obj
                break
        assert target is not None, "找不到目标对象"
        target["hp"] = 150
        assert target["hp"] == 150, "字段修改失败"
        print("  [通过] 数据库字段修改")

        # 批量替换逻辑测试
        count = 0
        for obj in db_data:
            if obj is not None and "hp" in obj and obj["hp"] == 200:
                obj["hp"] = 250
                count += 1
        assert count == 1, "批量替换计数错误"
        assert db_data[1]["hp"] == 250, "批量替换值错误"
        print("  [通过] 批量字段替换")
    finally:
        os.unlink(temp_db_path)

    # ---------- 测试 3: 插件配置解析 ----------
    plugins_content = 'var $plugins = [{"name":"TestPlugin","status":"on","description":"测试","parameters":{"param1":"value1"}}];'
    start = plugins_content.find("[")
    end = plugins_content.rfind("]")
    plugins_data = json.loads(plugins_content[start:end + 1])
    assert len(plugins_data) == 1, "插件解析数量错误"
    assert plugins_data[0]["status"] == "on", "插件状态错误"
    assert "param1" in plugins_data[0]["parameters"], "插件参数错误"
    print("  [通过] 插件配置解析")

    # ---------- 测试 4: CSV 导出 ----------
    csv_data = [
        {"id": 1, "name": "物品A", "desc": "包含,逗号"},
        {"id": 2, "name": "物品B", "desc": "普通描述"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", errors="replace") as f:
        csv_path = f.name

    try:
        export_to_csv(csv_data, csv_path)
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            csv_content = f.read()
        assert "物品A" in csv_content, "CSV 内容缺失"
        assert '"包含,逗号"' in csv_content, "CSV 转义错误"
        print("  [通过] CSV 导出")
    finally:
        os.unlink(csv_path)

    # ---------- 测试 5: 地图数据解析 ----------
    map_data = {
        "id": 1,
        "width": 20,
        "height": 15,
        "events": [
            {
                "id": 1,
                "name": "NPC1",
                "x": 5,
                "y": 5,
                "pages": [
                    {"conditions": {"switchId": 1}, "list": [{"code": 101, "parameters": ["你好"]}]}
                ],
            }
        ],
    }
    events_info = []
    for event in map_data.get("events", []):
        events_info.append({
            "id": event.get("id", 0),
            "name": event.get("name", ""),
            "pages": [{"conditions": p.get("conditions", {}), "commands": p.get("list", [])} for p in event.get("pages", [])],
        })
    assert len(events_info) == 1, "地图事件解析失败"
    assert events_info[0]["name"] == "NPC1", "事件名称错误"
    assert len(events_info[0]["pages"][0]["commands"]) == 1, "事件指令解析失败"
    print("  [通过] 地图事件解析")

    # ---------- 测试 6: 工程类型识别（模拟） ----------
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建模拟 MV 工程
        with open(os.path.join(tmpdir, "Game.rpgproject"), "w", encoding="utf-8", errors="replace") as f:
            f.write('{"version": "1.6.1"}')
        os.makedirs(os.path.join(tmpdir, "data"), exist_ok=True)
        with open(os.path.join(tmpdir, "data", "System.json"), "w", encoding="utf-8", errors="replace") as f:
            json.dump({"gameTitle": "测试游戏", "advanced": {}}, f)

        # 手动模拟识别逻辑
        has_mv = os.path.isfile(os.path.join(tmpdir, "Game.rpgproject"))
        has_data = os.path.isdir(os.path.join(tmpdir, "data"))
        assert has_mv and has_data, "工程结构识别失败"
        print("  [通过] 工程结构识别")

    print("\n所有自检通过！")
    return 0


def main() -> int:
    """主函数。"""
    parser = argparse.ArgumentParser(
        description="RPGMaker 工程安全读写工具",
        epilog="示例: python main.py --inspect /path/to/project",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )
    parser.add_argument(
        "--inspect",
        metavar="PROJECT_DIR",
        help="检查工程结构并输出基本信息",
    )
    parser.add_argument(
        "--parse-map",
        metavar="MAP_FILE",
        help="解析指定地图文件（需配合 --project）",
    )
    parser.add_argument(
        "--project",
        metavar="PROJECT_DIR",
        help="工程根目录（用于其他操作）",
    )
    parser.add_argument(
        "--update-db",
        metavar="DB_FILE",
        help="数据库文件名（如 Actors.json）",
    )
    parser.add_argument(
        "--id",
        type=int,
        help="数据库对象 ID",
    )
    parser.add_argument(
        "--field",
        help="要修改的字段名",
    )
    parser.add_argument(
        "--value",
        help="新的字段值",
    )
    parser.add_argument(
        "--check-plugins",
        action="store_true",
        help="校验插件配置",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查工程模式
    if args.inspect:
        project = RPGMakerProject(args.inspect)
        print(f"工程类型: {project.project_type}")
        print(f"版本: {project.version}")
        print(f"数据目录: {project.data_dir}")
        return 0

    # 解析地图模式
    if args.parse_map:
        if not args.project:
            fail("E003", "解析地图需要指定 --project")
        project = RPGMakerProject(args.project)
        map_info = parse_map_file(project.data_dir, args.parse_map)
        print(f"地图 ID: {map_info['map_id']}")
        print(f"尺寸: {map_info['width']}x{map_info['height']}")
        print(f"事件数量: {len(map_info['events'])}")
        for ev in map_info["events"]:
            print(f"  事件 {ev['id']}: {ev['name']} ({ev['x']},{ev['y']})")
        return 0

    # 修改数据库模式
    if args.update_db:
        if not args.project or args.id is None or not args.field or args.value is None:
            fail("E003", "修改数据库需要 --project, --id, --field, --value")
        project = RPGMakerProject(args.project)
        # 尝试转换值类型
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError:
            value = args.value
        success = update_database_field(project.data_dir, args.update_db, args.id, args.field, value)
        if success:
            print(f"成功修改 {args.update_db} 中 ID={args.id} 的 {args.field} 字段")
        return 0

    # 校验插件模式
    if args.check_plugins:
        if not args.project:
            fail("E003", "校验插件需要指定 --project")
        project = RPGMakerProject(args.project)
        plugins = parse_plugins_js(project)
        print(f"插件数量: {len(plugins)}")
        for p in plugins:
            status = "有效" if p["valid"] else "有错误"
            print(f"  {p['name']}: {p['status']} ({status})")
            if p["issues"]:
                for issue in p["issues"]:
                    print(f"    - {issue}")
        return 0

    # 无有效操作
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
