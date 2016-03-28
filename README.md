=============================
HttpDNS
=============================
## 描述
基于DNSPOD(D+)移动解析的一个HttpDNS调度的一个小项目，目的是利用DNSPOD的免费D+解析服务来构建基于HTTP协议的域名解析及调度功能
HttpDNS的特点：
* 防止域名污染
* 接入简单
* 调度精准
* 水平扩展


## 适用场景
不想受困于各种运营商的域名污染以及域名缓存更新缓慢的APP移动应用，同时又有精准调度的需求
比如需要根据APP版本区分访问接口，旧版本访问old.my_api.com,新版本访问new.my_api.com


## 额外支持
支持DNSPOD D+ 企业版(详细见配置方式)


## 部署环境要求

#### 网络环境
* BGP（支持any cast更佳）

#### 软件环境（Python第三方库）
* django
* requests
* pyDes
* leveldb


## 部署方式
    $ git clone https://github.com/luost/HttpDNS
    $ cd httpdns
    $ pip install -r requirements.txt
    $ python manager runserver 0.0.0.0:80 # 推荐使用uwsgi + nginx部署


## 应用接入方式
数据请求和应答均使用 http get 协议。

####请求格式
接口示例：为“http://ip:port/?domain=www.163.com.&client_ip=1.1.1.1”
* domain 必选，表示要查询的域名
* client_ip 可选，表示用户 ip，可以不携带 client_ip 参数，当没有这个 ip 参数时，服务器会把 http 报文的源 ip 当做用户 ip。
* ttl 可选，指定域名解析的ttl
除了以上三个参数，在请求的同时可以携带任何自定义参数，用于调度时使用，如：
* http://ip:port/?domain=www.163.com.&client_ip=1.1.1.1&client_version=v1.0.1&platform=ios&user_id=111111

####返回格式
返回示例：{"server_ip_list": ["1.1.1.1", "2.2.2.2"], "ttl": 600, domain": "node1.www.163.com", "backup": [ip1, ip2]}
* server_ip_list 为针对提交的domain参数解析出的IP，当域名错误或不存在时，该值为空列表
* ttl 为域名的ttl
* domain 为调度后的新域名，只是一个调度结果显示，客户端可以不解析
* backup 为服务器的备用IP，如果当前IP访问失效，可以使用该列表的任何一个IP发起访问(可配置)，也可使用轮询访问策略


##配置方式

#### httpdns/config.py:
<pre><code># -*- coding: UTF-8 -*-

from httpdns.settings import BASE_DIR


# DATABASE PATH
DB_PATH = BASE_DIR + "/database"


# BACKUP SERVER IP
BACKUP_IP_LIST = []


# DEFAULT DOMAIN CACHE TTL(default is 86400, it's not dns server ttl!). in seconds
DEFAULT_DOMAIN_CACHE_TTL = 86400


# USE D+ ENTERPRISE VERSION(default is False)
D_PLUS_ENTERPRISE_VERSION = False


# AVAILABLE WHEN D_PLUS_ENTERPRISE_VERSION SET TO True
D_PLUS_ID = ""
D_PLUS_SECRET = ""


# DISPATCH EXPRESS MAP
#
# FORMAT:
#       {
#           express_name: [COMPARE_METHOD, COMPARE_FIELD, COMPARE_VALUE],
#           ...
#       }
#
# COMPARE_METHOD LIST:
#   $gt     ->  ">"
#   $gte    ->  ">="
#   $lt     ->  "<"
#   $lte    ->  "<="
#   $in     ->  "in"
#   $nin    ->  "not in"
#   $eq     ->  "=="
#   $neq    ->  "!="
#   $regex  ->  regular pattern
#   $lambda ->  function(match_filed): return boolean
#
# COMPARE_FIELD:
#
#   by default, you have the following COMPARE_FIELD:
#       1. all django queryset META data(all field in request.META). like: "HTTP_USER_AGENT", "HTTP_X_FORWARDED_FOR"
#       2. all http header from http client.
#       3. all http(get) params from http client.(all field request.GET.dict())
#
# EXAMPLE:
#   # assume request url is "http://localhost/resolve?domain=www.a.com&field_1=v1&field_2=88888"
#   # so you can use "field_1", "field_2" as COMPARE_FIELD.
#   ["$in", "field_1", "v1,v2"]                                 ---> "if "v1" in ['v1', 'v2']"
#   ["$gte", "field_2", 15]                                     ---> "if 88888 >= 15"
#   ["$regex", "field_1", "^v\d{1,3}$"],                       ---> "if re.match( r'^v\d{1,3}$', 'v1')"
#   ["$lambda", "field_1", "lambda x.startswith('v')"]            ---> "if 'v1'.startswith('v1.0')"
#
#   # assume HTTP_X_FORWARDED_FOR is "10.1.1.1"
#   ["$neq", "HTTP_X_FORWARDED_FOR", "127.0.0.1"]               ---> "if '10.1.1.1' != '127.0.0.1'"
EXPR_MAP = {
    "expr1": ["$in", "field_1", "v1,v2"],
    "expr2": ["$gte", "field_2", 15],
    "expr3": ["$lte", "field_2", 99999],
    "expr4": ["$regex", "field_1", "^v\d{1,3}$"],
    "expr5": ["$lambda", "field_1", "lambda x: x == 'v3'"],
}


# DISPATCH RULE
#
# FORMAT:
#       {
#           domain: [REPLACE_DOMAIN, EXPRESS_NAME_LIST],
#           ...
#       }
#
# EXAMPLE:
#       {
#           "api.a.com": [
#               # if resolve domain is "api.a.com" and matched all express(expr1 in EXPR_MAP), return "test.a.com"
#               ["test.a.com", ["expr1", "expr2"]],
#
#               # if resolve domain is "forbid.a.com" and matched all express(expr3 in EXPR_MAP), return "forbid.a.com"
#               ["forbid.a.com", ["expr3"]],
#            ],
#
#           "api.b.com": [
#               ...
#           ],
#       }
DISPATCH_RULE = {
    "www.163.com": [
        ["mirrors.163.com", ["expr1", "expr2", "expr3", "expr4"]],
        ["news.163.com", ["expr5"]],
    ]
}
</code></pre>


## 后续
加上WEB管理界面，去掉繁琐难看的配置文件模式

## 联系
root@luost.org



