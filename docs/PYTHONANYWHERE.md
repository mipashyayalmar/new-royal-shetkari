# Running Royal Shetkari POS on PythonAnywhere

A test copy of the POS on a free PythonAnywhere account, for example
`https://royalhotel.pythonanywhere.com`. It's for trying the software, not for the
restaurant's real billing. A free account has 100 CPU-seconds a day for consoles and
tasks, 512 MB of disk, and limited outgoing internet.

## Files

- `requirements-pythonanywhere.txt`: the packages the POS needs, without the optional
  cloud, AI, Twilio, PostgreSQL and Windows packages.
- `scripts/pythonanywhere/deploy.sh`: unpacks a release, creates the virtualenv
  (`~/.virtualenvs/royal-shetkari`), installs packages, backs up the database, migrates
  and collects static files.
- `scripts/pythonanywhere/wsgi.py`: the web app's WSGI file.

## Settings (`~/royal-shetkari/.env`, never committed)

```
LOCAL_INSTALL=True
DEBUG=False
SECRET_KEY=<new random value>
FIELD_ENCRYPTION_KEY=<the same key as the database it came from>
ALLOWED_HOSTS=royalhotel.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://royalhotel.pythonanywhere.com
BASE_URL=https://royalhotel.pythonanywhere.com
DB_CONN_MAX_AGE=0
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
PUBLIC_WEBSITE=True
CANONICAL_HOST=royalhotel.pythonanywhere.com
```

`PUBLIC_WEBSITE=True` shows the public business website and policy pages (`core/website.py`)
at `/` instead of sending visitors to login; `CANONICAL_HOST` lets search engines and
Razorpay's website check index those pages.

`FIELD_ENCRYPTION_KEY` must match the key the database was created with, or saved
payment secrets can't be read.

## Web tab

- Source code: `/home/<user>/royal-shetkari`
- Virtualenv: `/home/<user>/.virtualenvs/royal-shetkari`, Python 3.13
- Static files: `/static/` → `/home/<user>/royal-shetkari/staticfiles`,
  `/media/` → `/home/<user>/royal-shetkari/media`
- WSGI file: the contents of `scripts/pythonanywhere/wsgi.py`
- Force HTTPS: on

## Updating

1. Build a release zip (`git archive -o royal_shetkari_release.zip HEAD`). Add
   `db.sqlite3` and `media/` only when you want to replace the online data.
2. Upload it to the home directory (Files tab).
3. In a Bash console: `bash ~/royal-shetkari/scripts/pythonanywhere/deploy.sh`.
4. Press **Reload** on the Web tab.

### Small updates through the API

For template or static-file changes (no new packages, no migrations), skip the zip:
upload each changed file with the Files API and reload the web app. Create the API token
on the Account page (API token tab) and keep it in an environment variable, never in git.

```bash
B=https://www.pythonanywhere.com/api/v0/user/Royalhotel
R=/home/Royalhotel/royal-shetkari
curl -H "Authorization: Token $PA_TOKEN" -F "content=@templates/core/base.html"      "$B/files/path$R/templates/core/base.html"
# static files go to both static/ and staticfiles/ (the folder that's served)
curl -X POST -H "Authorization: Token $PA_TOKEN" "$B/webapps/royalhotel.pythonanywhere.com/reload/"
```

## Installing on phones

The site is an installable web app. On Android open it in Chrome and tap **Install App**
under Sign In, or use **⋮ > Install app**. The manifest is `templates/manifest.json`, the
icons are in `static/icons/`, and the service worker is `static/sw.js`.

## Before anyone outside the team uses it

- Give every account its own strong password (Setup > Staff). The superuser accounts
  can open `/admin/`.
- The QR shown for UPI payments is the restaurant's real PhonePe QR, so test payments
  move real money. The POS never marks a QR payment paid by itself.
