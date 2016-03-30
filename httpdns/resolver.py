# -*- coding: UTF-8 -*-

import os
import re
import time
import json
import copy
import urllib

import leveldb
import requests
import pyDes

from httpdns.config import BACKUP_IP_LIST, D_PLUS_ID, D_PLUS_SECRET, D_PLUS_ENTERPRISE_VERSION
from httpdns.config import DISPATCH_RULE, EXPR_MAP, DB_PATH, DEFAULT_DOMAIN_CACHE_TTL


class RpcFormatter(object):
    """
    rpc format module
    """

    @staticmethod
    def resolve_wrapper(func):
        """
        rpc format wrapper
        :param func:
        :return: json
        """
        def _wrapper_(*args, **kwargs):
            server_ip_list, ttl, domain = func(*args, **kwargs)
            data = {
                "server_ip_list": server_ip_list,
                "ttl": ttl, 
                "backup": BACKUP_IP_LIST,
                "domain": domain,
            }
            return json.dumps(data)
        return _wrapper_


class DNSResolver(object):
    """
    dns resolve module
    """

    def __init__(self, domain, client_ip=None, client_extra_info=None, ttl=None):
        """
        init
        :param domain:  request domain
        :param client_ip: request client ip
        :param client_extra_info: http get params dict(request.GET.dict())
        :param ttl:  domain ttl
        :return: None
        """
        self.domain = domain
        self.client_ip = client_ip
        self.client_extra_info = client_extra_info or dict()
        self.ttl = ttl
        if self.ttl is None:
            self.ttl = 1

    @RpcFormatter.resolve_wrapper
    def resolve(self):
        """
        resolve dns
        :return: server_ip_list, ttl, domain
        """
        dispatch_rule = CacheController.get_dispatch_rule_cache(self.domain)
        dispatcher = Dispatcher(self.client_extra_info, dispatch_rule)
        domain = dispatcher.get_dispatched_domain()
        if domain is None:
            domain = self.domain
        server_ip_list, ttl = CacheController.get_resolve_cache(domain, self.client_ip, 
                                                                ttl=self.ttl)
        if server_ip_list is not None:
            return server_ip_list, ttl, domain
        if D_PLUS_ENTERPRISE_VERSION:
            server_ip_list, ttl = self._enterprise_version_resolver_(domain, self.client_ip)
        else:
            server_ip_list, ttl = self._base_resolver_(domain, self.client_ip)
        if server_ip_list is None or ttl is None:
            server_ip_list, ttl = [], 0
        else:
            CacheController.set_resolve_cache(domain, self.client_ip, server_ip_list)
        return server_ip_list, ttl, domain

    @classmethod
    def _base_resolver_(cls, domain, client_ip):
        """
        resolve from "http://119.29.29.29/d" (free version)
        when D_PLUS_ENTERPRISE_VERSION is False
        :param domain:
        :param client_ip:
        :return: server_ip_list, ttl
        """
        params = {"dn": domain, "ip": client_ip, "ttl": 1}
        url = "http://119.29.29.29/d?" + urllib.urlencode(params)
        _server_ip_list, _ttl = None, None
        try:
            res = requests.get(url)
            if res.status_code == 200 and res.content:
                _ip_str, _ttl = res.content.split(",")
                _server_ip_list = _ip_str.split(";")
        except:
            return _server_ip_list, _ttl

    @classmethod
    def _enterprise_version_resolver_(cls, domain, client_ip):
        """
        resolve from "http://119.29.29.29/d" (enterprise version)
        when D_PLUS_ENTERPRISE_VERSION is True
        :param domain:
        :param client_ip:
        :return:
        """
        des_obj = pyDes.des(D_PLUS_SECRET, pyDes.ECB, padmode=pyDes.PAD_PKCS5)
        domain = des_obj.encrypt(domain)
        params = {"dn": domain, "id": D_PLUS_ID, "ip": client_ip, "ttl": 1}
        url = "http://119.29.29.29/d?" + urllib.urlencode(params)
        _server_ip_list, _ttl = None, None
        try:    
            res = requests.get(url)
            if res.status_code == 200 and res.content:
                content = des_obj.decrypt(res.content, padmode=pyDes.PAD_PKCS5)
                _ip_str, _ttl = content.split(",")
                _server_ip_list = _ip_str.split(";")
        except:
            return _server_ip_list, _ttl


