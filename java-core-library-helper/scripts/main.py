#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Java核心库助手 - 命令行工具
提供 Google Guava 等 Java 核心库的使用指南生成能力。
"""

import argparse
import sys
import os
import re
import json
import tempfile
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Any

dry_run = False  # v3.268 模块级 dry-run 标志

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理该请求",
    "E005": "置信度过低，结果无法确定",
    "E006": "文件读取失败，请检查文件路径和权限",
    "E007": "文件写入失败，请检查磁盘空间和权限",
    "E008": "参数校验失败，请检查命令行参数",
    "E009": "内部逻辑错误，请报告开发者",
    "E010": "未知异常，请查看错误详情",
}

# ============================================================
# 核心数据结构
# ============================================================

# 能力边界声明（与功能规格一致）
CAPABILITIES = {
    "can_do": [
        "生成 Guava 集合操作指南",
        "生成 Guava 缓存使用指南",
        "生成 Guava 并发工具指南",
        "生成 Guava 函数式编程指南",
        "支持批量处理和自定义格式",
    ],
    "cannot_do": [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ],
}

# 触发词表
TRIGGER_WORDS = ["guava", "java库", "集合操作", "java缓存", "并发工具", "函数式编程"]

# 标准流程步骤
STANDARD_FLOW = [
    "Step 1: 收集最小信息集 - 确认输入来源、输出格式要求、期望完整度",
    "Step 2: 执行核心流程 - 解析输入、识别关键信息、按规则处理、生成结果",
    "Step 3: 输出与校验 - 整理结果、自查字段完整性、标注置信度",
]

# 常见问题
FAQ = [
    ("处理速度如何？", "骨架结果 1 分钟内，详细结果视输入量而定"),
    ("会不会出错？", "低置信度内容会标注 [需核实]，请人工复核关键结果"),
    ("支持哪些输入？", "用户提供的数据/文件/URL"),
]

# ============================================================
# Guava 指南生成核心逻辑
# ============================================================

GUAVA_GUIDES = {
    "collection": {
        "title": "Guava 集合操作指南",
        "description": "Guava 提供了丰富的集合工具类，以下是常用 API 示例：",
        "examples": [
            {
                "name": "ImmutableList 不可变列表",
                "code": """
// 创建不可变列表
ImmutableList<String> list = ImmutableList.of("a", "b", "c");
ImmutableList<String> list2 = ImmutableList.<String>builder()
    .add("a").add("b").build();

// 从已有集合创建
List<String> original = Arrays.asList("x", "y");
ImmutableList<String> copy = ImmutableList.copyOf(original);
""",
                "usage": "不可变集合保证线程安全，适合作为常量或配置数据"
            },
            {
                "name": "Multimap 多值映射",
                "code": """
// 创建 ArrayListMultimap
Multimap<String, Integer> multimap = ArrayListMultimap.create();
multimap.put("key1", 1);
multimap.put("key1", 2);
multimap.put("key2", 3);

// 获取所有值
Collection<Integer> values = multimap.get("key1"); // [1, 2]

// 遍历所有键值对
for (Map.Entry<String, Integer> entry : multimap.entries()) {
    System.out.println(entry.getKey() + " -> " + entry.getValue());
}
""",
                "usage": "Multimap 解决一个键对应多个值的场景，避免 Map<String, List<V>> 的繁琐操作"
            },
            {
                "name": "BiMap 双向映射",
                "code": """
// 创建 HashBiMap
BiMap<String, Integer> biMap = HashBiMap.create();
biMap.put("one", 1);
biMap.put("two", 2);

// 反向查询
BiMap<Integer, String> inverse = biMap.inverse();
String key = inverse.get(1); // "one"

// 强制放入（会覆盖已有映射）
biMap.forcePut("uno", 1);
""",
                "usage": "BiMap 提供键值双向查询，适合需要反向查找的场景"
            },
            {
                "name": "Lists/Maps/Sets 工具类",
                "code": """
