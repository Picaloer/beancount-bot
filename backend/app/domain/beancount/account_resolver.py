"""
Maps transaction fields to Beancount account names.

Account structure (following Beancount conventions):
  Assets:WeChat            微信零钱
  Assets:Alipay            支付宝余额
  Expenses:Food:Delivery   餐饮/外卖
  Income:Salary            收入/工资
"""
from app.domain.transaction.models import BillSource, TransactionDirection

# Expense account mapping: (category_l1, category_l2) → account
EXPENSE_ACCOUNTS: dict[tuple[str, str | None], str] = {
    ("餐饮", "外卖"):   "Expenses:Food:Delivery",
    ("餐饮", "堂食"):   "Expenses:Food:DineIn",
    ("餐饮", "咖啡"):   "Expenses:Food:Coffee",
    ("餐饮", "奶茶"):   "Expenses:Food:MilkTea",
    ("餐饮", "快餐"):   "Expenses:Food:FastFood",
    ("餐饮", "正餐"):   "Expenses:Food:DineIn",
    ("餐饮", "零食"):   "Expenses:Food:Snacks",
    ("购物", "服装"):   "Expenses:Shopping:Clothing",
    ("购物", "数码"):   "Expenses:Shopping:Electronics",
    ("购物", "日用品"): "Expenses:Shopping:Daily",
    ("购物", "超市"):   "Expenses:Shopping:Grocery",
    ("购物", "网购"):   "Expenses:Shopping:Online",
    ("购物", "美妆"):   "Expenses:Shopping:Beauty",
    ("购物", "家居"):   "Expenses:Shopping:HomeGoods",
    ("娱乐", "游戏"):   "Expenses:Entertainment:Game",
    ("娱乐", "电影"):   "Expenses:Entertainment:Movie",
    ("娱乐", "音乐"):   "Expenses:Entertainment:Music",
    ("娱乐", "视频会员"): "Expenses:Entertainment:Streaming",
    ("娱乐", "KTV"):    "Expenses:Entertainment:KTV",
    ("交通", "打车"):   "Expenses:Transport:Taxi",
    ("交通", "公交地铁"): "Expenses:Transport:PublicTransit",
    ("交通", "加油"):   "Expenses:Transport:Fuel",
    ("交通", "高铁机票"): "Expenses:Transport:Travel",
    ("交通", "共享单车"): "Expenses:Transport:Bike",
    ("住房", "房租"):   "Expenses:Housing:Rent",
    ("住房", "水电"):   "Expenses:Housing:Utilities",
    ("住房", "物业"):   "Expenses:Housing:Management",
    ("医疗健康", "医院"):  "Expenses:Health:Hospital",
    ("医疗健康", "药店"):  "Expenses:Health:Pharmacy",
    ("医疗健康", "健身"):  "Expenses:Health:Fitness",
    ("医疗健康", "保险"):  "Expenses:Health:Insurance",
    ("教育", "在线课程"):  "Expenses:Education:Online",
    ("教育", "书籍"):    "Expenses:Education:Books",
    ("教育", "培训"):    "Expenses:Education:Training",
    ("转账", None):     "Expenses:Transfer",
    ("其他", None):     "Expenses:Other",
}

# Asset account for each bill source
SOURCE_ACCOUNTS: dict[BillSource, str] = {
    BillSource.WECHAT: "Assets:WeChat",
    BillSource.ALIPAY: "Assets:Alipay",
    BillSource.CMB: "Assets:Bank:CMB",
}

INCOME_ACCOUNT = "Income:Other"
TRANSFER_ACCOUNT = "Assets:Transfer"


def resolve_expense_account(category_l1: str, category_l2: str | None) -> str:
    key = (category_l1, category_l2)
    if key in EXPENSE_ACCOUNTS:
        return EXPENSE_ACCOUNTS[key]
    # Try L1 only
    l1_key = (category_l1, None)
    if l1_key in EXPENSE_ACCOUNTS:
        return EXPENSE_ACCOUNTS[l1_key]
    return "Expenses:Other"


def resolve_asset_account(source: BillSource) -> str:
    return SOURCE_ACCOUNTS.get(source, "Assets:Unknown")