class Dispatcher(object):
    """
    dispatch module
    """
    
    def __init__(self, client_extra_info, dispatch_rule):
        """
        init
        :param client_extra_info: http get params dict(request.GET.dict())
        :param dispatch_rule: dispatch rule
        :return:
        """
        self.client_extra_info = client_extra_info
        self.dispatch_rule = dispatch_rule
        if self.client_extra_info is None:
            self.client_extra_info = {}
        if self.dispatch_rule is None:
            self.dispatch_rule = []

        self._expr_map_ = {
            "$lambda": self._lambda_, 
            "$gt": self._gt_, "$lt": self._lt_, "$gte": self._gte_, 
            "$lte": self._lte_, "$eq": self._eq_, "$neq": self._neq_, 
            "$in": self._in_, "$nin": self._nin_, "$regex": self._regex_,
        }

    def get_dispatched_domain(self):
        """
        get dispatched domain
        if doesn't match any rule, return None
        :return: str
        """
        if not self.dispatch_rule:
            return None
        for _rule in self.dispatch_rule:
            _match = False
            _domain, _expr_list = _rule[0:2]
            for i in _expr_list:
                _expr, _key, _value = i[0:3]
                _func = self._expr_map_.get(_expr)
                _real_value = self.client_extra_info.get(_key)
                if _func is None:
                    _match = False
                    break
                if not _func(_real_value, _value):
                    _match = False
                    break
                _match = True
            if _match:
                return _domain
        return None

    @classmethod
    def _gt_(cls, v1, v2):
        """
        comparison operators： greater than
        :param v1:
        :param v2:
        :return: True or False
        """
        try:
            return int(v1) > int(v2)
        except ValueError:
            return False

    @classmethod
    def _gte_(cls, v1, v2):
        """
        comparison operators： greater than or equal
        :param v1:
        :param v2:
        :return: True or False
        """
        try:
            return int(v1) >= int(v2)
        except ValueError:
            return False

    @classmethod
    def _lt_(cls, v1, v2):
        """
        comparison operators： less than
        :param v1:
        :param v2:
        :return: True or False
        """
        try:
            return int(v1) < int(v2)
        except ValueError:
            return False

    @classmethod
    def _lte_(cls, v1, v2):
        """
        comparison operators： less than or equal
        :param v1:
        :param v2:
        :return: True or False
        """
        try:
            return int(v1) <= int(v2)
        except ValueError:
            return False

    @classmethod
    def _eq_(cls, v1, v2):
        """
        comparison operators: equal
        :param v1:
        :param v2:
        :return: True or False
        """
        return str(v1) == str(v2)

    @classmethod
    def _neq_(cls, v1, v2):
        """
        comparison operators: not equal
        :param v1:
        :param v2:
        :return: True or False
        """
        return str(v1) != str(v2)

    @classmethod
    def _in_(cls, v1, v2, split_str=","):
        """
        comparison operators: in
        by default, split pattern is ","
        :param v1:
        :param v2:
        :return: True or False
        """
        return str(v1) in str(v2).split(split_str)

    @classmethod
    def _nin_(cls, v1, v2, split_str=","):
        """
        comparison operators: not in
        by default, split pattern is ","
        :param v1:
        :param v2:
        :return: True or False
        """
        return str(v1) not in str(v2).split(split_str)

    @classmethod
    def _regex_(cls, v1, v2):
        """
        comparison operators: regular(using re module)
        :param v1:
        :param v2: regular pattern
        :return: True or False
        """
        compiler = re.compile(r'%s' % v2)
        if compiler.findall(str(v1)):
            return True
        return False

    @classmethod
    def _lambda_(cls, v1, v2):
        """
        comparison operators: lambda
        :param v1:
        :param v2: str(function(v1): return boolean)
        :return: True or False
        """
        status = False
        try:
            func = eval(v2)
            status = func(str(v1))
        except:
            return status


