"""Static files storage."""
import posixpath

from whitenoise.storage import CompressedManifestStaticFilesStorage


class ManifestStaticStorage(CompressedManifestStaticFilesStorage):
    """WhiteNoise's hashed, compressed storage, but a folder path such as
    {% static 'vendor/bootswatch' %} (used by the Jazzmin admin theme) gets
    its plain URL instead of raising "Missing staticfiles manifest entry".
    Missing *files* still raise, as before."""

    def stored_name(self, name):
        try:
            return super().stored_name(name)
        except ValueError:
            if not posixpath.splitext(name.rstrip("/"))[1]:
                return name
            raise
