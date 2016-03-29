# -*- coding: UTF-8 -*-

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from httpdns.resolver import DNSResolver


@csrf_exempt
def resolve(request):
    if "HTTP_X_FORWARDED_FOR" in request.META:
        _client_ip = request.META["HTTP_X_FORWARDED_FOR"]
    else:
        _client_ip = request.META["REMOTE_ADDR"]
    domain = request.GET.get("domain")
    client_ip = request.GET.get("client_ip") or _client_ip
    ttl = request.GET.get("ttl")
    client_extra_info = request.GET.dict()
    client_extra_info.update(request.META)
    return HttpResponse(DNSResolver(domain, client_ip, client_extra_info, ttl).resolve())