class CacheController(object):
    """
    cache controller module
    """

    # level db conn map
    CACHE_CONN_MAP = {}

    @classmethod
    def get_resolve_cache(cls, domain, client_ip, ttl):
        """
        get domain resolve cache
        :param domain:
        :param client_ip:
        :param ttl:
        :return: server_ip_list, ttl
        """
        cache_conn = cls._get_cache_conn_(domain)
        cache_key = cls._get_resolve_cache_key_(domain, client_ip)
        try:
            cache_data = cache_conn.Get(cache_key)
            cache_data = json.loads(cache_data)
        except KeyError:
            return None, None
        except ValueError:
            return None, None
        _ttl = DEFAULT_DOMAIN_CACHE_TTL - (time.time() - cache_data["timestamp"])
        if _ttl < ttl:
            return None, None
        return cache_data["server_ip_list"], int(_ttl)

    @classmethod
    def set_resolve_cache(cls, domain, client_ip, server_ip_list):
        """
        set domain resolve cache
        :param domain:
        :param client_ip:
        :param server_ip_list:
        :return: Always return True
        """
        cache_conn = cls._get_cache_conn_(domain)
        cache_key = cls._get_resolve_cache_key_(domain, client_ip)
        cache_data = {
            "timestamp": time.time(),
            "server_ip_list": server_ip_list,
        }
        cache_data = json.dumps(cache_data)
        cache_conn.Put(cache_key, cache_data)
        return True

    @classmethod
    def del_resolve_cache(cls, domain):
        """
        delete domain resolve cache
        :param domain:
        :return: Always return True
        """
        cache_conn = cls._get_cache_conn_(domain)
        for i in cache_conn.RangeIter():
            cache_key = i[0]
            cache_conn.Delete(cache_key)
        return True

    @classmethod
    def get_dispatch_rule_cache(cls, domain):
        """
        get domain dispatch rule cache
        :param domain:
        :return: dispatch rule or None(if record doesn't exists or record format isn't valid)
        """
        cache_conn = cls._get_cache_conn_(domain)
        cache_key = cls._get_dispatch_rule_cache_key_(domain)
        try:
            cache_data = cache_conn.Get(cache_key)
            dispatch_rule = json.loads(cache_data)
            if not dispatch_rule:
                return None
            return dispatch_rule
        except KeyError:
            dispatch_rule = copy.deepcopy(DISPATCH_RULE.get(domain))
            if not dispatch_rule:
                return None
            for _rule in dispatch_rule:
                _expr_list = _rule[1]
                _new_expr_list = []
                for _expr_id in _expr_list:
                    _expr = EXPR_MAP.get(_expr_id)
                    if _expr is None:
                        continue
                    _new_expr_list.append(_expr)
                _rule[1] = _new_expr_list 
            return dispatch_rule

    @classmethod
    def set_dispatch_rule_cache(cls, domain, dispatch_rule):
        """
        set domain dispatch rule
        :param domain:
        :param dispatch_rule: it must be a dict object
        :return: boolean(Always return True)
        """
        cache_conn = cls._get_cache_conn_(domain)
        cache_key = cls._get_dispatch_rule_cache_key_(domain)
        cache_data = json.dumps(dispatch_rule)
        cache_conn.Put(cache_key, cache_data)
        return True

    @classmethod
    def del_dispatch_rule_cache(cls, domain):
        """
        delete domain dispatch rule
        :param domain:
        :return: boolean(Always return True)
        """
        cache_conn = cls._get_cache_conn_(domain)
        cache_key = cls._get_dispatch_rule_cache_key_(domain)
        try:
            cache_conn.Delete(cache_key)
        except:
            return True

    @classmethod
    def _get_cache_conn_(cls, domain):
        """
        get cache db operator obj, default is level db obj.
        if you want to custom you own cache db obj, rewrite it and return you own cache db obj
        cache db obj must define the following method:
            class method -> Put(key, value)         # set value by key, return True or False
            class method -> Get(key, value)         # get value by key, return str
            class method -> Delete(key, value)      # del value by key, return True or False
            class method -> RangeIter()             # get all key and value, return [(key, value), ...]
        :param domain:
        :return: obj
        """
        cache_conn = cls.CACHE_CONN_MAP.get(domain)
        if cache_conn is not None:
            return cache_conn
        if not domain:
            raise ValueError
        if not os.path.exists(DB_PATH):
            os.mkdir(DB_PATH)
        cache_conn = leveldb.LevelDB(DB_PATH + "/" + domain)
        cls.CACHE_CONN_MAP[domain] = cache_conn
        return cache_conn

    @classmethod
    def _get_resolve_cache_key_(cls, domain, client_ip):
        """
        get domain resolve cache key for save
        :param domain:
        :param client_ip:
        :return: str
        """
        return "resolve_cache$%s$%s" % (domain, client_ip)

    @classmethod
    def _get_dispatch_rule_cache_key_(cls, domain):
        """
        get domain dispatch rule cache key for save
        :param domain:
        :return: str
        """
        return "dispatch_rule$%s" % domain
