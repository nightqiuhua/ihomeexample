#coding:utf-8

from . import api 
from flask import current_app,request,jsonify
from ihome.utils.response_code import RET
from ihome.utils.commons import login_required
from ihome.utils.image_storage import storage
from ihome.models import Area,House,Facility,HouseImage
from ihome import db,redis_store,constants
import json

#从redis中提取出的数据是格式是字节形式的字符串一定要进行类型的转换


@api.route("/areas",methods=["GET"])
def get_area_info():
    """获取城区信息"""
    # 尝试从redis中获取数据
    try:
        resp_json = redis_store.get("area_info")
        resp_json = json.loads(resp_json)
    except Exception as e:
        current_app.logger.error(e)
    else:
        if resp is not None:
            # redis 有缓存数据
            current_app.logger.info("hit redis area_info")
            return resp_json,200,{"Content-Type":"applicatin/json"}

    # 查询数据库，读取城区信息
    try:
        area_li = Area.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据库异常")

    area_dict_li = []
    # 将对象转换为字典
    for area in area_li:
        area_dict_li.append(area.to_dict())

    # 将数据转换为json字符串
    resp_dict = dict(errno=RET.OK,errmsg="OK",data=area_dict_li)
    resp_json = json.dumps(resp_dict)

    # 将数据保存到redis中
    try:
        redis_store.setex("area_info",constants.AREA_INFO_REDIS_CACHE_EXPIRES,resp_json)
    except Exception as e:
        current_app.logger.error(e)
    
    return resp_json,200,{"Content-Type":"application/json"}


@api.route("/houses/info",methods=["POST"])
@login_required
def save_house_info():
    """保存房屋的基本信息
    前端发送过来的json数据
    {
        "title":"",
        "price":"",
        "area_id":"1",
        "address":"",
        "room_count":"",
        "acreage":"",
        "unit":"",
        "capacity":"",
        "beds":"",
        "deposit":"",
        "min_days":"",
        "max_days":"",
        "facility":["7","8"]
    }
    """
    # 获取数据
    user_id = g.user_id
    house_data = request.get_json()

    title = house_data.get("title")  # 房屋名称标题
    price = house_data.get("price")  # 房屋单价
    area_id = house_data.get("area_id")  # 房屋所属城区的编号
    address = house_data.get("address")  # 房屋地址
    room_count = house_data.get("room_count")  # 房屋包含的房间数目
    acreage = house_data.get("acreage")  # 房屋面积
    unit = house_data.get("unit")  # 房屋布局（几室几厅)
    capacity = house_data.get("capacity")  # 房屋容纳人数
    beds = house_data.get("beds")  # 房屋卧床数目
    deposit = house_data.get("deposit")  # 押金
    min_days = house_data.get("min_days")  # 最小入住天数
    max_days = house_data.get("max_days")  # 最大入住天数

    #校验参数
    # 判断参数是否完整
    if not all([title, price, area_id, address, room_count, acreage, unit, capacity, beds, deposit, min_days, max_days]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")

    # 判断金额是否正确
    try:
        price = int(float(price)*100)
        deposit = int(float(deposit)*100)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR,errmsg="参数错误")

    # 判断城区id是否存在
    try:
        area = Area.query.get(area_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据库异常")

    if area is None:
        return jsonify(errno=RET.NODATA,errmsg="城区信息有误")

    #业务逻辑
    # 保存房屋信息
    house = House(
        user_id = user_id,
        area_id = area_id,
        title = title,
        price = price,
        address = address,
        room_count = room_count,
        acreage = acreage,
        unit = unit,
        capacity = capacity,
        beds = beds,
        deposit = deposit,
        min_days = min_days,
        max_days = max_days
    )

    # 处理房屋的设施信息
    facility_ids = house_data.get("facility")

    # 如果用户勾选了设施信息，再保存数据库
    if facility_ids:
        try:
            facilities = Facility.query.filter(Facility.id.in_(facility_ids))
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR,errmsg="数据库异常")

        if facilities:
            #表示有合法的设施数据
            #保存数据
            house.facilities = facilities

    try:
        db.session.add(house)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="保存数据异常")

    #返回数据
    return jsonify(errno=RET.OK,errmsg="OK",data={"house_id":house.id})


