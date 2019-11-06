#coding:utf-8

from . import api 
from ihome.utils.captcha.captcha import captcha 
from ihome.libs.yuntongxun.sms import CCP
from flask import make_response,jsonify,current_app,request
from ihome import constants,redis_store,db
from ihome.utils.response_code import RET
from ihome.models import User
from ihome.tasks.sms.tasks import send_sms
import json

import random

@api.route("/image_codes/<image_code_id>")
def get_image_code(image_code_id):
    """
    获取图片验证码
    ：params image_code_id：图片验证码编号
    ：return：正常：验证码图片 异常：返回json
    """
    #业务逻辑处理
    #生成验证码图片
    #名字，真实文本，图片数据
    name,  text,  image_data = captcha.generate_captcha()
    #存储验证码，设置有效期
    try:
        redis_store.setex("image_code_{}".format(image_code_id),constants.IMAGE_CODE_REDIS_EXPIRES,text)
    except Exception as e:
        #记录日志
        current_app.logger.error(e)
        #返回异常
        return jsonify(errno=RET.DBERR,errmsg="保存图片验证码失败")

    #返回图片
    resp = make_response(image_data)
    resp.headers["Content-Type"] = "image/jpg"
    return resp


#GET /api/v1.0/sms_codes/<mobile>?image_code=xxxx&image_code_id=xxxxx
@api.route("/sms_codes/<re(r'1[34578]\d{9}'):mobile>")
def get_sms_code(mobile):
    """获取短信验证码"""
    #获取参数
    image_code = request.args.get("image_code")
    image_code_id = request.args.get("image_code_id")

    #校验参数
    if not all([image_code,image_code_id]):
        #表示参数不完整
        return jsonify(errno=RET.DATAERR,errmsg="参数不完整")

    #业务逻辑
    #从redis取出真实图片验证码
    try:
        real_image_code = redis_store.get("image_code_{}".format(image_code_id))
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="redis 数据库异常")
    
    #判断图片验证码是否过期
    if real_image_code is None:
        #表示图片验证码没有或者过期
        return jsonify(errno=RET.NODATA,errmsg="图片验证码失效")

    #删除redis中的图片验证码，防止用户使用同一个图片验证码被验证多次


    try:
        redis_store.delete("image_code_{}".format(image_code_id))
    except Exception as e:
        current_app.logger.error(e)

    #对比验证码
    real_image_code = bytes.decode(real_image_code)
    if real_image_code.upper() != image_code.upper():
        #表示用户填写错误
        return jsonify(errno=RET.PARAMERR,errmsg="图片验证码错误")

    #判断对于这个手机号的操作，在60秒内有没有之前的记录，如果有，则认为用户操作频繁，不接受处理
    try:
        send_flag = redis_store.get("send_sms_code_{}".format(mobile))
    except Exception as e:
        current_app.logger.error(e)
    else:
        if send_flag is not None:
            #表示之前60秒内有发送过记录
            return jsonify(errno=RET.DATAEXIST,errmsg="请求过于频繁")

    #判断手机号是否存在
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
    else:
        if user is not None:
            #表示用户不存在
            return jsonify(errno=RET.DATAEXIST,errmsg="手机号已存在")

    #如果手机号不存在，则生成短信验证码
    sms_code = "%06d" % random.randint(0,999999)
    #保存真实验证码
    try:
        redis_store.setex("sms_code_{}".format(mobile),constants.SMS_CODE_REDIS_EXPIRES,sms_code)
        #保存发送这个手机号的记录，防止用户在60s内再次触发发送验证码的操作
        redis_store.setex("send_sms_code_{}".format(mobile),constants.SEND_SMS_CODE_INTERVAL,1)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="保存短信验证码异常")
    #发送短信
    #ccp = CCP()
    #try:
    #    result = ccp.send_template_sms(mobile,sms_code,str(int(constants.SMS_CODE_REDIS_EXPIRES/60)),1)
    #except Exception as e:
    #    current_app.logger.error(e)
    #    return jsonify(errno=RET.THIRDERR,errmsg="发送异常")
    
    #if result == 0:
    #    #表示发送成功
    #    return jsonify(errno=RET.OK,errmsg="短信验证码发送成功")
    #else:
    #    #发送不成功
    #    return jsonifg(errno=RET.THIRDERR,errmsg="发送失败")
    #返回异步任务对象
    result_obj = send_sms.delay(mobile,sms_code,str(int(constants.SMS_CODE_REDIS_EXPIRES/60)),1)
    print(result_obj.id)

    #返回值
    return jsonify(errno=RET.OK,errmsg="发送成功")


