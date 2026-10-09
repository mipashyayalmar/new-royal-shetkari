# PythonAnywhere WSGI file for Royal Shetkari POS.
# Copy into the web app's WSGI file (Web tab > WSGI configuration file).
# Settings come from ~/royal-shetkari/.env (see docs/PYTHONANYWHERE.md).
import os
import sys

APP = os.path.expanduser("~/royal-shetkari")
if APP not in sys.path:
    sys.path.insert(0, APP)
os.chdir(APP)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