@api.route("/house/image",methods=["POST"])
@login_required
def save_house_image():
    """保存房屋图片
    参数  图片 房屋的id
    """
    image_file = request.file.get("house_image")
    house_id = request.form.get("house_id")

    if not all([image_file,house_id]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数不完整")

    # 判断house_id正确性
    try:
        house = House.query.get(house_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据库异常")

    if house is None:
        return jsonify(errno=RET.NODATA,errmsg="房屋不存在")

    image_data = image_file.read()
    #保存图片到七牛中
    try:
        file_name = storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg="保存图片失败")

    # 保存图片信息到数据库中
    house_image = HouseImage(house_id=house_id,url=file_name)
    db.session.add(house_image)

    # 处理房屋的主图片
    if not house.index_image_url:
        #如果房屋的主图片不存在
        house.index_image_url = file_name
        db.session.add(house)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg="保存图片数据异常")

    image_url = constants.QINIU_URL_DOMAIN+file_name

    # 返回处理
    return jsonify(errno=RET.OK,errmsg="OK",data={"image_url":image_url})

@api.route("/user/houses",methods=["GET"])
@login_required
def get_usr_houses():
    """获取用户发布的房源信息"""
    user_id = g.user_id

    try:
        user = User.query.get(user_id)
        houses = user.houses
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="获取数据失败")

    # 将查询到的房屋信息转换为字典存放到列表中

    if houses:
        houses_list = [house.to_basic_dict() for house in houses]
    return jsonify(errno=RET.OK,errmsg="OK",data={"houses":houses_list})
        


@api.route("/house/index",methods=["GET"])
def get_house_index():
    """获取主页幻灯片展示的房屋基本信息"""
    # 从缓存中获取数据
    try:
        ret = redis_store.get("home_page_data")
    except Exception as e:
        current_app.logger.error(e)
        ret = None

    if ret:
        # 如果存在有缓存数据
        current_app.logger.info("hit house index info redis")
        #
        return '{"errno":0,"errmsg":"OK","data":{}}'.format(ret),200,{"Content-Type":"application/json"}
    else:
        try:
            # 如果缓存中没有数据，查询数据库，返回房屋订单数目最多的5条数据
            house = House.query.order_by(House.order_count.desc()).limit(constants.HOME_PAGE_MAX_HOSUE)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR,errmsg="查询数据失败")

        if not houses:
            #房屋数据不存在
            return jsonify(errno=RET.NODATA,errmsg="查询没有数据")

    #返回数据
    houses_list = []
    for house in houses:
        # 如果房屋未设置主图片，则跳过
        if not house.index_image_url:
            continue
        houses_list.append(house.to_basic_dict())

    # 将数据转为json，并保存到redis缓存
    json_houses = json.dumps(houses_list)
    try:
        redis_store.setex("home_page_data",constants.HOME_PAGE_DATA_REDIS_EXPIRES,json_houses)
    except Exception as e:
        current_app.logger.error(e)
    return '{"errno":0, "errmsg":"OK", "data":%s}' % json_houses, 200, {"Content-Type": "application/json"}
    
@api.route("/houses/<int:house_id>",methods=["GET"])
def get_house_detail(house_id):
    """获取房屋详情"""
    # 前端在房屋详情页面展示时，如果浏览页面的用户不是该房屋的房东，则展示预定按钮，否则不展示
    # 所以需要返回登录用户的user_id

    #获取参数
    # 尝试获取用户登录的信息，若登录，则返回给前端登录用户的user_id，否则返回user_id = -1
    user_id = session.get("user_id",-1)


    #校验参数
    if not hosue_id:
        return jsonify(errno=RET.PARAMERR,errmsg="参数缺失")

    #业务逻辑
    # 先从redis缓存中获取信息
    try:
        ret = redis_store.get("house_info_{}".format(house_id))
    except Exception as e:
        current_app.logger.error(e)
        ret = None
    if ret:
        current_app.logger.info("hit hosue for redis")
        return '{"errno":"0","errmsg":"OK","data":{"user_id":%s,"house":%s}}' % (user_id,ret),200,{"content-Type":"application/json"}
    # 查询数据库

    try:
        house = House.query.get(house_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

    if not house:
        return jsonify(errno=RET.NODATA,errmsg="房屋不存在")

    # 将房屋对象数据转换字典
    try:
        house_data = house.to_full_dict()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR,errmsg="数据出错")

    # 存入redis中
    json_house = json.dumps(house_data)
    try:
        redis_store.setex("house_info_{}".format(house_id),constants.HOUSE_DETAIL_REDIS_EXPIRE_SECOND,house_data)
    except Exception as e:
        current_app.logger.error(e)

    resp = '{"errno":"0", "errmsg":"OK", "data":{"user_id":%s, "house":%s}}' % (user_id, json_house), \
           200, {"Content-Type": "application/json"}

    #返回数据
    return resp