// Lists 工具类
List<String> list = Lists.newArrayList("a", "b", "c");
List<List<String>> partition = Lists.partition(list, 2); // 分片

// Maps 工具类
Map<String, Integer> map = Maps.newHashMap();
Map<String, Integer> sortedMap = Maps.newTreeMap();

// Sets 工具类
Set<String> set = Sets.newHashSet("a", "b");
Set<String> union = Sets.union(set, Sets.newHashSet("b", "c"));
Set<String> intersection = Sets.intersection(set, Sets.newHashSet("b"));
""",
                "usage": "工具类提供便捷的创建和操作集合的方法"
            }
        ]
    },
    "cache": {
        "title": "Guava 缓存使用指南",
        "description": "Guava Cache 提供本地缓存解决方案，支持自动过期和回收：",
        "examples": [
            {
                "name": "LoadingCache 自动加载缓存",
                "code": """
// 创建 LoadingCache
LoadingCache<String, User> cache = CacheBuilder.newBuilder()
    .maximumSize(1000)                    // 最大容量
    .expireAfterWrite(10, TimeUnit.MINUTES) // 写入后10分钟过期
    .build(new CacheLoader<String, User>() {
        @Override
        public User load(String key) throws Exception {
            return loadUserFromDB(key); // 从数据库加载
        }
    });

// 使用缓存
User user = cache.get("user-123"); // 缓存未命中时自动加载
User user2 = cache.getUnchecked("user-456"); // 不抛出异常版本
""",
                "usage": "LoadingCache 适合需要自动加载数据的场景，减少重复查询"
            },
            {
                "name": "CacheBuilder 配置",
                "code": """
// 创建 Cache 实例
Cache<String, Object> cache = CacheBuilder.newBuilder()
    .maximumSize(10000)                    // 最大条目数
    .maximumWeight(100000)                 // 最大权重
    .weigher((key, value) -> value.toString().length()) // 权重计算
    .expireAfterAccess(5, TimeUnit.MINUTES) // 访问后5分钟过期
    .expireAfterWrite(1, TimeUnit.HOURS)    // 写入后1小时过期
    .refreshAfterWrite(30, TimeUnit.MINUTES) // 写入后30分钟刷新
    .recordStats()                          // 记录统计信息
    .build();

// 手动操作
cache.put("key", "value");
Object value = cache.getIfPresent("key");
cache.invalidate("key");
cache.cleanUp(); // 清理过期条目
""",
                "usage": "CacheBuilder 提供灵活的缓存配置选项"
            },
            {
                "name": "缓存统计与监听",
                "code": """
// 创建带统计的缓存
LoadingCache<String, String> cache = CacheBuilder.newBuilder()
    .recordStats()
    .removalListener(new RemovalListener<String, String>() {
        @Override
        public void onRemoval(RemovalNotification<String, String> notification) {
            System.out.println("移除: " + notification.getKey() + 
                " 原因: " + notification.getCause());
        }
    })
    .build(new CacheLoader<String, String>() {
        @Override
        public String load(String key) {
            return "value-" + key;
        }
    });

// 获取统计信息
CacheStats stats = cache.stats();
long hitRate = stats.hitRate(); // 命中率
long missCount = stats.missCount(); // 未命中次数
""",
                "usage": "统计信息帮助监控缓存性能，监听器处理缓存移除事件"
            }
        ]
    },
    "concurrency": {
        "title": "Guava 并发工具指南",
        "description": "Guava 提供强大的并发工具，简化多线程编程：",
        "examples": [
            {
                "name": "ListenableFuture 可监听异步任务",
                "code": """
// 创建线程池
ListeningExecutorService service = MoreExecutors.listeningDecorator(
    Executors.newFixedThreadPool(10));

// 提交异步任务
ListenableFuture<String> future = service.submit(() -> {
    Thread.sleep(1000);
    return "任务完成";
});

