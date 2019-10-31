    #-*- coding: UTF-8 -*-
    #  Copyright (c) 2014 The CCP project authors. All Rights Reserved.
    #
    #  Use of this source code is governed by a Beijing Speedtong Information Technology Co.,Ltd license
    #  that can be found in the LICENSE file in the root of the web site.
    #
    #   http://www.yuntongxun.com
    #
    #  An additional intellectual property rights grant can be found
    #  in the file PATENTS.  All contributing project authors may
    #  be found in the AUTHORS file in the root of the source tree.

from  datetime import datetime
import hashlib
import base64
import requests
import json


from xml.dom import minidom 

class REST:
    
    AccountSid=''
    AccountToken=''
    AppId=''
    SubAccountSid=''
    SubAccountToken=''
    ServerIP=''
    ServerPort=''
    SoftVersion=''
    Iflog=True #是否打印日志
    Batch=''  #时间戳
    BodyType = 'xml'#包体格式，可填值：json 、xml
    base_url = 'https://app.cloopen.com:8883'
    
     # 初始化
     # @param serverIP       必选参数    服务器地址
     # @param serverPort     必选参数    服务器端口
     # @param softVersion    必选参数    REST版本号
    def __init__(self,ServerIP,ServerPort,SoftVersion):

        self.ServerIP = ServerIP;
        self.ServerPort = ServerPort;
        self.SoftVersion = SoftVersion;
    
    
    # 设置主帐号
    # @param AccountSid  必选参数    主帐号
    # @param AccountToken  必选参数    主帐号Token
    
    def setAccount(self,AccountSid,AccountToken):
      self.AccountSid = AccountSid;
      self.AccountToken = AccountToken;   
    

    # 设置子帐号
    # 
    # @param SubAccountSid  必选参数    子帐号
    # @param SubAccountToken  必选参数    子帐号Token
 
    def setSubAccount(self,SubAccountSid,SubAccountToken):
      self.SubAccountSid = SubAccountSid;
      self.SubAccountToken = SubAccountToken;    

    # 设置应用ID
    # 
    # @param AppId  必选参数    应用ID

    def setAppId(self,AppId):
       self.AppId = AppId; 
    
    def log(self,url,body,data):
        print('这是请求的URL：')
        print(url);
        print('这是请求包体:')
        print(body);
        print('这是响应包体:')
        print(data);
        print('********************************')


    # 发送模板短信
    # @param to  必选参数     短信接收彿手机号码集合,用英文逗号分开
    # @param datas 可选参数    内容数据
    # @param tempId 必选参数    模板Id
    def sendTemplateSMS(self,phone,code,atime,templateId):

        # 获取时间戳
        timestamp = self.gen_timestamp()
        # 生成签名
        sig = self.gen_sig(timestamp)
        # 请求url
        url = self.gen_request_url(sig)
        # 请求头
        header = self.gen_request_header(timestamp)
        # 请求体
        body = self.gen_request_body(phone,code,atime,templateId)
        #请求云通信接口
        data = self.request_yuntongxin_api(url,header,json.dumps(body))
        return data

    # 构造请求url
    def gen_request_url(self,sig):
        self.url = self.base_url + '/2013-12-26/Accounts/{}/SMS/TemplateSMS?sig={}'.format(self.AccountSid,sig)
        return self.url

    # 构造请求头
    def gen_request_header(self,timestamp):
        authorization = self.gen_authorization(timestamp)
        return {
            "Accept":"application/json",
            "Content-Type":"application/json;charset=utf-8",
            "Authorization":authorization
        }

    # 构建请求体
    def gen_request_body(self,phone,code,atime,templateId):
        return {
            "to":phone,
            "appId":self.AppId,
            "templateId":templateId,
            "datas":[code,atime]
        }



    # 获取 Authorization
    def gen_authorization(self,timestamp):
        return self.base64_encode(self.AccountSid+':'+timestamp)

    # base64加密
    def base64_encode(self,raw):
        return base64.b64encode(raw.encode('utf-8')).decode()


    # 生成签名文档
    def gen_sig(self,timestamp):
        return self.md5(self.AccountSid+self.AccountToken+timestamp)

    # 生成时间戳
    def gen_timestamp(self):
        return  datetime.now().strftime('%Y%m%d%H%M%S')

    # md5加密
    def md5(self,raw):
        md5 = hashlib.md5()
        md5.update(raw.encode('utf-8'))
        return md5.hexdigest().upper()

    # 请求云通信接口
    def request_yuntongxin_api(self,url,header,body):
        response = requests.post(url,headers=header,data=body)
        return json.loads(response.text)