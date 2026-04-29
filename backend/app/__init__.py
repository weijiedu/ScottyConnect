import os
from typing import Any

from flask import Flask
from flask_cors import CORS
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from dotenv import load_dotenv

from app.accounts.service import ACCOUNT_SERVICE_EXTENSION_KEY, AccountService
from app.attendance.service import ATTENDANCE_SERVICE_EXTENSION_KEY, AttendanceService
from app.feedback.service import FEEDBACK_SERVICE_EXTENSION_KEY, FeedbackService
from app.recommendation.service import RECOMMENDATION_SERVICE_EXTENSION_KEY, RecommendationService
from app.lifecycle.service import LIFECYCLE_SERVICE_EXTENSION_KEY, LifecycleService
from app.tasks.service import TASKS_SERVICE_EXTENSION_KEY, TasksService
from app.networking.service import NETWORKING_SERVICE_EXTENSION_KEY, NetworkingService
from app.notification.service import NOTIFICATION_SERVICE_EXTENSION_KEY, NotificationService




def create_app():
    load_dotenv()
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[
            FlaskIntegration(),
            LoggingIntegration(level=20, event_level=40),
        ],
        # Prefer explicit user context over default PII collection in auth-heavy APIs.
        send_default_pii=False,
        environment=os.getenv("NODE_ENV"),
        max_breadcrumbs=100,
        attach_stacktrace=True,
    )

    app = Flask(__name__)
    CORS(app)

    # Register each service as an extension for subscriber-publisher pattern
    app.extensions[ACCOUNT_SERVICE_EXTENSION_KEY] = AccountService()
    app.extensions[RECOMMENDATION_SERVICE_EXTENSION_KEY] = RecommendationService()
    app.extensions[ATTENDANCE_SERVICE_EXTENSION_KEY] = AttendanceService()
    app.extensions[FEEDBACK_SERVICE_EXTENSION_KEY] = FeedbackService()
    app.extensions[NOTIFICATION_SERVICE_EXTENSION_KEY] = NotificationService()
    app.extensions[LIFECYCLE_SERVICE_EXTENSION_KEY] = LifecycleService()
    app.extensions[NETWORKING_SERVICE_EXTENSION_KEY] = NetworkingService()
    app.extensions[TASKS_SERVICE_EXTENSION_KEY] = TasksService()


    from .routes import main

    app.register_blueprint(main)

    return app