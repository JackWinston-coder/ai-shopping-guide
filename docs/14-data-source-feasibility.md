# 数据源说明

## 目标

说明项目商品数据的来源、结构和维护方式。

## 数据来源

项目商品数据为项目内提供的结构化数据集，存放在 `data/` 目录下，不依赖外部爬虫或第三方 API。

## 目录结构

```text
data/
├── 1_美妆护肤/
│   ├── data/                    # 该类目下的商品 JSON
│   │   ├── p_beauty_001.json
│   │   ├── p_beauty_002.json
│   │   └── ...
│   └── images/                  # 该类目下的商品图片
│       ├── p_beauty_001_live.jpg
│       ├── p_beauty_002_live.jpg
│       └── ...
├── 2_数码电子/
│   ├── data/
│   └── images/
├── 3_服饰运动/
│   ├── data/
│   └── images/
└── 4_食品饮料/
    ├── data/
    └── images/
```

## 类目与商品

| 类目目录 | 一级类目 | 二级类目示例 |
|---------|---------|------------|
| 1_美妆护肤 | 美妆护肤 | 精华、面霜、洁面、防晒、面膜等 |
| 2_数码电子 | 数码电子 | 智能手机、平板电脑、耳机、智能手表等 |
| 3_服饰运动 | 服饰运动 | 短袖T恤、运动鞋、冲锋衣、瑜伽裤等 |
| 4_食品饮料 | 食品饮料 | 坚果零食、咖啡、功能饮料、方便食品等 |

## 数据格式

每个商品 JSON 包含以下字段：

- `product_id`: 商品唯一 ID
- `title`: 商品标题
- `brand`: 品牌名
- `category`: 一级类目
- `sub_category`: 二级类目
- `base_price`: 商品基础价格
- `image_path`: 商品主图相对路径
- `skus`: SKU 列表（含 sku_id、properties、price）
- `rag_knowledge`: 商品知识库内容（含 marketing_description、official_faq、user_reviews）

详细 Schema 定义见 [13-product-schema.md](./13-product-schema.md)。

## 数据维护

- 使用 `scripts/validate-products.js` 校验数据完整性和一致性
- 新增商品数据时需确保 JSON 结构与现有数据一致
- 图片文件需与 JSON 中的 `image_path` 严格对应

## 验收标准

- 4 个类目目录均存在且包含商品数据
- 商品图片文件存在且路径可对上
- JSON 可被脚本正常读取
- `node scripts/validate-products.js` 校验通过
