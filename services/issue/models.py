from aries_cloudagent.messaging.models.base_record import BaseRecord, BaseRecordSchema
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.storage.error import StorageDuplicateError
from aries_cloudagent.messaging.util import datetime_to_str, time_now

from ..discovery.models import ConsentSchema, ServiceSchema
import hashlib
from marshmallow import fields, Schema
from typing import Mapping, Any
import uuid
import json


class ServiceIssueRecord(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "service_issue"

    APPLICATION_PENDING = "pending application"
    APPLICATION_CONSENT_ACCEPTED = "consent application accepted"
    APPLICATION_CONSENT_REJECTED = "consent application rejected"

    ISSUE_PENDING = "pending issue"
    ISSUE_REJECTED = "rejected issue"
    ISSUE_ACCEPTED = "accepted issue"

    class Meta:
        schema_class = "ServiceIssueRecordSchema"

    def __init__(
        self,
        *,
        state: str = None,
        service_schema: ServiceSchema = None,
        consent_schema: ConsentSchema = None,
        connection_id: str = None,
        exchange_id: str = None,
        record_id: str = None,
        **keywordArgs,
    ):
        super().__init__(record_id, state, **keywordArgs)
        self.service_schema = service_schema
        self.consent_schema = consent_schema
        self.connection_id = connection_id
        self.exchange_id = str(uuid.uuid4()) if exchange_id is None else exchange_id

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties"""
        return {
            prop: getattr(self, prop)
            for prop in (
                "service_schema",
                "consent_schema",
                "connection_id",
                "state",
                "exchange_id",
            )
        }

    @property
    def record_tags(self) -> dict:
        """Get tags for record, 
            NOTE: relevent when filtering by tags"""
        return {
            "connection_id": self.connection_id,
            "exchange_id": self.exchange_id,
            "state": self.state,
        }

    @classmethod
    async def retrieve_by_exchange_id(cls, context: InjectionContext, exchange_id: str):
        return await cls.retrieve_by_tag_filter(context, {"exchange_id": exchange_id},)


class ServiceIssueRecordSchema(BaseRecordSchema):
    class Meta:
        model_class = "ServiceIssueRecord"

    state = fields.Str(required=True)
    connection_id = fields.Str(required=True)
    exchange_id = fields.Str(required=True)
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())
