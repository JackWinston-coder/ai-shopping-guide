from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueryProfile:
    raw_query: str
    query_text: str
    category_hint: str | None = None
    sub_category_hints: list[str] = field(default_factory=list)
    hard_terms: list[str] = field(default_factory=list)
    boost_terms: list[str] = field(default_factory=list)
    exclude_terms: list[str] = field(default_factory=list)

    @property
    def has_hard_terms(self) -> bool:
        return bool(self.hard_terms)


DOMAIN_QUERY_RULES: dict[str, dict] = {
    "耳机": {
        "category_hint": "数码电子",
        "sub_category_hints": ["耳机"],
        "hard_terms": ["耳机", "耳塞", "真无线耳机", "头戴式耳机"],
        "boost_terms": ["降噪", "无线", "蓝牙", "通话", "续航"],
    },
    "跑步": {
        "category_hint": "服饰运动",
        "sub_category_hints": ["跑步鞋", "徒步鞋", "篮球鞋", "运动鞋"],
        "hard_terms": ["跑步鞋", "跑鞋", "徒步鞋", "篮球鞋", "运动鞋", "鞋"],
        "boost_terms": ["缓震", "轻量", "透气", "速干", "训练", "运动"],
    },
    "咖啡": {
        "category_hint": "食品饮料",
        "sub_category_hints": ["咖啡"],
        "hard_terms": ["咖啡", "咖啡豆", "速溶咖啡", "挂耳咖啡"],
        "boost_terms": ["提神", "冲泡", "醇香", "风味", "咖啡因"],
    },
    "油皮": {
        "category_hint": "美妆护肤",
        "sub_category_hints": ["面霜", "洁面", "防晒", "精华", "面膜", "化妆水"],
        "hard_terms": [],
        "boost_terms": ["控油", "清爽", "油脂", "毛孔", "轻薄", "不油腻"],
    },
    "面霜": {
        "category_hint": "美妆护肤",
        "sub_category_hints": ["面霜"],
        "hard_terms": ["面霜", "乳霜"],
        "boost_terms": ["保湿", "滋润", "修护", "抗老"],
    },
    "防晒": {
        "category_hint": "美妆护肤",
        "sub_category_hints": ["防晒"],
        "hard_terms": ["防晒", "防晒霜"],
        "boost_terms": ["SPF", "清爽", "不油腻", "紫外线"],
    },
    "洁面": {
        "category_hint": "美妆护肤",
        "sub_category_hints": ["洁面"],
        "hard_terms": ["洁面", "洗面奶", "洁面乳"],
        "boost_terms": ["清洁", "温和", "控油", "泡沫"],
    },
    "精华": {
        "category_hint": "美妆护肤",
        "sub_category_hints": ["精华"],
        "hard_terms": ["精华", "精华液", "精华素"],
        "boost_terms": ["修护", "抗老", "美白", "保湿"],
    },
    "运动鞋": {
        "category_hint": "服饰运动",
        "sub_category_hints": ["跑步鞋", "篮球鞋", "运动鞋"],
        "hard_terms": ["运动鞋", "跑鞋", "篮球鞋"],
        "boost_terms": ["缓震", "支撑", "透气", "轻量"],
    },
    "手机": {
        "category_hint": "数码电子",
        "sub_category_hints": ["手机"],
        "hard_terms": ["手机", "智能手机"],
        "boost_terms": ["拍照", "续航", "屏幕", "性能"],
    },
    "面膜": {
        "category_hint": "美妆护肤",
        "sub_category_hints": ["面膜"],
        "hard_terms": ["面膜", "贴片面膜"],
        "boost_terms": ["补水", "保湿", "修护", "美白"],
    },
    "蛋白粉": {
        "category_hint": "食品饮料",
        "sub_category_hints": ["蛋白粉"],
        "hard_terms": ["蛋白粉", "乳清蛋白"],
        "boost_terms": ["增肌", "蛋白质", "健身", "恢复"],
    },
    "吹风机": {
        "category_hint": "数码电子",
        "sub_category_hints": ["吹风机"],
        "hard_terms": ["吹风机", "电吹风"],
        "boost_terms": ["速干", "负离子", "恒温", "护发"],
    },
}

_MAX_LLM_PROFILE_CACHE = 512
_LLM_PROFILE_CACHE: dict[str, QueryProfile] = {}


def build_query_profile(query: str) -> QueryProfile:
    query_text = query.lower()
    category_hint = None
    sub_category_hints: list[str] = []
    hard_terms: list[str] = []
    boost_terms: list[str] = []

    for keyword, rule in DOMAIN_QUERY_RULES.items():
        if keyword not in query_text:
            continue
        if category_hint is None and rule.get("category_hint"):
            category_hint = rule["category_hint"]
        sub_category_hints.extend(rule.get("sub_category_hints", []))
        hard_terms.extend(term for term in rule.get("hard_terms", []) if term in query_text)
        boost_terms.extend(rule.get("boost_terms", []))

    base_profile = QueryProfile(
        raw_query=query,
        query_text=query_text,
        category_hint=category_hint,
        sub_category_hints=list(dict.fromkeys(sub_category_hints)),
        hard_terms=list(dict.fromkeys(hard_terms)),
        boost_terms=list(dict.fromkeys(boost_terms)),
    )

    if base_profile.category_hint is not None:
        return base_profile

    cached = _LLM_PROFILE_CACHE.get(query)
    if cached is not None:
        return cached

    llm_profile = _llm_build_profile(query)
    if llm_profile is not None:
        if len(_LLM_PROFILE_CACHE) >= _MAX_LLM_PROFILE_CACHE:
            oldest_key = next(iter(_LLM_PROFILE_CACHE))
            del _LLM_PROFILE_CACHE[oldest_key]
        _LLM_PROFILE_CACHE[query] = llm_profile
        return llm_profile

    return base_profile


_LLM_CLIENT = None


def _get_llm_client():
    global _LLM_CLIENT
    if _LLM_CLIENT is None:
        from server.llm.zhipu_client import ZhipuClient
        _LLM_CLIENT = ZhipuClient()
    return _LLM_CLIENT


def _llm_build_profile(query: str) -> QueryProfile | None:
    try:
        client = _get_llm_client()
        if not client.api_key:
            return None

        categories = ["美妆护肤", "数码电子", "食品饮料", "服饰运动"]
        response = client.chat_sync(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是电商搜索意图分析专家。根据用户查询，输出JSON格式的搜索意图分析。\n"
                        "可选品类：" + "、".join(categories) + "\n"
                        "输出格式：{\"category\":\"品类名\",\"boost\":[\"关键词1\",\"关键词2\"],"
                        "\"exclude\":[\"排除词1\"],\"hard\":[\"必须包含词\"]}\n"
                        "只输出JSON，不要解释。"
                    ),
                },
                {"role": "user", "content": query},
            ],
            temperature=0.0,
            max_tokens=120,
        )
        if not response:
            return None

        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        data = json.loads(clean)

        category = data.get("category")
        if category not in categories:
            category = None

        return QueryProfile(
            raw_query=query,
            query_text=query.lower(),
            category_hint=category,
            boost_terms=data.get("boost", [])[:5],
            exclude_terms=data.get("exclude", [])[:3],
            hard_terms=data.get("hard", [])[:3],
        )
    except Exception as e:
        logger.debug("LLM query profile skipped: %s", e)
        return None
