import argparse
import logging
import os

from app import create_app
from app.notification.service import NOTIFICATION_SERVICE_EXTENSION_KEY

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ScottyConnect backend server")
    parser.add_argument(
        "--info",
        action="store_true",
        help="Enable INFO level logging",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host interface to bind the web server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "5000")),
        help="Port to bind the web server",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable Flask debug mode",
    )
    return parser.parse_args()


def _configure_logging(enable_info: bool) -> None:
    level = logging.INFO if enable_info else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


if __name__ == "__main__":
    args = _parse_args()
    _configure_logging(args.info)
    app = create_app()
    is_reloader_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    should_start_worker = (not args.debug) or is_reloader_child
    if should_start_worker:
        app.extensions[NOTIFICATION_SERVICE_EXTENSION_KEY].start_worker()
    app.run(debug=args.debug, host=args.host, port=args.port)