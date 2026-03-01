# 设计模式读书笔记

## 什么是设计模式

设计模式是软件设计中常见问题的可复用解决方案。它们不是具体的代码，而是解决问题的思路和经验总结。

## 创建型模式

### 单例模式

确保一个类只有一个实例，并提供全局访问点。

```python
class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### 工厂模式

定义创建对象的接口，让子类决定实例化哪个类。

```python
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        return "Woof!"

class Cat(Animal):
    def speak(self):
        return "Meow!"

class AnimalFactory:
    def create_animal(self, animal_type):
        if animal_type == "dog":
            return Dog()
        elif animal_type == "cat":
            return Cat()
        raise ValueError("Unknown animal type")
```

## 结构型模式

### 适配器模式

将一个类的接口转换成客户期望的另一个接口。

### 装饰器模式

动态地给对象添加额外的职责。

```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before")
        result = func(*args, **kwargs)
        print("After")
        return result
    return wrapper

@my_decorator
def say_hello():
    print("Hello!")
```

### 代理模式

为另一个对象提供一个替身或占位符。

## 行为型模式

### 观察者模式

定义对象间的一对多依赖关系，当一个对象状态改变时，所有依赖它的对象都会收到通知。

```python
class Subject:
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        self._observers.append(observer)

    def detach(self, observer):
        self._observers.remove(observer)

    def notify(self):
        for observer in self._observers:
            observer.update(self)
```

### 策略模式

定义一系列算法，把它们一个个封装起来，并使它们可以相互替换。

## 何时使用设计模式

1. 代码重复出现相似结构时
2. 需要灵活扩展功能时
3. 追求代码可维护性和可读性时

## 注意事项

避免过度使用设计模式，导致代码过度复杂。设计模式是工具，不是银弹。
