from rest_framework import serializers
from formshare.apps.logger.models import XForm


class XFormField(serializers.WritableField):
    def to_native(self, obj):
        return obj.pk

    def from_native(self, data):
        return XForm.objects.get(pk=data)
