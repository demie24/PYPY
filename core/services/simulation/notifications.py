# core/services/simulation/notifications.py

import os
import logging
from services.email.email_service import get_email_provider

logger = logging.getLogger("services.simulation.notifications")

EMAILS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../emails"))

def send_simulation_email(to_email: str, template_name: str, subject: str, variables: dict):
    try:
        path = os.path.join(EMAILS_DIR, template_name)
        if os.path.exists(path):
            with open(path, "r") as f:
                html_body = f.read()
            for k, v in variables.items():
                html_body = html_body.replace(f"{{{k}}}", str(v))
        else:
            logger.warning(f"Email template {template_name} not found. Fallback plain body.")
            html_body = f"Simulation update details: {variables}"
            
        plain_body = f"{subject}\n\nVariables: {variables}"
        
        provider = get_email_provider()
        provider.send_email(to_email, subject, plain_body, html_body)
    except Exception as e:
        logger.error(f"Failed to dispatch simulation notification email: {e}")
