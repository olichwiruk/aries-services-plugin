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


class ConsentContentSchema(Schema):
    expiration = fields.Str(required=True)
    limitation = fields.Str(required=True)
    dictatedBy = fields.Str(required=True)
    validityTTL = fields.Str(required=True)


class ConsentSchema(Schema):
    # dri - decentralized resource identifier
    oca_schema_dri = fields.Str(required=True)
    oca_schema_namespace = fields.Str(required=True)
    data_dri = fields.Str(required=True)


class ServiceSchema(Schema):
    oca_schema_dri = fields.Str(required=True)
    oca_schema_namespace = fields.Str(required=True)


class ServiceRecord(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "verifiable_services"

    class Meta:
        schema_class = "ServiceRecordSchema"

    def __init__(
        self,
        *,
        label: str = None,
        service_schema: ServiceSchema = None,
        consent_schema: ConsentSchema = None,
        # those usually are created later
        ledger_schema_id: str = None,
        ledger_credential_definition_id: str = None,
        state: str = None,
        record_id: str = None,
        **keywordArgs,
    ):
        super().__init__(record_id, state, **keywordArgs)
        self.consent_schema = consent_schema
        self.service_schema = service_schema
        self.label = label
        self.ledger_schema_id = ledger_schema_id
        self.ledger_credential_definition_id = ledger_credential_definition_id

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties"""
        return {
            prop: getattr(self, prop)
            for prop in (
                "service_schema",
                "consent_schema",
                "label",
                "ledger_schema_id",
                "ledger_credential_definition_id",
            )
        }

    @property
    def record_tags(self) -> dict:
        return {"label": self.label}


class ServiceRecordSchema(BaseRecordSchema):
    class Meta:
        model_class = "ServiceRecord"

    label = fields.Str(required=True)
    service_id = fields.Str(required=True)
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())
    ledger_schema_id = (fields.Str(required=False),)
    ledger_credential_definition_id = (fields.Str(required=False),)

