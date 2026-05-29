# AI Shopping Guide

基于 RAG 的多模态电商智能导购 Web 项目。

## 项目目标

构建一个网页端 AI 电商导购 Demo，支持文本、图片、语音输入，通过 RAG 检索商品知识库，生成可靠导购回复，并完成商品卡片展示、购物车管理和模拟下单闭环。

## 目录结构

```text
client/      Next.js + React 前端
server/      后端 API、RAG、模型调用、爬虫
data/        商品 JSON、图片、向量库导入源
docs/        需求、架构、API、设计规范、测试与部署文档
devlogs/     每日开发日志
scripts/     初始化、数据导入、日志生成等脚本
docker/      Docker 与部署配置
```

## 每日开发流程

1. 运行 `scripts/new-devlog.ps1` 创建当天开发日志。
2. 从日志中的“明日待办”选择 1-3 个今日目标。
3. 完成开发后更新“已完成、遇到的问题、风险与决策、明日待办”。
4. 关键决策同步到 `docs/`。
5. 每个阶段结束后做一次可运行验证。

## 当前阶段

Milestone 6：前后端联调 + 多模态。