// 添加回调
Futures.addCallback(future, new FutureCallback<String>() {
    @Override
    public void onSuccess(String result) {
        System.out.println("成功: " + result);
    }
    
    @Override
    public void onFailure(Throwable t) {
        System.err.println("失败: " + t.getMessage());
    }
}, service);

// 组合多个异步任务
ListenableFuture<String> combined = Futures.transform(
    future,
    input -> input + " - 处理完成",
    service
);
""",
                "usage": "ListenableFuture 支持回调机制，避免阻塞等待异步结果"
            },
            {
                "name": "RateLimiter 限流器",
                "code": """
// 创建限流器：每秒允许2个请求
RateLimiter limiter = RateLimiter.create(2.0);

// 尝试获取许可
for (int i = 0; i < 10; i++) {
    if (limiter.tryAcquire()) {
        System.out.println("请求 " + i + " 被允许");
    } else {
        System.out.println("请求 " + i + " 被限流");
    }
}

// 阻塞获取许可
limiter.acquire(); // 会阻塞直到获取许可

// 批量获取
limiter.acquire(5); // 获取5个许可
""",
                "usage": "RateLimiter 控制请求速率，保护下游服务"
            },
            {
                "name": "Striped 锁分离",
                "code": """
// 创建 Striped 锁（256个锁）
Striped<Lock> stripedLocks = Striped.lock(256);

// 根据 key 获取对应锁
String key = "user-123";
Lock lock = stripedLocks.get(key);

// 使用锁
lock.lock();
try {
    // 临界区代码
    System.out.println("处理 " + key);
} finally {
    lock.unlock();
}

// 使用读写锁
Striped<ReadWriteLock> stripedRW = Striped.readWriteLock(128);
ReadWriteLock rwLock = stripedRW.get("data-key");
Lock readLock = rwLock.readLock();
Lock writeLock = rwLock.writeLock();
""",
                "usage": "Striped 提供细粒度锁，减少锁竞争"
            }
        ]
    },
    "functional": {
        "title": "Guava 函数式编程指南",
        "description": "Guava 提供函数式编程支持，简化集合操作：",
        "examples": [
            {
                "name": "Function 函数接口",
                "code": """
// 定义函数
Function<String, Integer> lengthFunction = new Function<String, Integer>() {
    @Override
    public Integer apply(String input) {
        return input.length();
    }
};

// 使用函数转换集合
List<String> names = Arrays.asList("Alice", "Bob", "Charlie");
List<Integer> lengths = Lists.transform(names, lengthFunction);

// 使用 Predicate 过滤
Predicate<String> startsWithA = new Predicate<String>() {
    @Override
    public boolean apply(String input) {
        return input.startsWith("A");
    }
};

Collection<String> filtered = Collections2.filter(names, startsWithA);
""",
                "usage": "Function 和 Predicate 提供函数式操作集合的能力"
            },
            {
                "name": "FluentIterable 链式操作",
                "code": """
// 创建 FluentIterable
FluentIterable<String> iterable = FluentIterable.from(Arrays.asList(
    "apple", "banana", "cherry", "date"
));

// 链式操作
List<String> result = iterable
    .filter(s -> s.length() > 4)      // 过滤长度大于4的
    .transform(String::toUpperCase)    // 转大写
    .limit(2)                          // 取前2个
    .toList();                         // 转为 List

// 其他操作
boolean anyMatch = iterable.anyMatch(s -> s.startsWith("a"));
boolean allMatch = iterable.allMatch(s -> s.length() > 2);
Optional<String> first = iterable.first();
""",
                "usage": "FluentIterable 提供流畅的链式集合操作"
            },
            {
                "name": "Optional 空值处理",
                "code": """
// 创建 Optional
Optional<String> present = Optional.of("value");
Optional<String> absent = Optional.absent();
Optional<String> fromNullable = Optional.fromNullable(null);

