# -*- coding: UTF-8 -*-

import re
import json
import urllib

import requests
import pyDes

from httpdns.cache_controller import CacheController
from httpdns.config import BACKUP_IP_LIST, D_PLUS_ID, D_PLUS_SECRET, D_PLUS_ENTERPRISE_VERSION


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
        finally:
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
        finally:
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
        finally:
            return status
