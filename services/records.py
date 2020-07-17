from aries_cloudagent.messaging.models.base_record import BaseRecord, BaseRecordSchema
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.storage.error import StorageDuplicateError
from aries_cloudagent.messaging.util import datetime_to_str, time_now
from aries_cloudagent.messaging.valid import INDY_ISO8601_DATETIME
from aries_cloudagent.messaging.valid import IndyISO8601DateTime

import hashlib
from marshmallow import fields, Schema
from typing import Mapping, Any
import uuid


class ConsentSchema(Schema):
    # information fields
    did = fields.Str(required=False)
    name = fields.Str(required=False)
    version = fields.Str(required=False)
    description = fields.Str(required=False)
    # mandatory fields
    expiration = fields.Str(required=True, **INDY_ISO8601_DATETIME)
    limitation = fields.Str(required=True, **INDY_ISO8601_DATETIME)
    dictatedBy = fields.Str(required=True)
    validityTTL = fields.Integer()


# TODO: I think I need to add hash based storage
class ServiceRecord(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "verifiable_services"

    class Meta:
        schema_class = "ServiceRecordSchema"

    def __init__(
        self,
        *,
        record_id: str = None,
        payload: str = None,
        state: str = None,
        consent_schema: str = None,
        **keywordArgs,
    ):
        super().__init__(record_id, state, **keywordArgs)
        self.consent_schema = consent_schema
        self.payload = payload

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties"""
        return {prop: getattr(self, prop) for prop in ("payload", "consent_schema")}


class ServiceRecordSchema(BaseRecordSchema):
    class Meta:
        model_class = "ServiceRecord"

    payload = fields.Str(required=True)
    consent_schema = fields.Nested("ConsentSchema")

