"""
DemoRecord: the list of every row `manage.py seed_royal_shetkari` created.

The seed never edits or deletes anything that is not on this list, so the
restaurant's real data (orders taken, dishes added or repriced by the owner)
is never touched by re-running the seed or by --reset-demo.
"""
from django.contrib.contenttypes.models import ContentType
from django.db import models


class DemoRecord(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64)
    # Which part of the seed made it: "setup" (restaurant, staff, menu, tables,
    # stock items...) or "history" (orders, payments, purchases, shifts...).
    kind = models.CharField(max_length=20, default="history")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["content_type", "object_id"], name="unique_demo_record"),
        ]
        indexes = [models.Index(fields=["content_type", "kind"])]

    def __str__(self):
        return f"demo {self.content_type.model} #{self.object_id}"

    @classmethod
    def ids_for(cls, model, kind=None):
        qs = cls.objects.filter(content_type=ContentType.objects.get_for_model(model))
        if kind:
            qs = qs.filter(kind=kind)
        return [int(i) if i.isdigit() else i for i in qs.values_list("object_id", flat=True)]
