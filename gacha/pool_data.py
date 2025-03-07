
from PIL import Image,ImageFont,ImageDraw,ImageMath
from loguru import logger
from io import BytesIO

import collections
import httpx
import asyncio
import re
import os
import json



FILE_PATH = os.path.dirname(__file__)
ICON_PATH = os.path.join(FILE_PATH,'icon')


POOL_API =   "https://webstatic.mihoyo.com/hk4e/gacha_info/cn_gf01/gacha/list.json"
ROLES_API = ['https://genshin.honeyhunterworld.com/db/char/characters/?lang=CHS',
             'https://genshin.honeyhunterworld.com/db/char/unreleased-and-upcoming-characters/?lang=CHS']
ARMS_API =  ['https://genshin.honeyhunterworld.com/db/weapon/sword/?lang=CHS',
             'https://genshin.honeyhunterworld.com/db/weapon/claymore/?lang=CHS',
             'https://genshin.honeyhunterworld.com/db/weapon/polearm/?lang=CHS',
             'https://genshin.honeyhunterworld.com/db/weapon/bow/?lang=CHS',
             'https://genshin.honeyhunterworld.com/db/weapon/catalyst/?lang=CHS']
ROLES_HTML_LIST = None
ARMS_HTML_LIST = None

FONT_PATH = os.path.join(os.path.dirname(FILE_PATH),'artifact_collect',"zh-cn.ttf")
FONT=ImageFont.truetype(FONT_PATH, size=20)


POOL_PROBABILITY = {
    # 所有卡池的4星和5星概率,这里直接填写官方给出的概率，程序会自动对4星概率进行累计
    "角色up池": {"5": 0.006, "4": 0.051},
    "武器up池": {"5": 0.007, "4": 0.060},
    "常驻池": {"5": 0.006, "4": 0.051}
}

UP_PROBABILITY = {
    # 这里保存的是当UP池第一次抽取到或上次已经抽取过UP时，本次出现UP的概率有多大，常驻池不受影响
    "角色up池": 0.5,
    "武器up池": 0.75
}

# 这个字典记录的是3个不同的卡池，每个卡池的抽取列表
POOL = collections.defaultdict(
    lambda: {
        '5_star_UP': [],
        '5_star_not_UP': [],
        '4_star_UP': [],
        '4_star_not_UP': [],
        '3_star_not_UP': []
    })

DISTANCE_FREQUENCY = {
    # 3个池子的5星是多少发才保底
    '角色up池': 90,
    '武器up池': 80,
    '常驻池': 90
}



async def get_url_data(url):
    # 获取url的数据
    async with httpx.AsyncClient() as client:
        resp = await client.get(url=url)
        if resp.status_code != 200:
            raise ValueError(f"从 {url} 获取数据失败，错误代码 {resp.status_code}")
        return resp.content



async def get_role_en_name(ch_name):
    # 从 genshin.honeyhunterworld.com 获取角色的英文名
    global ROLES_HTML_LIST
    if ROLES_HTML_LIST == None:
        ROLES_HTML_LIST = []
        for api in ROLES_API:
            data = await get_url_data(api)
            ROLES_HTML_LIST.append(data.decode("utf-8"))

    pattern = ".{80}" + str(ch_name)
    for html in ROLES_HTML_LIST:
        txt = re.search(pattern, html)
        if txt == None:
            continue
        txt = re.search('"/db/char/.+/\?lang=CHS"',txt.group()).group()
        en_name = txt[10:-11]
        return en_name
    raise NameError(f"没有找到角色 {ch_name} 的图标名")



async def get_arm_id(ch_name):
    # 从 genshin.honeyhunterworld.com 获取武器的ID
    global ARMS_HTML_LIST
    if ARMS_HTML_LIST == None:
        ARMS_HTML_LIST = []
        for api in ARMS_API:
            data = await get_url_data(api)
            ARMS_HTML_LIST.append(data.decode("utf-8"))

    pattern = '.{40}' + str(ch_name)
    for html in ARMS_HTML_LIST:
        txt = re.search(pattern, html)
        if txt == None:
            continue
        txt = re.search('weapon/.+?/\?lang', txt.group()).group()
        arm_id = txt[7:-6]
        return arm_id
    raise NameError(f"没有找到武器 {ch_name} 的 ID")


async def get_icon(url):
    # 获取角色或武器的图标，直接返回 Image
    icon = await get_url_data(url)
    icon = Image.open(BytesIO(icon))
    icon_a = icon.getchannel("A")
    icon_a = ImageMath.eval("convert(a*b/256, 'L')", a=icon_a, b=icon_a)
    icon.putalpha(icon_a)
    return icon




async def get_role_element(en_name):
    # 获取角色属性，直接返回属性图标 Image
    url = f'https://genshin.honeyhunterworld.com/db/char/{en_name}/?lang=CHS'
    data = await get_url_data(url)
    data = data.decode("utf-8")
    element = re.search('/img/icons/element/.+?_35.png',data).group()
    element = element[19:-7]

    element_path = os.path.join(FILE_PATH,'icon',f'{element}.png')
    return Image.open(element_path)



