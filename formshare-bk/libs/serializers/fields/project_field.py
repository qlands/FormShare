from rest_framework import serializers
from formshare.apps.logger.models.project import Project


class ProjectField(serializers.WritableField):
    def to_native(self, obj):
        return obj.pk

    def from_native(self, data):
        return Project.objects.get(pk=data)
