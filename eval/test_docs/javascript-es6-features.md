# JavaScript ES6+ 新特性详解

## let 和 const

ES6 引入了块级作用域变量声明方式。

```javascript
// const 用于常量，不能重新赋值
const PI = 3.14159;

// let 用于可变变量
let count = 0;
count = 1; // 合法
```

## 箭头函数

箭头函数提供更简洁的函数语法，并且不绑定自己的 this。

```javascript
// 传统函数
function add(a, b) {
  return a + b;
}

// 箭头函数
const add = (a, b) => a + b;

// 带函数体
const greet = (name) => {
  const message = `Hello, ${name}!`;
  return message;
};
```

## 解构赋值

从数组或对象中提取值，赋给变量。

```javascript
// 数组解构
const [first, second] = [1, 2, 3];

// 对象解构
const { name, age } = { name: "Alice", age: 30 };

// 函数参数解构
function printUser({ name, age }) {
  console.log(`${name} is ${age} years old`);
}
```

## 模板字符串

使用反引号创建带插值的字符串。

```javascript
const name = "World";
const message = `Hello, ${name}!`;
```

## Promise 和 async/await

处理异步操作。

```javascript
// Promise
fetch('/api/data')
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error(error));

// async/await
async function fetchData() {
  try {
    const response = await fetch('/api/data');
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(error);
  }
}
```

## 模块导出导入

```javascript
// math.js
export const add = (a, b) => a + b;
export const subtract = (a, b) => a - b;
export default multiply;

// main.js
import multiply, { add, subtract } from './math.js';
```
