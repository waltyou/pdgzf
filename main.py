from datetime import datetime, timedelta
import json
import requests
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import io
import time
import os

s = requests.Session()

def loop_url_for_data(url, page_count=1, project_id=None, token=""):
    header = {
        "gzfauthentication": token
    }
    for page_index in range(page_count):
        print("获取数据中...." + url)
        body = {
            "pageIndex": page_index,
            "pageSize": 10,
            "where": {"keywords": "", "projectId": project_id}
        }
        res = requests.post(url=url, json=body, headers=header)
        if res.status_code == 200:
            try:
                yield res.json()
            except Exception as e:
                print("获取数据失败,重新获取中...:", res.status_code, "错误信息:", res.text)


def detail_data(hourse_id=None, token=""):
    header = {
        "gzfauthentication": token
    }
    print("获取数据中.... hourse_id: " + str(hourse_id))
    res = requests.get(
        url='https://select.pdgzf.com/api/v1.0/app/gzf/house/' + str(hourse_id), headers=header)
    if res.status_code == 200:
        try:
            return res.json()
        except Exception as e:
            print("获取数据失败,重新获取中...:", res.status_code, "错误信息:", res.text)


def get_captcha():
    while True:
        code_res = s.get(
            url="https://select.pdgzf.com/api/v1.0/gzf/captcha/image/captcha.png?height=47&width=135&date=1638589964620")
        print("获取验证码...")
        if code_res.status_code == 200:
            fp = io.BytesIO(code_res.content)
            with fp:
                img = mpimg.imread(fp, format='png')
            plt.imshow(img)
            plt.show()
            break
        else:
            print("获取失败等待重新获取...")
            time.sleep(2)


def login(account, password):
    token = "xxxxxxxxxxx"
    print("start login")
    get_captcha()
    while True:
        captcha = input("请输入验证码：")
        body = {
            "account": account,
            "password": password,
            "captcha": str(captcha)
        }
        user_res = s.post(
            url="https://select.pdgzf.com/api/v1.0/app/gzf/user/login", json=body)
        if user_res.status_code == 200 and user_res.json()['success']:
            print("登录成功...")
            token = user_res.json()['data']['accessToken']
            break
        else:
            print("登录失败,等待重新登录", user_res.status_code, "错误信息:", user_res.text)
            get_captcha()
    return token


def toDate(timestamp):
   return datetime.fromtimestamp(timestamp/1000)


type_dict = {}
type_dict[1] = "一室"
type_dict[2] = "一室一厅"
type_dict[3] = "两室"
type_dict[4] = "两室一厅"
type_dict[5] = "三室"
type_dict[6] = "三室一厅"
type_dict[7] = "四室"
type_dict[8] = "五室"

header = "名称,价格,面积,户型,起租日期,预计位置,已选,第一日期,地铁距离,详情链接"

def format_output(detail):
    fullName = detail['fullName']
    rent = detail['rent']
    area = detail['area']
    typeName = type_dict[detail['typeName']]
    emoveInDate = toDate(detail['emoveInDate'])
    queuePosition = detail['queuePosition']
    queueCount = detail['queueCount']
    l = list(map(lambda person: person['qualification']['startDate'], detail['queue']))
    if len(l) > 0:
        l.sort()
        firstDate = l[0]
    else:
        firstDate = 'null'
    metroDistance = detail['metroDistance']
    url = 'https://select.pdgzf.com/houseDetails?Id=' + \
        str(detail['id'])

    return f"{fullName},{rent},{area},{typeName},{emoveInDate},{queuePosition},{queueCount},{firstDate},{metroDistance},{url}"


