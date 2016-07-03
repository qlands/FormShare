from rest_framework import viewsets

from formshare.apps.api.permissions import XFormPermissions
from formshare.apps.logger.models.xform import XForm

from formshare.libs import filters
from formshare.libs.mixins.anonymous_user_public_forms_mixin import (
    AnonymousUserPublicFormsMixin)
from formshare.libs.mixins.last_modified_mixin import LastModifiedMixin
from formshare.libs.serializers.stats_serializer import (
    StatsSerializer, StatsInstanceSerializer)


class StatsViewSet(LastModifiedMixin,
                   AnonymousUserPublicFormsMixin,
                   viewsets.ReadOnlyModelViewSet):

    """
Stats summary for median, mean, mode, range, max, min.
A query parameter `method` can be used to limit the results to either
`mean`, `median`, `mode` or `range` only results.

Example:

    GET /api/v1/stats/1?

Response:

    [
        {
            "age":
                {
                    "median": 8,
                    "mean": 23.4,
                    "mode": 23,
                    "range": 24,
                    "max": 28,
                    "min": 4
                },
        ...
    ]

Example:

    GET /api/v1/stats/1?method=median

Response:

    [
        {
            "age":
                {
                    "median": 8,
                },
        ...
    ]
"""
    lookup_field = 'pk'
    queryset = XForm.objects.all()
    filter_backends = (filters.AnonDjangoObjectPermissionFilter, )
    permission_classes = [XFormPermissions, ]
    serializer_class = StatsSerializer

    def get_serializer_class(self):
        lookup = self.kwargs.get(self.lookup_field)
        if lookup is not None:
            serializer_class = StatsInstanceSerializer
        else:
            serializer_class = \
                super(StatsViewSet, self).get_serializer_class()

        return serializer_class
