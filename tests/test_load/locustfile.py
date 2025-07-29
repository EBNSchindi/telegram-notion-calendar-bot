"""
Load tests for concurrent user scenarios using Locust.
"""
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import StatsCSVFileWriter
import json
import random
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramBotUser(HttpUser):
    """Simulates a Telegram user interacting with the bot."""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Initialize user session."""
        self.user_id = random.randint(100000, 999999)
        self.appointments = []
        self.memos = []
        logger.info(f"User {self.user_id} started")
    
    @task(3)
    def create_appointment(self):
        """Create a new appointment."""
        appointment_texts = [
            "Meeting with team at 3pm",
            "Doctor appointment tomorrow at 10:30am",
            "Lunch with client next Tuesday at 12:30pm",
            "Project review on Friday at 2pm",
            "Conference call at 4:30pm EST"
        ]
        
        payload = {
            "update_id": random.randint(1, 999999),
            "message": {
                "message_id": random.randint(1, 999999),
                "from": {
                    "id": self.user_id,
                    "first_name": f"User{self.user_id}"
                },
                "text": f"/new {random.choice(appointment_texts)}",
                "date": int(datetime.now().timestamp())
            }
        }
        
        with self.client.post("/webhook", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                self.appointments.append({
                    "created_at": datetime.now(),
                    "text": payload["message"]["text"]
                })
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(5)
    def list_appointments(self):
        """List user's appointments."""
        payload = {
            "update_id": random.randint(1, 999999),
            "message": {
                "message_id": random.randint(1, 999999),
                "from": {
                    "id": self.user_id,
                    "first_name": f"User{self.user_id}"
                },
                "text": "/list",
                "date": int(datetime.now().timestamp())
            }
        }
        
        with self.client.post("/webhook", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(2)
    def check_today_appointments(self):
        """Check today's appointments."""
        payload = {
            "update_id": random.randint(1, 999999),
            "message": {
                "message_id": random.randint(1, 999999),
                "from": {
                    "id": self.user_id,
                    "first_name": f"User{self.user_id}"
                },
                "text": "/today",
                "date": int(datetime.now().timestamp())
            }
        }
        
        with self.client.post("/webhook", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(2)
    def create_memo(self):
        """Create a new memo."""
        memo_texts = [
            "Remember to buy groceries",
            "Project idea: AI-powered calendar",
            "Important: Call mom on weekend",
            "TODO: Review pull requests",
            "Note: Update documentation"
        ]
        
        payload = {
            "update_id": random.randint(1, 999999),
            "message": {
                "message_id": random.randint(1, 999999),
                "from": {
                    "id": self.user_id,
                    "first_name": f"User{self.user_id}"
                },
                "text": f"/memo {random.choice(memo_texts)}",
                "date": int(datetime.now().timestamp())
            }
        }
        
        with self.client.post("/webhook", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                self.memos.append({
                    "created_at": datetime.now(),
                    "text": payload["message"]["text"]
                })
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(1)
    def search_appointments(self):
        """Search for appointments."""
        search_terms = ["meeting", "doctor", "lunch", "call", "review"]
        
        payload = {
            "update_id": random.randint(1, 999999),
            "message": {
                "message_id": random.randint(1, 999999),
                "from": {
                    "id": self.user_id,
                    "first_name": f"User{self.user_id}"
                },
                "text": f"/search {random.choice(search_terms)}",
                "date": int(datetime.now().timestamp())
            }
        }
        
        with self.client.post("/webhook", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(1)
    def handle_callback_query(self):
        """Simulate button clicks (callback queries)."""
        if self.appointments:
            # Simulate deleting an appointment
            payload = {
                "update_id": random.randint(1, 999999),
                "callback_query": {
                    "id": str(random.randint(1, 999999)),
                    "from": {
                        "id": self.user_id,
                        "first_name": f"User{self.user_id}"
                    },
                    "data": f"delete_appointment:app_{random.randint(1, 100)}"
                }
            }
            
            with self.client.post("/webhook", json=payload, catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Got status code {response.status_code}")
    
    def on_stop(self):
        """Clean up user session."""
        logger.info(f"User {self.user_id} finished. Created {len(self.appointments)} appointments and {len(self.memos)} memos")


class PowerUser(TelegramBotUser):
    """Simulates a power user with more frequent interactions."""
    
    wait_time = between(0.5, 2)  # Faster interactions
    
    @task(10)
    def rapid_appointment_creation(self):
        """Create appointments rapidly."""
        for _ in range(5):
            self.create_appointment()


class APIStressTest(HttpUser):
    """Direct API stress testing."""
    
    wait_time = between(0.1, 0.5)  # Very fast requests
    host = "http://localhost:8000"  # Adjust to your API endpoint
    
    @task
    def stress_notion_api(self):
        """Stress test Notion API integration."""
        headers = {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json"
        }
        
        # Simulate direct API call
        payload = {
            "user_id": random.randint(100000, 999999),
            "action": "query_appointments",
            "date_range": "week"
        }
        
        with self.client.post("/api/appointments", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # Rate limited
                response.failure("Rate limited")
            else:
                response.failure(f"Got status code {response.status_code}")


# Custom event handlers for detailed metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test metrics."""
    logger.info("Load test starting...")
    logger.info(f"Target host: {environment.host}")
    logger.info(f"Total users: {environment.parsed_options.num_users}")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log detailed request metrics."""
    if exception:
        logger.error(f"Request failed: {name} - {exception}")
    elif response_time > 5000:  # Log slow requests (>5s)
        logger.warning(f"Slow request: {name} - {response_time}ms")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate final test report."""
    logger.info("Load test completed!")
    
    # Calculate statistics
    stats = environment.stats
    
    logger.info("\n=== Load Test Summary ===")
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Failed requests: {stats.total.num_failures}")
    logger.info(f"Median response time: {stats.total.median_response_time}ms")
    logger.info(f"95th percentile: {stats.total.get_response_time_percentile(0.95)}ms")
    logger.info(f"99th percentile: {stats.total.get_response_time_percentile(0.99)}ms")
    
    # Save detailed stats to CSV
    csv_writer = StatsCSVFileWriter(
        environment,
        stats_base_filepath="load_test_results",
        full_history=True
    )


# Scenario-based load testing
class ScenarioUser(HttpUser):
    """User following specific scenarios."""
    
    wait_time = between(2, 5)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scenario = random.choice([
            self.morning_routine,
            self.business_day,
            self.weekend_planning
        ])
    
    @task
    def execute_scenario(self):
        """Execute the selected scenario."""
        self.scenario()
    
    def morning_routine(self):
        """Simulate morning routine scenario."""
        # Check today's appointments
        self.check_today_appointments()
        
        # Add a new appointment
        self.create_appointment()
        
        # Check reminders
        self.list_appointments()
    
    def business_day(self):
        """Simulate business day scenario."""
        # Multiple appointment creations
        for _ in range(3):
            self.create_appointment()
        
        # Search for specific appointments
        self.search_appointments()
        
        # Create work memos
        for _ in range(2):
            self.create_memo()
    
    def weekend_planning(self):
        """Simulate weekend planning scenario."""
        # Check next week
        payload = {
            "update_id": random.randint(1, 999999),
            "message": {
                "message_id": random.randint(1, 999999),
                "from": {
                    "id": self.user_id,
                    "first_name": f"User{self.user_id}"
                },
                "text": "/week",
                "date": int(datetime.now().timestamp())
            }
        }
        
        self.client.post("/webhook", json=payload)
        
        # Plan activities
        weekend_activities = [
            "Hiking on Saturday at 9am",
            "Dinner with friends on Saturday at 7pm",
            "Movie on Sunday at 3pm"
        ]
        
        for activity in weekend_activities:
            payload["message"]["text"] = f"/new {activity}"
            self.client.post("/webhook", json=payload)