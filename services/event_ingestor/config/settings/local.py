from .base import *

DEBUG = True

SHELL_PLUS = "ipython"
SHELL_PLUS_PRINT_SQL = True
if DEBUG:
    INSTALLED_APPS.append("django_extensions")