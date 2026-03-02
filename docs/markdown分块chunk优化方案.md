当前markdown分块有一些问题，比如有如下文档

```markdown
# Java 学习指南

Java 语言概述

## 语法

blabla

### method

method description ...

### class

how to define a class
```

如上这个文章在被chunk后，“how to define a class” 很可能和最开始的 " # Java 学习指南" 就不在一个chunk了，这会导致当问 "如何在java里定义一个class" 时，检索不到标题中的java。

## 问题原因

由于title可能和content不在一个chunk，导致上下文确实

## 解决方案

在分chunk时，叠加标题，比如上面的文章，应生成如下的chunk，也就是把从一级标题一直到当前内容的标题都生成进去

```markdown
# Java 学习指南

## 语法

### class

how to define a class
```