// 安全获取值
String value = present.get(); // "value"
String defaultValue = absent.or("default"); // "default"
String orNull = absent.orNull(); // null

// 转换和过滤
Optional<Integer> length = present.transform(String::length);
Optional<String> filtered = present.filter(s -> s.length() > 3);

// 判断
boolean isPresent = present.isPresent(); // true
""",
                "usage": "Optional 优雅处理可能为 null 的值，避免 NullPointerException"
            }
        ]
    }
}


def generate_guava_guide(topic: str) -> Dict[str, Any]:
    """
    根据主题生成 Guava 使用指南。
    
    Args:
        topic: 主题类型 (collection/cache/concurrency/functional)
    
    Returns:
        包含指南内容的字典
    """
    topic = topic.lower()
    if topic not in GUAVA_GUIDES:
        return {
            "success": False,
            "error_code": "E004",
            "error_msg": f"{ERROR_CODES['E004']} 不支持的指南主题: {topic}",
            "data": None
        }
    
    guide_data = GUAVA_GUIDES[topic]
    timestamp = datetime.now(timezone.utc).isoformat()
    
    return {
        "success": True,
        "error_code": None,
        "error_msg": None,
        "data": {
            "topic": topic,
            "title": guide_data["title"],
            "description": guide_data["description"],
            "examples": guide_data["examples"],
            "generated_at": timestamp,
            "source": "Guava 官方文档与最佳实践",
            "confidence": 0.95
        }
    }


# ============================================================
# 输入校验函数
# ============================================================

def _read_text_safe(path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    多编码安全读取文件。
    
    Args:
        path: 文件路径
    
    Returns:
        (文件内容, 错误码) - 成功时错误码为 None
    """
    if not os.path.exists(path):
        return None, "E006"
    
    try:
        for enc in ("utf-8", "gbk", "gb18030"):
            try:
                with open(path, encoding=enc) as f:
                    return f.read(), None
            except UnicodeDecodeError:
                continue
        
        # 所有编码都失败，使用 errors=replace
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(), None
    except PermissionError:
        return None, "E006"
    except OSError as e:
        print(f"警告: 文件读取失败 - {str(e)}", file=sys.stderr)
        return None, "E006"


def _iter_lines(path: str):
    """
    流式读取文件行，复用 _read_text_safe 的编码回退逻辑。
    
    Args:
        path: 文件路径
    
    Yields:
        文件中的每一行
    """
    content, error_code = _read_text_safe(path)
    if error_code is not None:
        raise IOError(f"文件读取失败: {path}")
    
    for line in content.splitlines():
        yield line


def validate_input(data: Any) -> Tuple[bool, str]:
    """
    校验输入数据是否合法。
    
    返回: (是否合法, 错误信息)
    """
    if data is None:
        return False, ERROR_CODES["E001"]
    if isinstance(data, str) and not data.strip():
        return False, ERROR_CODES["E001"]
    if isinstance(data, (list, dict, tuple)) and len(data) == 0:
        return False, ERROR_CODES["E001"]
    return True, ""


def validate_output_format(fmt: str) -> Tuple[bool, str]:
    """
    校验输出格式参数。
    
    支持: text, json, table
    """
    allowed = {"text", "json", "table"}
    if fmt not in allowed:
        return False, f"{ERROR_CODES['E003']} 支持的格式: {', '.join(sorted(allowed))}"
    return True, ""


def validate_confidence_threshold(threshold: float) -> Tuple[bool, str]:
    """
    校验置信度阈值参数。
    """
    if not isinstance(threshold, (int, float)):
        return False, f"{ERROR_CODES['E008']} 置信度阈值必须是数字"
    if threshold < 0 or threshold > 1:
        return False, f"{ERROR_CODES['E008']} 置信度阈值必须在 0-1 之间"
    return True, ""


# ============================================================
# 核心逻辑函数
