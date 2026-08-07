#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simply-versioned — 模型版本 轻量追踪 历史回溯

独立实现脚本，仅依据功能规格设计。
提供版本快照、版本回溯、非侵入集成、轻量存储等核心能力。

用法示例:
    # 基本使用
    model = VersionedModel("user_1")
    model.set_data({"name": "Alice", "age": 30})
    model.save()                    # 保存并记录版本快照
    model.set_data({"name": "Alice", "age": 31})
    model.save()                    # 再次保存，记录第二个版本
    model.restore(1)                # 回溯到第1个版本

    # 自检
    python scripts/main.py --selftest
"""

import json
import sys
import copy
from datetime import datetime, timezone
from collections import OrderedDict

# 错误码定义
ERROR_CODES = {
    "E001": "无效的版本号",
    "E002": "版本数据不存在",
    "E003": "数据序列化失败",
    "E004": "数据反序列化失败",
    "E005": "版本存储目录不可用",
    "E006": "无效的数据格式",
    "E007": "版本号为非整数",
    "E008": "版本号超出范围",
    "E009": "存储引擎初始化失败",
    "E010": "未指定的通用错误",
}


class VersionError(Exception):
    """版本管理相关异常"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


class VersionStorage:
    """轻量版本存储引擎

    使用内存字典存储版本数据，支持序列化到 JSON 文件。
    不额外建表，以序列化形式存储版本快照。
    """

    def __init__(self, storage_path: str = None):
        """初始化存储引擎

        Args:
            storage_path: 可选，存储文件路径。为 None 时仅使用内存存储。
        """
        self._storage_path = storage_path
        self._versions = OrderedDict()  # 有序字典，key 为版本号，value 为快照数据
        self._current_version = 0

        # 如果指定了存储路径，尝试加载已有数据
        if storage_path:
            try:
                self._load_from_file()
            except (IOError, OSError) as exc:
                raise VersionError("E005", f"无法读取存储文件: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise VersionError("E004", f"存储文件格式错误: {exc}") from exc

    def _load_from_file(self):
        """从文件加载版本数据"""
        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._versions = OrderedDict(data.get("versions", {}))
                self._current_version = data.get("current_version", 0)
        except FileNotFoundError:
            # 文件不存在时使用空数据
            pass

    def _save_to_file(self):
        """保存版本数据到文件"""
        if not self._storage_path:
            return
        try:
            data = {
                "versions": dict(self._versions),
                "current_version": self._current_version,
            }
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except (IOError, OSError) as exc:
            raise VersionError("E005", f"无法写入存储文件: {exc}") from exc

    def snapshot(self, data: dict) -> int:
        """记录一个版本快照

        Args:
            data: 要保存的数据快照（字典类型）

        Returns:
            int: 新版本号

        Raises:
            VersionError: E003 序列化失败，E006 数据格式错误
        """
        if not isinstance(data, dict):
            raise VersionError("E006", "快照数据必须是字典类型")

        # 深拷贝数据，避免外部修改影响
        try:
            snapshot_data = copy.deepcopy(data)
            # 验证可序列化
            json.dumps(snapshot_data, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise VersionError("E003", f"数据无法序列化: {exc}") from exc

        # 生成新版本号
        self._current_version += 1

        # 记录版本元信息
        version_entry = {
            "data": snapshot_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": self._current_version,
        }

        self._versions[str(self._current_version)] = version_entry
        self._save_to_file()
        return self._current_version

    def restore(self, version: int) -> dict:
        """恢复到指定版本

        Args:
            version: 目标版本号

        Returns:
            dict: 恢复的数据快照

        Raises:
            VersionError: E001/E007/E008 版本号无效，E002 版本不存在
        """
        if not isinstance(version, int):
            raise VersionError("E007", f"版本号必须是整数，收到: {type(version).__name__}")

        if version < 1:
            raise VersionError("E001", f"版本号必须大于0，收到: {version}")

        version_key = str(version)
        if version_key not in self._versions:
            raise VersionError("E002", f"版本 {version} 不存在")

        entry = self._versions[version_key]
        try:
            # 深拷贝返回，避免调用方修改内部数据
            return copy.deepcopy(entry["data"])
        except (KeyError, TypeError) as exc:
            raise VersionError("E004", f"版本数据损坏: {exc}") from exc

    def get_version_list(self) -> list:
        """获取所有版本号列表

        Returns:
            list: 按时间顺序排列的版本号列表
        """
        return [int(k) for k in self._versions.keys()]

    def get_version_info(self, version: int) -> dict:
        """获取版本元信息

        Args:
            version: 版本号

        Returns:
            dict: 包含版本数据、时间戳等信息的字典
        """
        version_key = str(version)
        if version_key not in self._versions:
            raise VersionError("E002", f"版本 {version} 不存在")
        return copy.deepcopy(self._versions[version_key])

    def clear(self):
        """清空所有版本数据"""
        self._versions.clear()
        self._current_version = 0
        self._save_to_file()


class VersionedModel:
    """版本化模型基类

    提供版本快照和回溯能力的模型基类。
    使用方式：继承此类，在保存时调用 save() 自动记录版本。

    示例:
        class User(VersionedModel):
            def __init__(self, user_id):
                super().__init__(f"user_{user_id}")
                self.set_data({"name": "", "age": 0})
    """

    def __init__(self, model_id: str, storage_path: str = None):
        """初始化模型

        Args:
            model_id: 模型唯一标识
            storage_path: 可选，存储文件路径
        """
        self._model_id = model_id
        self._data = {}
        self._storage = VersionStorage(storage_path)
        self._is_modified = False

    def set_data(self, data: dict):
        """设置模型数据

        Args:
            data: 要设置的数据字典
        """
        if not isinstance(data, dict):
            raise VersionError("E006", "数据必须是字典类型")
        self._data = copy.deepcopy(data)
        self._is_modified = True

    def get_data(self) -> dict:
        """获取当前数据

        Returns:
            dict: 当前数据的深拷贝
        """
        return copy.deepcopy(self._data)

    def save(self) -> int:
        """保存当前状态并记录版本快照

        Returns:
            int: 新版本号
        """
        version = self._storage.snapshot(self._data)
        self._is_modified = False
        return version

    def restore(self, version: int) -> dict:
        """恢复到指定版本

        Args:
            version: 目标版本号

        Returns:
            dict: 恢复后的数据
        """
        restored_data = self._storage.restore(version)
        self._data = restored_data
        self._is_modified = True
        return self.get_data()

    def get_version_history(self) -> list:
        """获取版本历史

        Returns:
            list: 版本号列表
        """
        return self._storage.get_version_list()

    def get_version_info(self, version: int) -> dict:
        """获取指定版本的详细信息

        Args:
            version: 版本号

        Returns:
            dict: 版本信息
        """
        return self._storage.get_version_info(version)

    def is_modified(self) -> bool:
        """检查数据是否被修改但未保存

        Returns:
            bool: True 表示有未保存的修改
        """
        return self._is_modified


def run_selftest() -> bool:
    """运行内置自检

    使用内置样例数据验证核心逻辑，不依赖外部文件/网络。

    Returns:
        bool: True 表示自检通过
    """
    print("=" * 60)
    print("simply-versioned 自检程序")
    print("=" * 60)

    try:
        # 测试1: 基本版本记录
        print("\n[测试1] 基本版本记录")
        model = VersionedModel("test_model")
        model.set_data({"name": "张三", "age": 25, "city": "北京"})
        v1 = model.save()
        assert v1 == 1, f"第一个版本号应为1，实际为 {v1}"
        print(f"  ✓ 首次保存成功，版本号: {v1}")

        # 测试2: 多次保存生成多个版本
        print("\n[测试2] 多次保存生成多个版本")
        model.set_data({"name": "张三", "age": 26, "city": "北京"})
        v2 = model.save()
        model.set_data({"name": "张三", "age": 27, "city": "上海"})
        v3 = model.save()
        assert v2 == 2 and v3 == 3, f"版本号应递增，实际为 {v2}, {v3}"
        assert model.get_version_history() == [1, 2, 3], "版本历史不正确"
        print(f"  ✓ 共保存 {len(model.get_version_history())} 个版本: {model.get_version_history()}")

        # 测试3: 版本回溯
        print("\n[测试3] 版本回溯")
        restored = model.restore(1)
        assert restored == {"name": "张三", "age": 25, "city": "北京"}, "回溯到版本1的数据不正确"
        print(f"  ✓ 成功回溯到版本1: {restored}")

        # 测试4: 回溯后再恢复
        print("\n[测试4] 回溯后再次恢复")
        restored = model.restore(3)
        assert restored == {"name": "张三", "age": 27, "city": "上海"}, "回溯到版本3的数据不正确"
        print(f"  ✓ 成功回溯到版本3: {restored}")

        # 测试5: 错误处理 - 不存在的版本
        print("\n[测试5] 错误处理 - 不存在的版本")
        try:
            model.restore(99)
            raise AssertionError("应该抛出 E002 错误")
        except VersionError as exc:
            assert exc.code == "E002", f"错误码应为 E002，实际为 {exc.code}"
            print(f"  ✓ 正确抛出错误: {exc}")

        # 测试6: 错误处理 - 无效版本号
        print("\n[测试6] 错误处理 - 无效版本号")
        try:
            model.restore(-1)
            raise AssertionError("应该抛出 E001 错误")
        except VersionError as exc:
            assert exc.code == "E001", f"错误码应为 E001，实际为 {exc.code}"
            print(f"  ✓ 正确抛出错误: {exc}")

        # 测试7: 数据独立性
        print("\n[测试7] 数据独立性")
        original_data = {"name": "李四", "age": 30}
        model.set_data(original_data)
        original_data["age"] = 99  # 修改外部数据
        saved_data = model.get_data()
        assert saved_data["age"] == 30, "外部数据修改不应影响模型数据"
        print("  ✓ 数据深拷贝生效，外部修改不影响模型")

        # 测试8: 版本信息元数据
        print("\n[测试8] 版本信息元数据")
        info = model.get_version_info(1)
        assert "timestamp" in info, "版本信息应包含时间戳"
        assert "data" in info, "版本信息应包含数据"
        assert "version" in info, "版本信息应包含版本号"
        print(f"  ✓ 版本信息包含时间戳、数据和版本号")

        # 测试9: 修改标记
        print("\n[测试9] 修改标记")
        model.set_data({"name": "王五", "age": 40})
        assert model.is_modified(), "设置数据后应标记为已修改"
        model.save()
        assert not model.is_modified(), "保存后不应标记为已修改"
        print("  ✓ 修改标记逻辑正确")

        # 测试10: 数据格式验证
        print("\n[测试10] 数据格式验证")
        try:
            model.set_data("not_a_dict")
            raise AssertionError("应该抛出 E006 错误")
        except VersionError as exc:
            assert exc.code == "E006", f"错误码应为 E006，实际为 {exc.code}"
            print(f"  ✓ 正确拒绝非字典数据: {exc}")

        print("\n" + "=" * 60)
        print("所有自检测试通过！✓")
        print("=" * 60)
        return True

    except AssertionError as exc:
        print(f"\n✗ 自检失败: {exc}")
        return False
    except VersionError as exc:
        print(f"\n✗ 自检遇到版本错误: {exc}")
        return False
    except Exception as exc:
        print(f"\n✗ 自检遇到未预期错误: {exc}")
        return False


def main():
    """主入口函数"""
    # 处理命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 正常模式：显示帮助信息
    print("simply-versioned — 模型版本 轻量追踪 历史回溯")
    print()
    print("用法:")
    print("  python scripts/main.py --selftest    运行内置自检")
    print()
    print("功能特性:")
    print("  - 版本快照: 在模型每次保存时自动记录一份数据快照")
    print("  - 版本回溯: 将模型恢复到任意历史版本的状态")
    print("  - 非侵入集成: 仅需在模型中引入一个模块，无需改动表结构")
    print("  - 轻量存储: 版本数据以序列化形式存储，不额外建表")
    print()
    print("能力边界:")
    print("  - 不支持字段级 diff")
    print("  - 不自动清理旧版本")
    print("  - 不处理关联对象")
    print("  - 不提供版本合并")


if __name__ == "__main__":
    main()
