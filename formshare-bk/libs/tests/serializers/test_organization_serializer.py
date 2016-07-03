from django.test import TransactionTestCase

from formshare.libs.serializers.organization_serializer import\
    OrganizationSerializer


class TestOrganizationSerializer(TransactionTestCase):

    def setUp(self):
        self.serializer = OrganizationSerializer()

    def test_get_org_permissions_none(self):
        perms = self.serializer.get_org_permissions(None)
        self.assertEqual(perms, [])
