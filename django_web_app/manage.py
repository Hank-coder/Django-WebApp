#!/usr/bin/env python

import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_web_app.settings')

    # 如果只提供了脚本名称（例如，执行“python manage.py”而没有其他参数）
    # 则默认添加 'runserver' 作为参数
    if len(sys.argv) == 1:
        sys.argv.append('runserver 0.0.0.0:8000')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
