from aries_cloudagent.messaging.models.base_record import BaseRecord, BaseRecordSchema
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.storage.error import StorageDuplicateError
from aries_cloudagent.messaging.util import datetime_to_str, time_now

from ..discovery.records import ConsentSchema, ServiceSchema
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
        service_schema: ServiceSchema = None,
        consent_schema: ConsentSchema = None,
        connection_id: str = None,
        exchange_id: str = None,
        state: str = None,
        record_id: str = None,
        **keywordArgs,
    ):
        super().__init__(record_id, state, **keywordArgs)
        self.service = service
        self.consent = consent
        self.connection_id = connection_id
        self.exchange_id = exchange_id


class ServiceIssueRecordSchema(BaseRecordSchema):
    state = fields.Str(required=True)
    connection_id = fields.Str(required=True)
    exchange_id = fields.Str(required=True)
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())
