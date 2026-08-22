---
slug: java-core-library-helper
name: java-core-library-helper
displayName: Java核心库 集合缓存并发 速查
description: Guava与Java核心库实用指南，覆盖集合、缓存、并发与函数式编程。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CodeForge Studio
agent_created: true
trigger_words: ["Guava", "Java集合操作", "Java缓存", "Java并发工具", "ImmutableList", "LoadingCache", "RateLimiter", "Multimap", "ListenableFuture"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Java 核心库与 Guava 实用指南

## 一、能力边界（一页纸速查卡）

### 能做

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 不可变集合创建 | ImmutableList / ImmutableSet / ImmutableMap 的多种构造方式 |
| 2 | Multimap 操作 | ArrayListMultimap / HashMultimap 的增删查改 |
| 3 | 缓存策略配置 | CacheBuilder 的过期、刷新、最大容量设置 |
| 4 | 限流器使用 | RateLimiter 的 QPS 设定与 acquire/tryAcquire 调用 |
| 5 | 异步回调 | ListenableFuture 的 addCallback 成功/失败处理 |
| 6 | 函数式工具 | Function / Predicate / Optional 的链式用法 |

### 不能做

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不覆盖 Guava 全部 API | 仅聚焦集合、缓存、并发、函数式四大模块 |
| 2 | 不提供分布式缓存方案 | 本指南只涉及本地 JVM 内缓存 |
| 3 | 不讲解复杂锁机制 | 如 Striped 锁、读写锁的高级用法请查阅官方文档 |
| 4 | 不替代官方 Javadoc | 未收录的方法请直接查官方文档 |
| 5 | 不处理版本迁移 | 不同大版本间的 API 差异需自行核对 |

### 适用对象

- 使用 Java 8+ 的后端开发人员
- 项目中已引入 Guava 依赖（或准备引入）
- 需要快速查阅常用 API 写法的场景

---

## 二、触发方式

当你的输入包含以下关键词或意图时，本 Skill 将被激活：

| 用户说（大白话） | 触发词匹配 | 本 Skill 将提供 |
|-----------------|-----------|----------------|
| "怎么创建一个不可变的 List？" | ImmutableList | 创建方式 + 代码示例 |
| "有没有类似 Map<K, List<V>> 的结构？" | Multimap | 使用示例 + 遍历方式 |
| "缓存怎么设置 10 分钟过期？" | CacheBuilder / 过期策略 | 配置参数 + 完整示例 |
| "接口限流怎么做？" | RateLimiter | QPS 设置 + 获取许可代码 |
| "异步任务完成后怎么回调？" | ListenableFuture | addCallback 用法 |
| "Optional 怎么用？" | Optional | 常见用法示例 |

---

## 三、标准流程

### 前置条件

1. **JDK 版本确认**：默认按 JDK 8 语法编写示例。若你的项目使用更高版本，请在提问时说明，否则输出 `[需核实:JDK版本]` 提示。
2. **Guava 版本确认**：默认按 33.x 编写示例。若未指定版本，输出 `[需核实:版本兼容性]` 标注。
3. **依赖确认**：默认假设 Maven/Gradle 已引入 Guava 依赖。若未引入，请先添加：

```xml
<!-- Maven -->
<dependency>
    <groupId>com.google.guava</groupId>
    <artifactId>guava</artifactId>
    <version>33.0.0-jre</version>
</dependency>
```

```gradle
// Gradle
implementation 'com.google.guava:guava:33.0.0-jre'
```

### 执行步骤

#### 场景 A：不可变集合

1. 判断需求类型：不可变集合（Immutable）还是 Multimap。
2. 不可变集合创建方式：

```java
// 方式一：of 方法（适用于少量元素）
ImmutableList<String> list = ImmutableList.of("a", "b", "c");
ImmutableSet<Integer> set = ImmutableSet.of(1, 2, 3);
ImmutableMap<String, Integer> map = ImmutableMap.of("key1", 1, "key2", 2);

// 方式二：builder 构建（适用于动态数据）
ImmutableList<String> listBuilder = ImmutableList.<String>builder()
    .add("a")
    .addAll(Arrays.asList("b", "c"))
    .build();

// 方式三：copyOf 复制（从已有集合转换）
List<String> mutableList = new ArrayList<>();
mutableList.add("x");
ImmutableList<String> immutableList = ImmutableList.copyOf(mutableList);
```

3. Multimap 操作：

```java
// 创建
Multimap<String, Integer> multimap = ArrayListMultimap.create();

// 添加（同一 key 可对应多个 value）
multimap.put("a", 1);
multimap.put("a", 2);
multimap.put("b", 3);

// 查询
Collection<Integer> values = multimap.get("a"); // [1, 2]

// 遍历
for (Map.Entry<String, Integer> entry : multimap.entries()) {
    System.out.println(entry.getKey() + " -> " + entry.getValue());
}

// 删除
multimap.remove("a", 1); // 只移除 key="a" 且 value=1 的条目
multimap.removeAll("b"); // 移除 key="b" 的所有条目
```

4. 将示例代码粘贴到项目中，替换变量名与业务逻辑。

#### 场景 B：缓存配置

1. 判断需要**自动加载**（LoadingCache）还是**手动管理**（Cache）。

2. 自动加载（LoadingCache）：

```java
LoadingCache<String, User> cache = CacheBuilder.newBuilder()
    .maximumSize(1000)                    // 最大条目数
    .expireAfterWrite(10, TimeUnit.MINUTES) // 写入后 10 分钟过期
    .build(new CacheLoader<String, User>() {
        @Override
        public User load(String key) throws Exception {
            return loadUserFromDB(key);   // 缓存未命中时自动加载
        }
    });

// 使用
User user = cache.get("userId-123"); // 命中缓存或自动加载
```

3. 手动管理（Cache）：

```java
Cache<String, User> cache = CacheBuilder.newBuilder()
    .maximumSize(1000)
    .expireAfterAccess(30, TimeUnit.MINUTES) // 30 分钟未访问则过期
    .build();

// 写入
cache.put("userId-123", user);

// 读取
User user = cache.getIfPresent("userId-123"); // 未命中返回 null

// 显式删除
cache.invalidate("userId-123");
```

4. 同时设置写入过期与刷新：

```java
LoadingCache<String, User> cache = CacheBuilder.newBuilder()
    .maximumSize(1000)
    .expireAfterWrite(10, TimeUnit.MINUTES)  // 10 分钟过期
    .refreshAfterWrite(5, TimeUnit.MINUTES)  // 5 分钟后刷新（异步重新加载）
    .build(new CacheLoader<String, User>() {
        @Override
        public User load(String key) throws Exception {
            return loadUserFromDB(key);
        }
    });
```

5. 运行示例，观察缓存命中与过期行为。

#### 场景 C：并发工具

1. 判断是**限流**（RateLimiter）还是**异步回调**（ListenableFuture）。

2. 限流（RateLimiter）：

```java
// 创建：每秒允许 5 个请求
RateLimiter rateLimiter = RateLimiter.create(5.0);

// 阻塞获取许可（最多等待 1 秒）
boolean acquired = rateLimiter.tryAcquire(1, 1, TimeUnit.SECONDS);
if (acquired) {
    // 处理请求
} else {
    // 返回限流提示
}

// 阻塞获取（无超时）
rateLimiter.acquire(); // 会阻塞直到获取许可
```

3. 异步回调（ListenableFuture）：

```java
// 将普通 ExecutorService 包装为 ListeningExecutorService
ListeningExecutorService service = MoreExecutors.listeningDecorator(
    Executors.newFixedThreadPool(4)
);

// 提交异步任务
ListenableFuture<String> future = service.submit(() -> {
    Thread.sleep(2000);
    return "任务结果";
});

// 注册回调
Futures.addCallback(future, new FutureCallback<String>() {
    @Override
    public void onSuccess(String result) {
        System.out.println("成功: " + result);
    }

    @Override
    public void onFailure(Throwable t) {
        System.err.println("失败: " + t.getMessage());
    }
}, service); // 回调在哪个执行器上运行
```

4. 若涉及更复杂的锁或监控，查阅官方文档（本指南不展开）。

#### 场景 D：函数式编程

```java
// Function 转换
Function<String, Integer> lengthFunc = String::length;
int len = lengthFunc.apply("hello"); // 5

// Predicate 过滤
Predicate<String> nonEmpty = s -> !s.isEmpty();
boolean result = nonEmpty.test("abc"); // true

// Optional 判空
Optional<String> optional = Optional.ofNullable(getNullableValue());
String value = optional.orElse("默认值");
boolean present = optional.isPresent();
```

---

## 四、置信度门控

当信息不足时，本 Skill 会输出 `[需核实:字段]` 占位符，绝不编造。常见情况：

| 场景 | 输出占位符 | 用户需补充 |
|------|-----------|-----------|
| 未指定 JDK 版本 | `[需核实:JDK版本]` | JDK 8 / 11 / 17 / 21 |
| 未指定 Guava 版本 | `[需核实:版本兼容性]` | Guava 版本号 |
| 询问未收录的方法 | `[需核实:方法名]` | 方法全名，建议查官方 Javadoc |
| 依赖未确认 | `[需核实:依赖配置]` | pom.xml 或 build.gradle 片段 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| E001 | 不可变集合试图修改 | "ImmutableList 不支持 add/remove 操作" | 改用 ArrayList 或创建时预留可变副本 |
| E002 | 缓存 key 为 null | "CacheBuilder 不允许 null key" | 使用 Optional 包装或过滤 null 值 |
| E003 | RateLimiter 获取许可超时 | "tryAcquire 返回 false，请求被限流" | 增加超时时间或降级处理 |
| E004 | ListenableFuture 回调未执行 | "回调未触发，检查执行器是否关闭" | 确保 service 未 shutdown，或使用 directExecutor() |
| E005 | Multimap 遍历时修改 | "ConcurrentModificationException" | 使用迭代器的 remove 方法或收集后统一删除 |
| E006 | Guava 版本不兼容 | "NoSuchMethodError 或 ClassNotFoundException" | 核对 Guava 版本与 JDK 版本匹配性 |

---

## 六、FAQ 反模式

### 坑 1：过度使用 ImmutableList.of()

**反模式**：元素超过 5 个时仍用 `of()` 方法，代码冗长且易错。

**正确做法**：

```java
// 反模式
ImmutableList<String> list = ImmutableList.of("a", "b", "c", "d", "e", "f");

// 正确做法
ImmutableList<String> list = ImmutableList.<String>builder()
    .add("a", "b", "c", "d", "e", "f")
    .build();
```

### 坑 2：缓存过期时间设置不合理

**反模式**：所有缓存统一设置 10 分钟过期，不考虑业务特性。

**正确做法**：根据数据变更频率分级设置——热点数据 1 分钟，常规数据 10 分钟，静态数据 1 小时。

### 坑 3：RateLimiter 放在方法内部创建

**反模式**：每个请求都 `RateLimiter.create(5.0)`，限流失效。

**正确做法**：将 RateLimiter 定义为类的静态字段或单例。

```java
// 正确做法
public class ApiService {
    private static final RateLimiter limiter = RateLimiter.create(5.0);

    public void handleRequest() {
        if (limiter.tryAcquire()) {
            // 处理
        }
    }
}
```

### 坑 4：忽略 ListenableFuture 的异常处理

**反模式**：只注册 onSuccess 回调，不处理 onFailure，异常被静默吞掉。

**正确做法**：始终同时实现 onSuccess 和 onFailure，至少记录日志。

### 坑 5：Multimap 的 get() 返回视图而非副本

**反模式**：对 `multimap.get(key)` 返回的集合直接 clear()，影响原 Multimap。

**正确做法**：需要独立副本时使用 `new ArrayList<>(multimap.get(key))`。

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
不可变集合 → ImmutableList.of(...) / builder() / copyOf()
Multimap    → ArrayListMultimap.create() → put / get / entries()
缓存        → CacheBuilder.newBuilder().maximumSize().expireAfterWrite().build()
限流        → RateLimiter.create(qps) → tryAcquire() / acquire()
异步回调    → MoreExecutors.listeningDecorator(executor) → Futures.addCallback()
```

### 新手路径（首次使用）

1. 先确认 JDK 与 Guava 版本（见前置条件）。
2. 从「场景 A：不可变集合」开始，掌握创建与遍历。
3. 再学「场景 B：缓存配置」，理解过期策略。
4. 最后接触「场景 C：并发工具」，注意限流与异步的配合。

### 进阶路径（有经验开发者）

1. 直接查阅「场景 C：并发工具」中的 ListenableFuture 与 RateLimiter 组合使用。
2. 关注「FAQ 反模式」中的坑，避免生产环境踩雷。
3. 对于未覆盖的 API，结合「置信度门控」机制，输出占位符后自行查官方文档。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的代码示例和配置建议仅供参考，不构成任何形式的保证。在生产环境使用前，使用者应自行测试验证。

2. **禁止反向工程**：禁止对本 Skill 文档进行反向工程、反编译、破解或试图提取底层逻辑。禁止将本 Skill 用于任何违反法律法规或第三方权益的用途。

3. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

4. **版本变更**：本 Skill 可能随时更新或修改，恕不另行通知。使用者应定期检查最新版本。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 CodeForge Studio

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