async def paste_role_icon(ch_name,star):
    # 拼接角色图鉴图

    en_name = await get_role_en_name(ch_name)
    url = f"https://genshin.honeyhunterworld.com/img/char/{en_name}_face.png"
    avatar_icon = await get_icon(url)
    element_icon = await get_role_element(en_name)

    bg = Image.open(os.path.join(FILE_PATH,'icon',f'{star}_star_bg.png'))
    bg_a = bg.getchannel("A")
    bg1 = Image.new("RGBA",bg.size)
    txt_bg = Image.new("RGBA",(160,35),"#e9e5dc")
    x = int(160/256 * avatar_icon.size[0])
    avatar_icon = avatar_icon.resize((x, 160))
    element_icon = element_icon.resize((40, 40))
    x_pos = int(160/2 - x / 2)
    bg.paste(avatar_icon, (x_pos,3),avatar_icon)
    bg.paste(element_icon, (2,3),element_icon)
    bg.paste(txt_bg, (0,163))
    draw = ImageDraw.Draw(bg)
    draw.text((80, 180), ch_name, fill="#4a5466ff", font=FONT, anchor="mm",align="center")
    bg1.paste(bg,(0,0),bg_a)
    return bg1



async def paste_arm_icon(ch_name,star):
    # 拼接武器图鉴图
    arm_id = await get_arm_id(ch_name)
    url = f'https://genshin.honeyhunterworld.com/img/weapon/{arm_id}_a.png'
    arm_icon = await get_icon(url)
    star_icon = Image.open(os.path.join(FILE_PATH,'icon',f'{star}_star.png'))

    bg = Image.open(os.path.join(FILE_PATH,'icon',f'{star}_star_bg.png'))
    bg_a = bg.getchannel("A")
    bg1 = Image.new("RGBA",bg.size)
    txt_bg = Image.new("RGBA",(160,35),"#e9e5dc")
    arm_icon = arm_icon.resize((130, 160))
    bg.paste(arm_icon, (17,3),arm_icon)
    bg.paste(txt_bg, (0,163))
    draw = ImageDraw.Draw(bg)
    draw.text((80, 180), ch_name, fill="#4a5466ff", font=FONT, anchor="mm",align="center")
    bg.paste(star_icon,(6,135),star_icon)
    bg1.paste(bg,(0,0),bg_a)
    return bg1




async def up_role_icon(name, star):
    # 更新角色图标
    role_name_path = os.path.join(ICON_PATH, "角色图鉴", str(name) + ".png")
    if os.path.exists(role_name_path):
        return
    logger.info(f"正在更新 {name} 角色图标")
    if not os.path.exists(os.path.join(ICON_PATH, '角色图鉴')):
        os.makedirs(os.path.join(ICON_PATH, '角色图鉴'))

    role_icon = await paste_role_icon(name,star)
    with open(role_name_path , "wb") as icon_file:
        role_icon.save(icon_file)




async def up_arm_icon(name, star):
    # 更新武器图标
    arm_name_path = os.path.join(ICON_PATH, "武器图鉴", str(name) + ".png")
    if os.path.exists(arm_name_path):
        return
    logger.info(f"正在更新 {name} 武器图标")
    if not os.path.exists(os.path.join(ICON_PATH, '武器图鉴')):
        os.makedirs(os.path.join(ICON_PATH, '武器图鉴'))

    arm_icon = await paste_arm_icon(name,star)
    with open(arm_name_path , "wb") as icon_file:
        arm_icon.save(icon_file)



async def init_pool_list():
    # 初始化卡池数据
    global ROLES_HTML_LIST
    global ARMS_HTML_LIST

    ROLES_HTML_LIST = None
    ARMS_HTML_LIST = None

    # fix: #61
    POOL.clear()
    
    logger.info(f"正在更新卡池数据")
    data = await get_url_data(POOL_API)
    data = json.loads(data.decode("utf-8"))
    for d in data["data"]["list"]:
        if d['gacha_name'] == "角色":
            pool_name = '角色up池'
        elif d['gacha_name'] == "武器":
            pool_name = '武器up池'
        else:
            pool_name = '常驻池'

        pool_url = f"https://webstatic.mihoyo.com/hk4e/gacha_info/cn_gf01/{d['gacha_id']}/zh-cn.json"
        pool_data = await get_url_data(pool_url)
        pool_data = json.loads(pool_data.decode("utf-8"))

        for prob_list in ['r3_prob_list','r4_prob_list','r5_prob_list']:
            for i in pool_data[prob_list]:
                item_name = i['item_name']
                item_type = i["item_type"]
                item_star = str(i["rank"])
                key = ''
                key += item_star
                if str(i["is_up"]) == "1":
                    key += "_star_UP"
                else:
                    key += "_star_not_UP"
                POOL[pool_name][key].append(item_name)

                if item_type == '角色':
                    await up_role_icon(name = item_name,star = item_star)
                else:
                    await up_arm_icon(name = item_name,star = item_star)




# 初始化
loop = asyncio.get_event_loop()
loop.run_until_complete(init_pool_list())
