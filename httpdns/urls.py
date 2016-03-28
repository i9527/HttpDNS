# -*- coding: UTF-8 -*-

from django.conf.urls import url
from views import resolve

urlpatterns = [
    url(r'^resolve', resolve),
]
