from rest_framework import serializers

from formshare.apps.logger.models import Note


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
