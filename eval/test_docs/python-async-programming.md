# Python 异步编程指南

## 概述

Python 的异步编程通过 `asyncio` 模块实现，允许编写并发代码而无需多线程。

## 核心概念

### async/await 语法

```python
import asyncio

async def fetch_data():
    await asyncio.sleep(1)
    return {"data": "example"}

async def main():
    result = await fetch_data()
    print(result)

asyncio.run(main())
```

### 协程与任务

协程是异步编程的基本单元，通过 `async def` 定义。任务是调度协程执行的方式。

```python
async def task1():
    await asyncio.sleep(1)
    print("Task 1 done")

async def task2():
    await asyncio.sleep(0.5)
    print("Task 2 done")

async def main():
    await asyncio.gather(task1(), task2())
```

## 最佳实践

1. 使用 `asyncio.gather()` 并发执行多个协程
2. 避免在协程中执行阻塞操作
3. 使用 `asyncio.to_thread()` 将阻塞代码放到线程池
4. 合理设置超时时间，避免协程永久阻塞
