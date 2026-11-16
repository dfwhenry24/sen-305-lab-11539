from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from requests_app.models import Category, ServiceRequest, WorkOrder


class WorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", password="pass12345")
        self.staff = User.objects.create_user("staff", password="pass12345", is_staff=True)
        self.tech = User.objects.create_user("tech", password="pass12345", is_staff=True)
        self.category = Category.objects.create(name="Facilities")
        self.item = ServiceRequest.objects.create(
            requester=self.owner, category=self.category,
            title="Projector does not display",
            description="The projector reports no HDMI signal.",
            location="Room B12", priority=3,
        )

    def test_non_staff_assignment_returns_403_and_creates_no_work_order(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("requests:assign", args=[self.item.id]),
            {"technician": self.tech.id},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(WorkOrder.objects.count(), 0)

    def test_staff_assignment_creates_one_work_order_and_sets_assigned(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("requests:assign", args=[self.item.id]),
            {"technician": self.tech.id},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(WorkOrder.objects.filter(service_request=self.item).count(), 1)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, ServiceRequest.Status.ASSIGNED)

    def test_resolution_without_assignment_leaves_request_unchanged(self):
        self.client.force_login(self.staff)
        self.client.post(
            reverse("requests:resolve", args=[self.item.id]),
            {"work_notes": "Replaced the cable."},
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, ServiceRequest.Status.OPEN)
        self.assertIsNone(self.item.resolved_at)
        self.assertEqual(WorkOrder.objects.count(), 0)

    def test_assigned_technician_resolution_changes_both_models(self):
        work_order = WorkOrder.objects.create(service_request=self.item, technician=self.tech)
        self.item.status = ServiceRequest.Status.ASSIGNED
        self.item.save(update_fields=["status", "updated_at"])

        self.client.force_login(self.tech)
        response = self.client.post(
            reverse("requests:resolve", args=[self.item.id]),
            {"work_notes": "Replaced the HDMI cable."},
        )
        self.assertEqual(response.status_code, 302)

        self.item.refresh_from_db()
        work_order.refresh_from_db()
        self.assertEqual(self.item.status, ServiceRequest.Status.RESOLVED)
        self.assertIsNotNone(self.item.resolved_at)
        self.assertEqual(work_order.work_notes, "Replaced the HDMI cable.")
        self.assertIsNotNone(work_order.completed_at)


class PaginationFilterTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user("owner", password="pass12345")
        category = Category.objects.create(name="ICT Support")
        for i in range(12):
            ServiceRequest.objects.create(
                requester=self.owner, category=category,
                title=f"Printer fault number {i}",
                description="Paper jam.", location="Lab", priority=3,
            )

    def test_filtered_pagination_preserves_q_and_status(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("requests:list"), {"q": "Printer", "status": "open"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "q=Printer&amp;status=open&page=2")

        page2 = self.client.get(
            reverse("requests:list"), {"q": "Printer", "status": "open", "page": 2}
        )
        self.assertEqual(page2.status_code, 200)
        self.assertEqual(page2.context["query"], "Printer")
        self.assertEqual(page2.context["selected_status"], "open")
        self.assertEqual(len(page2.context["page_obj"]), 2)