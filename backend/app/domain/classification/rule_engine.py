"""
Keyword-based rule engine for transaction classification.
Rules can match merchant, description, or both fields.
"""
from dataclasses import dataclass
from typing import Literal

from app.domain.transaction.models import RawTransaction


MatchField = Literal["merchant", "description", "any"]


@dataclass
class Rule:
    keywords: list[str]  # case-insensitive substring match
    category_l1: str
    category_l2: str | None
    priority: int = 0
    match_field: MatchField = "any"


# Built-in system rules covering high-frequency merchants
SYSTEM_RULES: list[Rule] = [
    # 餐饮 - 外卖
    Rule(["美团", "饿了么", "eleme", "meituan"], "餐饮", "外卖", 10),
    # 餐饮 - 咖啡
    Rule(["星巴克", "starbucks", "瑞幸", "luckin", "manner", "m stand", "tims"], "餐饮", "咖啡", 10),
    # 餐饮 - 奶茶
    Rule(["喜茶", "奈雪", "茶颜悦色", "蜜雪冰城", "古茗", "书亦", "沪上阿姨", "霸王茶姬"], "餐饮", "奶茶", 10),
    # 餐饮 - 快餐
    Rule(["麦当劳", "肯德基", "kfc", "burger king", "汉堡王", "必胜客", "pizza hut", "subway", "塔斯汀"], "餐饮", "快餐", 10),
    # 购物 - 超市
    Rule(["沃尔玛", "家乐福", "大润发", "盒马", "山姆", "永辉", "华润万家", "物美"], "购物", "超市", 10),
    # 购物 - 网购
    Rule(["淘宝", "天猫", "京东", "拼多多", "抖音小店", "快手小店"], "购物", "网购", 10),
    # 购物 - 数码
    Rule(["苹果", "apple store", "小米", "华为商城", "三星"], "购物", "数码", 10),
    # 娱乐 - 视频会员
    Rule(["爱奇艺", "优酷", "腾讯视频", "bilibili", "b站", "芒果tv", "netflix"], "娱乐", "视频会员", 10),
    # 娱乐 - 游戏
    Rule(["steam", "epic", "腾讯游戏", "网易游戏", "米哈游", "游戏充值"], "娱乐", "游戏", 10),
    # 娱乐 - 音乐
    Rule(["网易云音乐", "qq音乐", "spotify", "酷狗", "酷我"], "娱乐", "音乐", 10),
    # 交通 - 打车
    Rule(["滴滴", "高德打车", "曹操出行", "享道出行", "如祺出行", "uber"], "交通", "打车", 10),
    # 交通 - 公交地铁
    Rule(["地铁", "公交", "metro", "transit"], "交通", "公交地铁", 10),
    # 交通 - 高铁机票
    Rule(["12306", "携程", "飞猪", "去哪儿", "高铁", "动车", "火车票", "机票", "航空"], "交通", "高铁机票", 10),
    # 交通 - 共享单车
    Rule(["哈啰", "美团单车", "青桔", "小蓝车"], "交通", "共享单车", 10),
    # 医疗健康 - 健身
    Rule(["keep", "超级猩猩", "乐刻", "健身"], "医疗健康", "健身", 10),
    # 医疗健康 - 药店
    Rule(["大参林", "益丰", "老百姓药店", "华润医药", "药房", "药店"], "医疗健康", "药店", 10),
    # 教育 - 在线课程
    Rule(["得到", "极客时间", "慕课", "coursera", "udemy", "知乎课堂"], "教育", "在线课程", 10),
    # 住房
    Rule(["物业", "水费", "电费", "燃气", "供暖"], "住房", "水电", 10),
]


class RuleEngine:
    def __init__(self, rules: list[Rule] | None = None) -> None:
        self._rules: list[Rule] = sorted(
            rules or [],
            key=lambda rule: rule.priority,
            reverse=True,
        )

    def classify(self, tx: RawTransaction) -> tuple[str, str | None] | None:
        """Returns (category_l1, category_l2) or None if no rule matches."""
        for rule in self._rules:
            text = self._text_for_rule(tx, rule.match_field)
            if any(keyword.lower() in text for keyword in rule.keywords):
                return rule.category_l1, rule.category_l2
        return None

    def _text_for_rule(self, tx: RawTransaction, match_field: MatchField) -> str:
        if match_field == "merchant":
            return tx.merchant.lower()
        if match_field == "description":
            return tx.description.lower()
        return f"{tx.merchant} {tx.description}".lower()
