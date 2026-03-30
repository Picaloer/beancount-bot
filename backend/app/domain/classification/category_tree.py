"""
Two-level category taxonomy.
L1 → L2 mapping used by rule engine, LLM prompts, and frontend display.
"""

CATEGORY_TREE: dict[str, list[str]] = {
    "餐饮": ["外卖", "堂食", "咖啡", "奶茶", "快餐", "正餐", "零食"],
    "购物": ["服装", "数码", "日用品", "超市", "网购", "美妆", "家居"],
    "娱乐": ["游戏", "电影", "音乐", "视频会员", "KTV", "演出", "体育"],
    "交通": ["打车", "公交地铁", "加油", "高铁机票", "共享单车", "停车"],
    "住房": ["房租", "水电", "物业", "家政", "装修", "家具家电"],
    "医疗健康": ["医院", "药店", "健身", "保险", "体检"],
    "教育": ["在线课程", "书籍", "考试", "培训", "文具"],
    "转账": ["家人", "朋友", "还款", "收款"],
    "其他": ["未分类"],
}

# Flat list of all L1 categories
L1_CATEGORIES: list[str] = list(CATEGORY_TREE.keys())

# Flat list of all L2 sub-categories
L2_CATEGORIES: list[str] = [sub for subs in CATEGORY_TREE.values() for sub in subs]


def get_l2_options(category_l1: str) -> list[str]:
    return CATEGORY_TREE.get(category_l1, ["未分类"])


def is_valid_l1(cat: str) -> bool:
    return cat in CATEGORY_TREE


def category_tree_for_prompt() -> str:
    """Compact representation for LLM system prompts."""
    lines = []
    for l1, l2_list in CATEGORY_TREE.items():
        lines.append(f"  {l1}: {', '.join(l2_list)}")
    return "\n".join(lines)
