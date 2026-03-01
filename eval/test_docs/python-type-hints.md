# Python 类型提示完全指南

## 为什么使用类型提示

类型提示（Type Hints）从 Python 3.5 引入，可以提高代码可读性和可维护性。

## 基础类型

```python
name: str = "Alice"
age: int = 30
price: float = 19.99
is_active: bool = True
```

## 容器类型

```python
from typing import List, Dict, Set, Tuple

numbers: List[int] = [1, 2, 3]
scores: Dict[str, int] = {"Alice": 90, "Bob": 85}
unique_items: Set[int] = {1, 2, 3}
coordinates: Tuple[int, int] = (10, 20)
```

## 高级类型

### Optional 和 Union

```python
from typing import Optional, Union

def find_user(user_id: int) -> Optional[dict]:
    # 可能返回 None
    pass

def process(value: Union[str, int]) -> str:
    # 处理多种类型
    return str(value)
```

### TypeVar 和泛型

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: List[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()
```

## 运行时类型检查

使用 `pydantic` 或 `dataclasses` 进行运行时验证：

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int
    email: str
```

## 工具支持

- mypy: 静态类型检查器
- pyright: 微软开发的类型检查器
- pytype: Google 开发的类型检查器
