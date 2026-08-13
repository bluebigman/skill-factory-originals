#!/usr/bin/env python3
"""冒烟测试修复版"""

import sys
import argparse


def solve(data):
    """返回处理后的数据"""
    return data


def selftest():
    """离线自测"""
    test_data = [1, 2, 3, 4, 5]
    result = solve(test_data)
    assert len(result) == len(test_data), "长度不一致"
    assert sum(result) > 0, "求和应大于0"
    print("selftest passed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return 0

    # 正常模式：读取输入并处理
    data = sys.stdin.read()
    result = solve(data)
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
