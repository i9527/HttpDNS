# -*- coding: UTF-8 -*-

import os
import time
import json
import copy

import leveldb
from httpdns.config import DISPATCH_RULE, EXPR_MAP, DB_PATH, DEFAULT_DOMAIN_CACHE_TTL


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
        finally:
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
