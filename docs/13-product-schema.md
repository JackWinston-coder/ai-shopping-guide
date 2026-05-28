# 商品数据 Schema

## 目标

统一定义 `data/data/**` 下的商品 JSON 结构，保证后续采集、导入、RAG 切块和检索都使用同一套字段。

## 目录约定

- `data/{类目序号}_{类目名}/data/`：存放该类目下的商品 JSON
- `data/{类目序号}_{类目名}/images/`：存放该类目下的商品图片
- 类目目录命名规范：`1_美妆护肤`、`2_数码电子`、`3_服饰运动`、`4_食品饮料`
- 每个商品 JSON 与主图一一对应，建议文件名保持同一个 `product_id` 前缀
- 示例：`data/1_美妆护肤/data/p_beauty_001.json`，图片：`data/1_美妆护肤/images/p_beauty_001_live.jpg`

## 顶层字段

- `product_id`: 商品唯一 ID，建议使用稳定字符串，如 `p_beauty_001`
- `title`: 商品标题
- `brand`: 品牌名
- `category`: 一级类目
- `sub_category`: 二级类目
- `base_price`: 商品基础价格，数值类型
- `image_path`: 商品主图相对路径，相对于项目 `data/` 目录，例如 `1_美妆护肤/images/p_beauty_001_live.jpg`
- `skus`: SKU 列表
- `rag_knowledge`: 商品知识库内容

## SKU 字段

每个 SKU 需要包含：

- `sku_id`: SKU 唯一 ID
- `properties`: 规格属性对象，例如容量、颜色、尺寸
- `price`: SKU 价格

## RAG 字段

`rag_knowledge` 下建议包含：

- `marketing_description`: 商品导购型介绍
- `official_faq`: 官方问答数组
- `user_reviews`: 用户评价数组

## 采集规则

- 商品图片路径与 JSON 中的 `image_path` 必须严格一致，且以项目 `data/` 目录为基准
- `base_price` 应与最常见或基础 SKU 价格一致
- `official_faq` 和 `user_reviews` 用于后续 RAG 检索，不应留空
- 同一类目下所有商品 JSON 结构保持一致
- 数据来源为项目内已提供的结构化数据集，不依赖外部爬虫

## 本阶段验收

- 4 个类目目录均存在且包含商品数据
- 商品图片文件存在且路径可对上
- JSON 可被脚本正常读取
- `node scripts/validate-products.js` 校验通过
