"""Paho MQTT client construction compatible with both 1.x and 2.x."""

import paho.mqtt.client as mqtt


def create_client(client_id: str) -> mqtt.Client:
    """Prefer callback API v2 when supported, while retaining Paho 1.x support."""
    callback_api = getattr(mqtt, "CallbackAPIVersion", None)
    if callback_api is not None:
        return mqtt.Client(
            callback_api_version=callback_api.VERSION2,
            client_id=client_id,
        )
    return mqtt.Client(client_id=client_id)
