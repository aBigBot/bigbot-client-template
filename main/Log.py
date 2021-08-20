from colorit import *
from django.conf import settings


init_colorit()


def debug(tag, *args):
    if settings.DEBUG:
        args = ", ".join([str(item) for item in args])
        print(color(f"{tag}: {args}", Colors.blue))


def error(tag, *args):
    args = ", ".join([str(item) for item in args])
    print(color(f"{tag}: {args}", Colors.red))


def info(tag, *args):
    args = ", ".join([str(item) for item in args])
    print(color(f"{tag}: {args}", Colors.purple))


def message(tag, *args, green=False):
    args = ", ".join([str(item) for item in args])
    if green:
        print(background(f"{tag}: {args}", Colors.green))
    else:
        print(background(f"{tag}: {args}", Colors.red))


def warning(tag, *args):
    args = ", ".join([str(item) for item in args])
    print(color(f"{tag}: {args}", Colors.orange))
