"""Load Testing with Locust

This module provides load testing scenarios for the Customer Success API
using Locust framework.

Run with:
    locust -f tests/load_test.py --host=http://localhost:8000
"""

import random
import json
from datetime import datetime
from typing import Dict, Any

from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask


# ============================================================================
# Test Data Generators
# ============================================================================

class TestDataGenerator:
    """Generate realistic test data for load testing."""

    FIRST_NAMES = [
        "John", "Jane", "Michael", "Sarah", "David", "Emily",
        "Robert", "Lisa", "James", "Maria", "William", "Jennifer"
    ]

    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
        "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez"
    ]

    COMPANIES = [
        "Acme Corp", "TechStart Inc", "Global Solutions", "Innovation Labs",
        "Digital Ventures", "Cloud Systems", "Data Dynamics", "Smart Tech"
    ]

    SUBJECTS = [
        "Unable to login to my account",
        "Payment processing issue",
        "Feature request: Dark mode",
        "Data export not working",
        "Account upgrade question",
        "Integration with third-party service",
        "Performance issues with dashboard",
        "Password reset not working",
        "Billing inquiry",
        "API rate limit question"
    ]

    MESSAGES = [
        "I'm experiencing issues with {feature}. Can you help me resolve this?",
        "I've been trying to {action} but keep getting an error. What should I do?",
        "Could you please assist me with {feature}? It's not working as expected.",
        "I need help with {action}. I've tried multiple times but no success.",
        "Is there a way to {action}? I can't find the option in the dashboard.",
        "I'm getting a timeout error when trying to {action}. Please advise.",
        "The {feature} feature seems to be broken. Can you look into this?",
        "I would like to request support for {action}. Is this possible?",
        "Having trouble with {feature}. This is urgent, please help!",
        "Quick question about {feature} - how do I configure this properly?"
    ]

    FEATURES = [
        "data export", "user management", "API integration", "reporting dashboard",
        "payment processing", "email notifications", "file uploads", "search functionality"
    ]

    ACTIONS = [
        "export my data", "update my profile", "integrate with Slack",
        "generate reports", "process payments", "upload files", "search records"
    ]

    CATEGORIES = ["technical", "billing", "feature_request", "account", "general"]

    @staticmethod
    def generate_customer_name() -> str:
        """Generate random customer name."""
        first = random.choice(TestDataGenerator.FIRST_NAMES)
        last = random.choice(TestDataGenerator.LAST_NAMES)
        return f"{first} {last}"

    @staticmethod
    def generate_email() -> str:
        """Generate random email address."""
        timestamp = int(datetime.now().timestamp() * 1000)
        random_num = random.randint(1000, 9999)
        return f"loadtest_{timestamp}_{random_num}@example.com"

    @staticmethod
    def generate_phone() -> str:
        """Generate random phone number."""
        return f"+1555{random.randint(1000000, 9999999)}"

    @staticmethod
    def generate_company() -> str:
        """Generate random company name."""
        return random.choice(TestDataGenerator.COMPANIES)

    @staticmethod
    def generate_subject() -> str:
        """Generate random support subject."""
        return random.choice(TestDataGenerator.SUBJECTS)

    @staticmethod
    def generate_message() -> str:
        """Generate random support message."""
        template = random.choice(TestDataGenerator.MESSAGES)
        feature = random.choice(TestDataGenerator.FEATURES)
        action = random.choice(TestDataGenerator.ACTIONS)
        return template.format(feature=feature, action=action)

    @staticmethod
    def generate_category() -> str:
        """Generate random category."""
        return random.choice(TestDataGenerator.CATEGORIES)

    @staticmethod
    def generate_support_request() -> Dict[str, Any]:
        """Generate complete support request."""
        return {
            "name": TestDataGenerator.generate_customer_name(),
            "email": TestDataGenerator.generate_email(),
            "subject": TestDataGenerator.generate_subject(),
            "message": TestDataGenerator.generate_message(),
            "category": TestDataGenerator.generate_category(),
            "phone": TestDataGenerator.generate_phone(),
            "company": TestDataGenerator.generate_company()
        }


# ============================================================================
# Web Form User
# ============================================================================

