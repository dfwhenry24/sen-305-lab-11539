from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from requests_app.models import Category, ServiceRequest

class ServiceRequestCrudTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", password="pass12345")
        self.other = User.objects.create_user("other", password="pass12345")
        self.category = Category.objects.create(name="Facilities")
        self.item = ServiceRequest.objects.create(
            requester=self.owner, category=self.category,
            title="Projector does not display",
            description="The projector reports no HDMI signal.",
            location="Room B12", priority=3,
        )
    
    def test_list_requires_login(self):
        response = self.client.get(reverse("requests:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
    
    def test_owner_can_open_detail(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("requests:detail", args=[self.item.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.item.title)
    
    def test_other_requester_receives_404(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("requests:detail", args=[self.item.id]))
        self.assertEqual(response.status_code, 404)
    
    def test_valid_post_creates_request_for_logged_in_user(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("requests:create"), {
            "category": self.category.id,
            "title": "Air conditioner leaks water",
            "description": "Water drips near the laboratory entrance.",
            "location": "Software Laboratory", "priority": 4,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ServiceRequest.objects.filter(
            requester=self.owner, title="Air conditioner leaks water"
        ).exists())
    
    def test_invalid_post_does_not_create_request(self):
        self.client.force_login(self.owner)
        before = ServiceRequest.objects.count()
        response = self.client.post(reverse("requests:create"), {
            "category": self.category.id, "title": "Short",
            "description": "", "location": "", "priority": 4,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ServiceRequest.objects.count(), before)
        self.assertContains(response, "Use at least 8 characters.")