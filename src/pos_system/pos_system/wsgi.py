"""
WSGI config for pos_system project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_system.settings')

application = get_wsgi_application()

# 启动定时备份调度器
try:
    from system.backup_scheduler import backup_scheduler
    backup_scheduler.start()
except Exception as e:
    print(f"启动备份调度器失败: {str(e)}")
