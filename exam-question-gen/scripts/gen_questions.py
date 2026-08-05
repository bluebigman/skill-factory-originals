#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_questions.py — 智能出题工具（exam-question-gen 真实实现）
按知识点/题型/难度自动抽题组卷，每题带答案与解析，支持难度分布控制。
纯标准库，零依赖。
"""
import argparse
import random
import sys

QUESTION_BANK = [
    # Python 基础
    {"point": "Python基础", "type": "单选", "difficulty": 1,
     "question": "Python 中用于定义函数的关键字是？",
     "options": ["A. function", "B. def", "C. func", "D. lambda"],
     "answer": "B", "analysis": "def 是函数定义关键字，lambda 定义匿名函数。"},
    {"point": "Python基础", "type": "单选", "difficulty": 1,
     "question": "下列哪个不是 Python 内置数据类型？",
     "options": ["A. list", "B. tuple", "C. array", "D. dict"],
     "answer": "C", "analysis": "array 属于 array 模块，非内置类型（内置是 list/tuple/dict/set）。"},
    {"point": "Python基础", "type": "判断", "difficulty": 1,
     "question": "Python 中列表(list)是可变对象。",
     "options": ["A. 正确", "B. 错误"],
     "answer": "A", "analysis": "list 可变，tuple 不可变。"},
    {"point": "Python基础", "type": "填空", "difficulty": 2,
     "question": "Python 中获取列表长度用内置函数 ____。",
     "options": [], "answer": "len()", "analysis": "len() 返回可迭代对象长度。"},
    {"point": "Python基础", "type": "单选", "difficulty": 2,
     "question": "表达式 7 // 2 的结果是？",
     "options": ["A. 3", "B. 3.5", "C. 4", "D. 2"],
     "answer": "A", "analysis": "// 是整除，7//2=3；/ 是浮点除 3.5。"},
    {"point": "Python基础", "type": "单选", "difficulty": 2,
     "question": "下列代码输出什么？print('a' + str(1))",
     "options": ["A. a1", "B. a+1", "C. 报错", "D. a 1"],
     "answer": "A", "analysis": "str(1)='1'，字符串拼接得 'a1'。"},
    # 数据结构
    {"point": "数据结构", "type": "单选", "difficulty": 1,
     "question": "栈(Stack)的特点是？",
     "options": ["A. 先进先出", "B. 先进后出", "C. 随机存取", "D. 无序"],
     "answer": "B", "analysis": "栈后进先出(LIFO)，队列先进先出(FIFO)。"},
    {"point": "数据结构", "type": "单选", "difficulty": 2,
     "question": "哈希表(HashTable)的平均查找时间复杂度是？",
     "options": ["A. O(n)", "B. O(log n)", "C. O(1)", "D. O(n²)"],
     "answer": "C", "analysis": "理想哈希平均 O(1)，最坏 O(n)。"},
    {"point": "数据结构", "type": "单选", "difficulty": 2,
     "question": "二叉树的前序遍历顺序是？",
     "options": ["A. 根-左-右", "B. 左-根-右", "C. 左-右-根", "D. 根-右-左"],
     "answer": "A", "analysis": "前序=根左右，中序=左根右，后序=左右根。"},
    {"point": "数据结构", "type": "判断", "difficulty": 1,
     "question": "队列(Queue)支持在两端进行插入和删除操作。",
     "options": ["A. 正确", "B. 错误"],
     "answer": "B", "analysis": "普通队列只允许一端插入、另一端删除；双端队列才两端都可。"},
    # 算法
    {"point": "算法", "type": "单选", "difficulty": 2,
     "question": "二分查找要求数据必须？",
     "options": ["A. 无序", "B. 有序", "C. 链式存储", "D. 哈希存储"],
     "answer": "B", "analysis": "二分查找前提是有序序列。"},
    {"point": "算法", "type": "单选", "difficulty": 3,
     "question": "快速排序的平均时间复杂度是？",
     "options": ["A. O(n)", "B. O(n log n)", "C. O(n²)", "D. O(log n)"],
     "answer": "B", "analysis": "快排平均 O(n log n)，最坏 O(n²)。"},
    {"point": "算法", "type": "填空", "difficulty": 2,
     "question": "动态规划的两个核心特征是重叠子问题和 ____。",
     "options": [], "answer": "最优子结构", "analysis": "DP 需满足最优子结构+重叠子问题。"},
    {"point": "算法", "type": "单选", "difficulty": 3,
     "question": "下列哪个算法是贪心算法的经典应用？",
     "options": ["A. 背包问题(分数)", "B. 最短路径(Dijkstra)", "C. 汉诺塔", "D. 斐波那契"],
     "answer": "A", "analysis": "分数背包可用贪心；Dijkstra 是贪心思想但通常归为图算法。"},
    # 网络
    {"point": "网络", "type": "单选", "difficulty": 1,
     "question": "HTTP 状态码 404 表示？",
     "options": ["A. 服务器错误", "B. 资源未找到", "C. 重定向", "D. 认证失败"],
     "answer": "B", "analysis": "404=Not Found；500 服务器错误；301 重定向；401 未认证。"},
    {"point": "网络", "type": "单选", "difficulty": 2,
     "question": "TCP 三次握手的第二个报文是？",
     "options": ["A. SYN", "B. SYN+ACK", "C. ACK", "D. FIN"],
     "answer": "B", "analysis": "①SYN ②SYN+ACK ③ACK。"},
    {"point": "网络", "type": "单选", "difficulty": 2,
     "question": "DNS 的主要作用是？",
     "options": ["A. 分配IP", "B. 域名转IP", "C. 加密传输", "D. 负载均衡"],
     "answer": "B", "analysis": "DNS 将域名解析为 IP 地址。"},
    {"point": "网络", "type": "判断", "difficulty": 1,
     "question": "HTTPS 相比 HTTP 增加了加密层(TLS/SSL)。",
     "options": ["A. 正确", "B. 错误"],
     "answer": "A", "analysis": "HTTPS = HTTP + TLS/SSL 加密。"},
    # 数据库
    {"point": "数据库", "type": "单选", "difficulty": 1,
     "question": "SQL 中用于查询数据的关键字是？",
     "options": ["A. SELECT", "B. INSERT", "C. UPDATE", "D. DELETE"],
     "answer": "A", "analysis": "SELECT 查询；INSERT 插入；UPDATE 更新；DELETE 删除。"},
    {"point": "数据库", "type": "单选", "difficulty": 2,
     "question": "数据库事务的 ACID 中 I 代表？",
     "options": ["A. 原子性", "B. 一致性", "C. 隔离性", "D. 持久性"],
     "answer": "C", "analysis": "A原子性 C一致性 I隔离性 D持久性。"},
    {"point": "数据库", "type": "填空", "difficulty": 2,
     "question": "SQL 中用于去重的关键字是 ____。",
     "options": [], "answer": "DISTINCT", "analysis": "SELECT DISTINCT col FROM t 去重。"},
    # 操作系统
    {"point": "操作系统", "type": "单选", "difficulty": 1,
     "question": "进程与线程的关系，下列正确的是？",
     "options": ["A. 进程是线程的子集", "B. 线程是进程内的执行单元", "C. 两者无关", "D. 进程必须多线程"],
     "answer": "B", "analysis": "进程是资源分配单位，线程是 CPU 调度单位（进程内）。"},
    {"point": "操作系统", "type": "单选", "difficulty": 2,
     "question": "死锁产生的四个必要条件不包括？",
     "options": ["A. 互斥", "B. 请求与保持", "C. 不可剥夺", "D. 资源足够"],
     "answer": "D", "analysis": "互斥/请求保持/不可剥夺/循环等待；资源足够不构成死锁条件。"},
    {"point": "操作系统", "type": "判断", "difficulty": 1,
     "question": "虚拟内存技术允许程序使用超过物理内存的地址空间。",
     "options": ["A. 正确", "B. 错误"],
     "answer": "A", "analysis": "虚拟内存通过页交换实现大地址空间。"},
    # Linux
    {"point": "Linux", "type": "单选", "difficulty": 1,
     "question": "Linux 中查看当前目录的命令是？",
     "options": ["A. ls", "B. cd", "C. pwd", "D. cat"],
     "answer": "C", "analysis": "pwd 打印当前目录；ls 列出文件；cd 切换目录。"},
    {"point": "Linux", "type": "单选", "difficulty": 1,
     "question": "Linux 中查看进程快照的命令是？",
     "options": ["A. ps", "B. top", "C. netstat", "D. grep"],
     "answer": "A", "analysis": "ps 静态快照；top 动态实时。"},
    {"point": "Linux", "type": "单选", "difficulty": 2,
     "question": "chmod 755 表示的权限是？",
     "options": ["A. rwxr-xr-x", "B. rwxrwxrwx", "C. rwxr--r--", "D. r--r-xr-x"],
     "answer": "A", "analysis": "7=rwx 5=r-x：属主rwx、组r-x、其他r-x。"},
    # 数学
    {"point": "数学", "type": "单选", "difficulty": 2,
     "question": "log₂(32) 的值是？",
     "options": ["A. 4", "B. 5", "C. 6", "D. 16"],
     "answer": "B", "analysis": "2⁵=32，故 log₂32=5。"},
    {"point": "数学", "type": "单选", "difficulty": 2,
     "question": "欧拉公式 e^(iπ) + 1 = ?",
     "options": ["A. 0", "B. 1", "C. i", "D. π"],
     "answer": "A", "analysis": "e^(iπ)=-1，故 +1=0。"},
    {"point": "数学", "type": "填空", "difficulty": 3,
     "question": "斐波那契数列第 7 项（从 F₀=0 起）是 ____。",
     "options": [], "answer": "13", "analysis": "0,1,1,2,3,5,8,13... 第7项=13。"},
    # 正则
    {"point": "正则", "type": "单选", "difficulty": 2,
     "question": "正则中 \\\\d 匹配什么？",
     "options": ["A. 任意数字", "B. 任意字母", "C. 空白", "D. 任意字符"],
     "answer": "A", "analysis": "\\d=数字 [0-9]；\\w=单词字符；\\s=空白；. =任意字符。"},
    {"point": "正则", "type": "单选", "difficulty": 2,
     "question": "正则中 * 表示？",
     "options": ["A. 出现0次或多次", "B. 出现1次或多次", "C. 出现0次或1次", "D. 恰好1次"],
     "answer": "A", "analysis": "* = 0~n次；+ = 1~n次；? = 0~1次。"},
]


def pick_questions(count, types, points, difficulty):
    """抽题：按难度分布 + 题型/知识点过滤，去重"""
    pool = QUESTION_BANK
    if points:
        pool = [q for q in pool if q["point"] in points]
    if types:
        pool = [q for q in pool if q["type"] in types]
    if difficulty:
        if isinstance(difficulty, str) and "-" in difficulty:
            lo, hi = map(int, difficulty.split("-"))
            pool = [q for q in pool if lo <= q["difficulty"] <= hi]
        else:
            d = int(difficulty)
            pool = [q for q in pool if q["difficulty"] == d]
    # 难度分布：优先覆盖 1-5 级
    ordered = []
    for d in range(1, 6):
        ordered += [q for q in pool if q["difficulty"] == d]
    ordered += [q for q in pool if q not in ordered]
    picked, seen = [], set()
    for q in ordered:
        if len(picked) >= count:
            break
        key = q["question"]
        if key in seen:
            continue
        seen.add(key)
        picked.append(q)
    if len(picked) < count:
        for q in pool:
            if len(picked) >= count:
                break
            if q not in picked:
                picked.append(q)
    return picked


def render(picked, answer_only=False):
    lines = []
    for i, q in enumerate(picked, 1):
        lines.append(f"{i}. [{q['point']}|{q['type']}|难度{q['difficulty']}] {q['question']}")
        for opt in q["options"]:
            lines.append(f"   {opt}")
        if answer_only:
            lines.append(f"   答案: {q['answer']}")
    if not answer_only:
        lines.append("\n--- 答案与解析 ---")
        for i, q in enumerate(picked, 1):
            lines.append(f"{i}. 答案: {q['answer']}  解析: {q['analysis']}")
    return "\n".join(lines)


def selftest() -> bool:
    print("🔧 运行自检...")
    if len(QUESTION_BANK) < 30:
        print(f"  ❌ 题库仅 {len(QUESTION_BANK)} 题")
        return False
    points = {q["point"] for q in QUESTION_BANK}
    if len(points) < 8:
        print(f"  ❌ 知识点仅 {len(points)} 个")
        return False
    picked = pick_questions(5, [], [], "")
    if len(picked) != 5 or len({q["question"] for q in picked}) != 5:
        print("  ❌ 抽题数量/去重异常")
        return False
    p2 = pick_questions(3, ["单选"], [], "")
    if not all(q["type"] == "单选" for q in p2):
        print("  ❌ 题型过滤异常")
        return False
    p3 = pick_questions(3, [], [], "1-2")
    if not all(q["difficulty"] in (1, 2) for q in p3):
        print("  ❌ 难度过滤异常")
        return False
    if not render(picked) or not render(picked, answer_only=True):
        print("  ❌ 渲染异常")
        return False
    print(f"  ✅ 题库 {len(QUESTION_BANK)} 题 / {len(points)} 知识点")
    print("  ✅ 抽题/过滤/去重/渲染正常")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="智能出题：按知识点/题型/难度自动组卷")
    ap.add_argument("--count", "-n", type=int, default=5, help="题目数量（默认5）")
    ap.add_argument("--types", default="", help="题型过滤，逗号分隔（单选,多选,判断,填空,简答）")
    ap.add_argument("--points", default="", help="知识点过滤，逗号分隔")
    ap.add_argument("--difficulty", default="", help="难度过滤：单值 3 或范围 1-3")
    ap.add_argument("--output", "-o", default="", help="输出到 Markdown 文件")
    ap.add_argument("--answer-only", action="store_true", help="只输出答案")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--version", action="version", version="gen_questions 1.0.0")
    args = ap.parse_args()

    if args.selftest:
        return 0 if selftest() else 1

    types = [t.strip() for t in args.types.split(",") if t.strip()] if args.types else []
    points = [p.strip() for p in args.points.split(",") if p.strip()] if args.points else []
    if args.count < 1 or args.count > 50:
        print("❌ --count 需在 1-50 之间")
        return 1
    picked = pick_questions(args.count, types, points, args.difficulty)
    if not picked:
        print("❌ 无符合条件的题目，请调整过滤条件")
        return 1
    text = render(picked, args.answer_only)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"📄 已输出: {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
