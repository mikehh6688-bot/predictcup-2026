"""2026 世界盃靜態資料 —— 英文隊名對照、維基組別頁面清單。

seed_worldcup.py 與 wiki_provider.py 共用，避免重複維護。
"""

# 英文隊名 -> (繁中顯示名, 國旗碼)。ENG/SCT 用次國家旗，其餘為 ISO2。
TEAM = {
    "Mexico": ("墨西哥", "MX"), "South Africa": ("南非", "ZA"),
    "South Korea": ("南韓", "KR"), "Czech Republic": ("捷克", "CZ"),
    "Canada": ("加拿大", "CA"), "Bosnia and Herzegovina": ("波士尼亞", "BA"),
    "Qatar": ("卡達", "QA"), "Switzerland": ("瑞士", "CH"),
    "Brazil": ("巴西", "BR"), "Morocco": ("摩洛哥", "MA"),
    "Haiti": ("海地", "HT"), "Scotland": ("蘇格蘭", "SCT"),
    "United States": ("美國", "US"), "Paraguay": ("巴拉圭", "PY"),
    "Australia": ("澳洲", "AU"), "Turkey": ("土耳其", "TR"),
    "Germany": ("德國", "DE"), "Curaçao": ("古拉索", "CW"),
    "Ivory Coast": ("象牙海岸", "CI"), "Ecuador": ("厄瓜多", "EC"),
    "Netherlands": ("荷蘭", "NL"), "Japan": ("日本", "JP"),
    "Sweden": ("瑞典", "SE"), "Tunisia": ("突尼西亞", "TN"),
    "Belgium": ("比利時", "BE"), "Egypt": ("埃及", "EG"),
    "Iran": ("伊朗", "IR"), "New Zealand": ("紐西蘭", "NZ"),
    "Spain": ("西班牙", "ES"), "Cape Verde": ("維德角", "CV"),
    "Saudi Arabia": ("沙烏地阿拉伯", "SA"), "Uruguay": ("烏拉圭", "UY"),
    "France": ("法國", "FR"), "Senegal": ("塞內加爾", "SN"),
    "Iraq": ("伊拉克", "IQ"), "Norway": ("挪威", "NO"),
    "Argentina": ("阿根廷", "AR"), "Algeria": ("阿爾及利亞", "DZ"),
    "Austria": ("奧地利", "AT"), "Jordan": ("約旦", "JO"),
    "Portugal": ("葡萄牙", "PT"), "DR Congo": ("剛果民主共和國", "CD"),
    "Uzbekistan": ("烏茲別克", "UZ"), "Colombia": ("哥倫比亞", "CO"),
    "England": ("英格蘭", "ENG"), "Croatia": ("克羅埃西亞", "HR"),
    "Ghana": ("迦納", "GH"), "Panama": ("巴拿馬", "PA"),
}

# 維基百科組別頁面（賽果同步用）
WIKI_GROUP_PAGES = [f"2026 FIFA World Cup Group {g}" for g in "ABCDEFGHIJKL"]


def zh_name(english):
    """英文隊名 -> 繁中顯示名（未知則回原文）。"""
    entry = TEAM.get(english)
    return entry[0] if entry else english
