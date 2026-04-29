# Base class for all services that participate in the message bus.
# Routing uses a single class-level registry — no MessageBus instance per service.

from __future__ import annotations

from app.bus.message import Message, MessageType

from app.logging.service import LoggerService

class Service:
    """
    Subclasses should subscribe to all types of messages they need to process.
    """

    def subscribeToMessages(self, message_types: list[MessageType]) -> None:
        for message_type in message_types:
            MessageBus.subscribe(message_type, self)

    """
    Subclasses should implement this method to publish messages to the message bus
    if they want to publish messages to the message bus.
    """

    def publishMessage(self, message: Message) -> None:
       
        MessageBus.publish(message)
        _logger = LoggerService(service_name="MESSAGE_BUS")
        _logger.info(f"Publishing message: {message}", event_id=message.data.get("event_id"), user_id=message.data.get("user_id"))

    """
    Subclasses should implement this method to process messages from the message bus
    if they want to process messages from the message bus.
    """

    def processMessage(self, message: Message) -> None:
        raise NotImplementedError("Subclasses must implement this method")


class MessageBus:
    """Process-local broker: one shared subscriber map for the whole app."""

    messageToSubscribers: dict[MessageType, list[Service]] = {}

    """
    Subscribe a service to a message type. Should be called by the service constructor to subscribe to all message types it needs to process.
    """
    @classmethod
    def subscribe(cls, message_type: MessageType, subscriber: Service) -> None:
        if message_type not in cls.messageToSubscribers:
            cls.messageToSubscribers[message_type] = []
        cls.messageToSubscribers[message_type].append(subscriber)

    """
    Publish a message to the message bus. Should be called by the service to publish a message to the message bus.
    """
    @classmethod
    def publish(cls, message: Message) -> None:
        for subscriber in cls.messageToSubscribers.get(message.get_type(), []):
            subscriber.processMessage(message)
