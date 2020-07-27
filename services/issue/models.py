from aries_cloudagent.messaging.models.base_record import BaseRecord, BaseRecordSchema
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.storage.error import StorageDuplicateError
from aries_cloudagent.messaging.util import datetime_to_str, time_now

import hashlib
from marshmallow import fields, Schema
from typing import Mapping, Any
import uuid
import json

from ..discovery.models import ConsentSchema, ServiceSchema
from ..util import assert_items_are_not_none


class ServiceIssueRecord(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "service_issue"

    ISSUE_PENDING = "pending issue"
    ISSUE_REJECTED = "rejected issue"
    ISSUE_ACCEPTED = "accepted issue"

    AUTHOR_SELF = "self"
    AUTHOR_OTHER = "other"

    class Meta:
        schema_class = "ServiceIssueRecordSchema"

    def __init__(
        self,
        *,
        state: str = None,
        author: str = None,
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
        self.author = author
        self.exchange_id = str(uuid.uuid4()) if exchange_id is None else exchange_id

        assert_items_are_not_none(
            self.service_schema,
            self.consent_schema,
            self.connection_id,
            self.author,
            self.exchange_id,
        )

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
                "author",
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
            "author": self.author,
        }

    @classmethod
    async def retrieve_by_exchange_id(cls, context: InjectionContext, exchange_id: str):
        return await cls.retrieve_by_tag_filter(context, {"exchange_id": exchange_id},)


class ServiceIssueRecordSchema(BaseRecordSchema):
    class Meta:
        model_class = "ServiceIssueRecord"

    state = fields.Str(required=False)
    author = fields.Str(required=False)
    connection_id = fields.Str(required=False)
    exchange_id = fields.Str(required=False)
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())
