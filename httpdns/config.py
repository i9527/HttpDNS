# -*- coding: UTF-8 -*-

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
