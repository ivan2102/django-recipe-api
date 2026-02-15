""""
Test tags API.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status # pyright: ignore[reportMissingImports]
from rest_framework.test import APIClient # pyright: ignore[reportMissingImports]

from core.models import Tag, Recipe
from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')

def detail_url(tag_id):
    """Create and return a tag detail url."""
    return reverse('recipe:tag-detail', args=[tag_id])

def create_user(email='user@example.com', password='testpass123'):
    """Create user."""
    return get_user_model().objects.create_user(email=email, password=password)


class PublicTagsApiTest(TestCase):
    """Test unauthenticated users API requests."""
    
    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """Test login is required for retrieving tags."""

        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTest(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieving a list of tags."""

        Tag.objects.create(user=self.user, name='Dinner')
        Tag.objects.create(user=self.user, name='Cook')

        response = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)


    def test_tags_authenticated_user(self):
        """"Test list of tags authenticated user."""

        user2 = create_user(email='user2@example.com')
        Tag.objects.create(user=user2, name='Tacos')
        tag = Tag.objects.create(user=self.user, name='Veggie-forward')

        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], tag.name)
        self.assertEqual(response.data[0]['id'], tag.id)


    def test_update_tag(self):
        """"Test update the tag."""
        tag = Tag.objects.create(user=self.user, name='Late Dinner')

        payload = {'name': 'Dessert'}
        url = detail_url(tag.id)
        response = self.client.patch(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])


    def test_delete_tag(self):
        """Test deleteing a tag."""
        tag = Tag.objects.create(user=self.user, name='Lanch')

        url = detail_url(tag.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        tag = Tag.objects.filter(user=self.user)
        self.assertFalse(tag.exists())

    def test_filter_tags_assigned_to_recipes(self):
        """Test listing tags assigned to recipes."""
        tag1 = Tag.objects.create(user=self.user, name='Breakfast')
        tag2 = Tag.objects.create(user=self.user, name='Lunch')
        recipe = Recipe.objects.create(
            title='Sweet potatoes',
            time_minutes=40,
            price=Decimal('5.50'),
            user=self.user
        )

        recipe.tags.add(tag1)
        response = self.client.get(TAGS_URL, {'assigned_only': 1})

        serializer1 = TagSerializer(tag1)
        serializer2 = TagSerializer(tag2)
        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)


    def test_filtered_tags_unique(self):
        """Test filtered tags returns a unique list."""
        tag = Tag.objects.create(user=self.user, name='Breakfast')
        Tag.objects.create(user=self.user, name='Dinner')
        recipe1 = Recipe.objects.create(
            title='Pancakes',
            time_minutes=5,
            price=Decimal('3.00'),
            user=self.user
        )

        recipe2 = Recipe.objects.create(
            title='Bacon Eggs Cheese Biscuit',
            time_minutes=50,
            price=Decimal('6.99'),
            user=self.user
        )

        recipe1.tags.add(tag)
        recipe2.tags.add(tag)

        response = self.client.get(TAGS_URL, {'assigned_only': 1})
        self.assertEqual(len(response.data), 1)