class WebFormUser(HttpUser):
    """Simulates users submitting support requests via web form.

    This user:
    - Submits support requests
    - Checks ticket status
    - Lists their tickets
    - Simulates realistic user behavior with wait times
    """

    wait_time = between(5, 15)  # Wait 5-15 seconds between tasks

    def on_start(self):
        """Initialize user session."""
        self.customer_email = TestDataGenerator.generate_email()
        self.customer_name = TestDataGenerator.generate_customer_name()
        self.ticket_ids = []

    @task(10)  # Weight: 10 (most common action)
    def submit_support_request(self):
        """Submit a support request via web form."""
        request_data = TestDataGenerator.generate_support_request()

        # Use consistent email for this user
        request_data["email"] = self.customer_email
        request_data["name"] = self.customer_name

        with self.client.post(
            "/support/submit",
            json=request_data,
            catch_response=True,
            name="/support/submit"
        ) as response:
            if response.status_code == 201:
                data = response.json()
                if "ticket_id" in data:
                    self.ticket_ids.append(data["ticket_id"])
                    response.success()
                else:
                    response.failure("No ticket_id in response")
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(3)  # Weight: 3
    def check_ticket_status(self):
        """Check status of a previously created ticket."""
        if not self.ticket_ids:
            # Skip if no tickets created yet
            raise RescheduleTask()

        ticket_id = random.choice(self.ticket_ids)

        with self.client.get(
            f"/support/ticket/{ticket_id}",
            catch_response=True,
            name="/support/ticket/[id]"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "ticket_id" in data and data["ticket_id"] == ticket_id:
                    response.success()
                else:
                    response.failure("Invalid ticket data")
            elif response.status_code == 404:
                response.failure("Ticket not found")
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)  # Weight: 2
    def list_my_tickets(self):
        """List all tickets for this customer."""
        with self.client.get(
            "/support/tickets",
            params={"email": self.customer_email},
            catch_response=True,
            name="/support/tickets"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    response.success()
                else:
                    response.failure("Invalid response format")
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(1)  # Weight: 1
    def lookup_customer(self):
        """Look up customer information."""
        with self.client.get(
            "/customers/lookup",
            params={"email": self.customer_email},
            catch_response=True,
            name="/customers/lookup"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "customer_id" in data:
                    response.success()
                else:
                    response.failure("Invalid customer data")
            elif response.status_code == 404:
                # Customer might not exist yet
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


# ============================================================================
# Health Check User
# ============================================================================

class HealthCheckUser(HttpUser):
    """Simulates monitoring systems checking health endpoints.

    This user:
    - Performs frequent health checks
    - Monitors system availability
    - Simulates monitoring tools like Prometheus, Datadog, etc.
    """

    wait_time = between(1, 3)  # Check every 1-3 seconds (aggressive monitoring)

    @task(20)  # Very high weight - health checks are frequent
    def check_health(self):
        """Check system health."""
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "status" in data and data["status"] in ["healthy", "degraded"]:
                    response.success()
                else:
                    response.failure("Invalid health status")
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(5)
    def check_root(self):
        """Check root endpoint."""
        with self.client.get(
            "/",
            catch_response=True,
            name="/"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(3)
    def check_metrics(self):
        """Check metrics endpoint."""
        with self.client.get(
            "/metrics/channels",
            params={"period": "today"},
            catch_response=True,
            name="/metrics/channels"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "metrics" in data:
                    response.success()
                else:
                    response.failure("Invalid metrics data")
            else:
                response.failure(f"Got status code {response.status_code}")


# ============================================================================
# Mixed User (Realistic Behavior)
# ============================================================================

class MixedUser(HttpUser):
    """Simulates realistic mixed user behavior.

    This user performs a variety of actions with realistic patterns.
    """

    wait_time = between(3, 10)

    def on_start(self):
        """Initialize user session."""
        self.customer_email = TestDataGenerator.generate_email()
        self.customer_name = TestDataGenerator.generate_customer_name()
        self.ticket_ids = []
        self.conversation_ids = []

    @task(8)
    def submit_and_check(self):
        """Submit a request and immediately check its status."""
        # Submit request
        request_data = TestDataGenerator.generate_support_request()
        request_data["email"] = self.customer_email
        request_data["name"] = self.customer_name

        response = self.client.post("/support/submit", json=request_data)

        if response.status_code == 201:
            data = response.json()
            ticket_id = data.get("ticket_id")
            conversation_id = data.get("conversation_id")

            if ticket_id:
                self.ticket_ids.append(ticket_id)

                # Immediately check status
                self.client.get(f"/support/ticket/{ticket_id}")

            if conversation_id:
                self.conversation_ids.append(conversation_id)

    @task(2)
    def browse_conversation_history(self):
        """Browse conversation history."""
        if not self.conversation_ids:
            raise RescheduleTask()

        conversation_id = random.choice(self.conversation_ids)
        self.client.get(f"/conversations/{conversation_id}")

    @task(1)
    def check_health(self):
        """Occasionally check health."""
        self.client.get("/health")


# ============================================================================
# Event Handlers for Statistics
# ============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("=" * 80)
    print("Customer Success API Load Test Starting")
    print("=" * 80)
    print(f"Host: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    print("=" * 80)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("=" * 80)
    print("Customer Success API Load Test Complete")
    print("=" * 80)

    # Print summary statistics
    stats = environment.stats
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"Min Response Time: {stats.total.min_response_time:.2f}ms")
    print(f"Max Response Time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")
    print("=" * 80)


# ============================================================================
# Custom Load Shapes (Optional)
# ============================================================================

from locust import LoadTestShape


class StepLoadShape(LoadTestShape):
    """
    A step load shape that increases users in steps.

    Useful for finding breaking points.
    """

    step_time = 60  # Each step lasts 60 seconds
    step_load = 10  # Increase by 10 users each step
    spawn_rate = 5  # Spawn 5 users per second
    time_limit = 600  # Total test duration: 10 minutes

    def tick(self):
        """Return user count and spawn rate for current time."""
        run_time = self.get_run_time()

        if run_time > self.time_limit:
            return None

        current_step = run_time // self.step_time
        return (current_step + 1) * self.step_load, self.spawn_rate


class SpikeLoadShape(LoadTestShape):
    """
    A spike load shape that simulates traffic spikes.

    Useful for testing system resilience.
    """

    time_limit = 300  # 5 minutes total

    def tick(self):
        """Return user count and spawn rate for current time."""
        run_time = self.get_run_time()

        if run_time > self.time_limit:
            return None

        # Create spikes every 60 seconds
        if run_time % 60 < 10:
            # Spike: 100 users
            return 100, 20
        else:
            # Normal: 20 users
            return 20, 5


# ============================================================================
# Usage Instructions
# ============================================================================

"""
USAGE:

1. Basic load test with web UI:
   locust -f tests/load_test.py --host=http://localhost:8000

2. Headless mode (no web UI):
   locust -f tests/load_test.py --host=http://localhost:8000 --headless -u 50 -r 10 -t 5m

3. Test specific user class:
   locust -f tests/load_test.py --host=http://localhost:8000 WebFormUser

4. With step load shape:
   locust -f tests/load_test.py --host=http://localhost:8000 StepLoadShape

5. Generate reports:
   locust -f tests/load_test.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 10m --html=report.html --csv=results

Parameters:
  -u, --users       Number of concurrent users
  -r, --spawn-rate  Rate to spawn users (users per second)
  -t, --run-time    Test duration (e.g., 5m, 1h)
  --host            Target host URL
  --headless        Run without web UI
  --html            Generate HTML report
  --csv             Generate CSV results

Example scenarios:

1. Smoke test (light load):
   locust -f tests/load_test.py --host=http://localhost:8000 --headless -u 10 -r 2 -t 2m

2. Load test (moderate load):
   locust -f tests/load_test.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 10m

3. Stress test (heavy load):
   locust -f tests/load_test.py --host=http://localhost:8000 --headless -u 500 -r 50 -t 15m

4. Spike test:
   locust -f tests/load_test.py --host=http://localhost:8000 SpikeLoadShape

5. Endurance test (long duration):
   locust -f tests/load_test.py --host=http://localhost:8000 --headless -u 50 -r 5 -t 2h
"""
