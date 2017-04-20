"""
Bloc twisted application plugins.
"""
from twisted.application.service import ServiceMaker


blocService = ServiceMaker(
    "bloc Service/",
    "bloc.tap",
    "Single master group membership server",
    "bloc")
