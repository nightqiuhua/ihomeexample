#coding:utf-8 

from qiniu import Auth,put_data,etag,urlsafe_base64_decode
import qiniu.config 

# 填写Access Key 和 Secret Key 
access_key = 'pvEWD5kRXAEJJIrKYtdJNzENnsRT7Ei9IrNqT3md'
secret_key = '3nmjoADmGVsI2lbtrd0kvXxqfgM1YSgtzm7oQgiI'

def storage(file_data):
    """
    上传文件到七牛
    :param file_data: 要上传的文件数据
    :return:
    """
    # 构建鉴权对象
    q = Auth(access_key,secret_key)

    # 要上传的空间
    bucket_name = 'ihome-qiu'

    # 生成上传Token,可以指定过期时间等
    token = q.upload_token(bucket_name,None,3600)

    ret,info = put_data(token,None,file_data)


    if info.status_code == 200:
        # 表示上传文件成功，返回文件名
        return ret.get("key")
    else:
        # 表示上传文件失败
        raise Exception("上传七牛失败")



