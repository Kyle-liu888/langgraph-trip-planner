"""Reject clearly over-broad inputs for the existing single-city planner."""

PROVINCES = set("河北 山西 辽宁 吉林 黑龙江 江苏 浙江 安徽 福建 江西 山东 河南 湖北 湖南 广东 海南 四川 贵州 云南 陕西 甘肃 青海 台湾 内蒙古 广西 西藏 宁夏 新疆".split())
SUFFIXES = ("壮族自治区", "回族自治区", "维吾尔自治区", "自治区", "省")


def city_input_error(value: str) -> str | None:
    city = value.strip()
    if not city:
        return "请输入目的地城市"
    for suffix in SUFFIXES:
        if city.endswith(suffix):
            city = city[:-len(suffix)]
            break
    if city in PROVINCES:
        return "当前支持单个城市的行程，请填写具体城市（如昆明、丽江），不要只填写省份或自治区"
    return None
