# -*- coding: UTF-8 -*-

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from httpdns.utils import get_request_ip
from httpdns.resolver import DNSResolver


@csrf_exempt
def resolve(request):
    domain = request.GET.get("domain")
    client_ip = request.GET.get("client_ip") or get_request_ip(request)
    ttl = request.GET.get("ttl")
    client_extra_info = request.GET.dict()
    client_extra_info.update(request.META)
    return HttpResponse(DNSResolver(domain, client_ip, client_extra_info, ttl).resolve())