def execute(token):
    housing_estates = []
    houses = []
    estates_page = page_count = next(loop_url_for_data(
        "https://select.pdgzf.com/api/v1.0/app/gzf/project/list"))['data']['pageCount']
    for estate in loop_url_for_data("https://select.pdgzf.com/api/v1.0/app/gzf/project/list", estates_page):
        for e in estate['data']['data']:
            e['metroDistance'] = "无"
            latitude = e['latitude']
            longitude = e['longitude']
            nearby_res = requests.get(
                f"https://api.map.baidu.com/place/v2/search?query=地铁&location={latitude},{longitude}&radius=2000&output=json&ak=ANwXDC5L7Af2InEayr5p1gi6tHmunrv3")
            nearby_res_json = nearby_res.json()
            if 'results' in nearby_res_json and len(nearby_res_json['results']) > 0:
                nearby = nearby_res_json['results'][0]
                metro_latitude = nearby['location']['lat']
                metro_longitude = nearby['location']['lng']
                distance_res = requests.get(
                    f"https://api.map.baidu.com/routematrix/v2/walking?ak=ANwXDC5L7Af2InEayr5p1gi6tHmunrv3&origins={latitude},{longitude}&destinations={metro_latitude},{metro_longitude}")
                distance_res_json = distance_res.json()
                if 'result' in distance_res_json and len(distance_res_json['result']) > 0:
                    distance = distance_res_json['result'][0]['distance']['text']
                    # print(e['address'] + " " + distance)
                    e['metroDistance'] = distance
        housing_estates += estate['data']['data']
    for estate in housing_estates:
        if estate['name'] not in exclued_list:
            page_count = 1
            page_count = next(loop_url_for_data("https://select.pdgzf.com/api/v1.0/app/gzf/house/list",
                                                page_count=page_count, project_id=estate['id']))['data']['pageCount']
            for house in loop_url_for_data("https://select.pdgzf.com/api/v1.0/app/gzf/house/list", page_count, project_id=estate['id'], token=token):
                for h in house['data']['data']:
                    h['metroDistance'] = estate['metroDistance']
                    detail = detail_data(h['id'], token=token)
                    h['queuePosition'] = detail['data']['queuePosition']
                    h['queue'] = detail['data']['queue']
                    del h['project']
                houses += house['data']['data']
    return houses


def print_output():
    output = open("output.json", 'r')
    lines = output.readlines()
    print(header)
    for line in lines:
        h = json.loads(line)
        a = format_output(h)
        print(a)

def save_to_file(houses):
    output_file = open("output.json", "w")
    csv_file = open("./data/" + str(datetime.now())[:10] + "_order.csv", "w")
    csv_file.write(f"{header}\n")
    for h in houses:
        # only check area >= 50
        if float(h['area']) >= min_area_size:
            output_file.write(json.dumps(h) + "\n")
            csv_file.write(format_output(h) + "\n")
    output_file.close()
    csv_file.close()


def tokenExpire():
    mtime = os.path.getmtime("./token")
    hours_ago_23 = datetime.now() - timedelta(hours=12)
    filetime = datetime.fromtimestamp(mtime)
    return filetime < hours_ago_23

def getToken(phone, pwd):
    if tokenExpire():
        token = login(phone, pwd)
        text_file = open("token", "w")
        text_file.write(token)
        text_file.close()
        print("save non-expired token to file")
    else:
        print("recover non-expired token from file")
        text_file = open("token", "r")
        token = text_file.read().replace('\n', '')
        text_file.close()
    return token

exclued_list = [
    '民生路318弄(馨澜公寓)', '康涵路58弄（世茂云图）', '永泰路136弄', 
    '航亭环路399弄（东方鸿璟园）', '上南路3880弄', '千汇路198弄（公元2040）', 
    '宣黄公路2585弄（惠南宝业华庭）', '秋亭路88弄（朗诗未来树）', '玉盘北路281弄（浦发华庭）', 
    '航城三路288弄（同悦湾华庭）', '新环北路1333弄（中洲华庭）', '绿晓路58弄（三湘海尚福邸）',
    '妙川路800弄（川沙博景苑）', '周东南路388弄（丰和雅苑）', '蓝靛路1688弄（保利艾庐）',
    '孙农路397弄（朗阅华庭）', '祝家港路399弄（九龙仓兰廷）', '周秀路398弄（汇福家园）',
    '诚礼路298弄（紫金轩）', '崇溪路111弄（绣云新都）'
    ]

# only save the houses which's area > min_area_size
min_area_size = 50.0

phone = '11111111111'
# find encode string by debug in browser
pwd = 'aaaaaaaaaaaaaaaa=='
token = getToken(phone, pwd)
houses = execute(token)
save_to_file(houses)
# print_output()