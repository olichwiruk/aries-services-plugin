from aries_cloudagent.messaging.models.base_record import BaseRecord, BaseRecordSchema
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.storage.error import StorageDuplicateError
from aries_cloudagent.messaging.util import datetime_to_str, time_now

import hashlib
from marshmallow import fields
from typing import Mapping, Any
import uuid


class SchemaExchangeRecord(BaseRecord):
    RECORD_TYPE = "SchemaExchange"
    RECORD_ID_NAME = "hash_id"
    AUTHOR_SELF = "self"

    class Meta:
        schema_class = "SchemaExchangeRecordSchema"

    def __init__(
        self, payload: str, author: str, *, hash_id: str = None, **kwargs,
    ):
        super().__init__(hash_id, None, **kwargs)
        self.author = author
        self.payload = payload

    @property
    def hash_id(self) -> str:
        """Accessor for the ID associated with this connection."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Get record value."""
        return {prop: getattr(self, prop) for prop in ("payload", "author")}

    @property
    def record_tags(self) -> dict:
        """Get tags for record, NOTE: relevent when filtering by tags"""
        return {
            "payload": self.payload,
            "author": self.author,
        }

    async def save(
        self,
        context: InjectionContext,
        *,
        reason: str = None,
        log_params: Mapping[str, Any] = None,
        log_override: bool = False,
        webhook: bool = None,
    ) -> str:
        """Persist the record to storage.

        Args:
            context: The injection context to use
            reason: A reason to add to the log
            log_params: Additional parameters to log
            webhook: Flag to override whether the webhook is sent

         NOTE: only deviation from the standard
               is in id generation (hash based on payload)
        """
        new_record = None
        log_reason = reason or ("Updated record" if self._id else "Created record")
        try:
            self.updated_at = time_now()
            storage: BaseStorage = await context.inject(BaseStorage)
            if not self._id:
                self._id = hashlib.sha256(self.payload.encode("UTF-8")).hexdigest()
                self.created_at = self.updated_at
                await storage.add_record(self.storage_record)
                new_record = True
            else:
                record = self.storage_record
                await storage.update_record_value(record, record.value)
                await storage.update_record_tags(record, record.tags)
                new_record = False
        finally:
            params = {self.RECORD_TYPE: self.serialize()}
            if log_params:
                params.update(log_params)
            if new_record is None:
                log_reason = f"FAILED: {log_reason}"
            self.log_state(context, log_reason, params, override=log_override)

        await self.post_save(context, new_record, self._last_state, webhook)
        self._last_state = self.state

        return self._id


class SchemaExchangeRecordSchema(BaseRecordSchema):
    class Meta:
        model_class = "SchemaExchange"

    author = fields.Str(required=False)
    payload = fields.Str(required=False)
    hash_id = fields.Str(required=False)


class SchemaExchangeRequestRecord(BaseRecord):
    RECORD_TYPE = "SchemaExchangeRequest"
    RECORD_ID_NAME = "record_id"

    AUTHOR_SELF = "self"
    AUTHOR_OTHER = "other"

    STATE_PENDING = "pending"
    STATE_APPROVED = "approved"
    STATE_DENIED = "failed to find the record"

    class Meta:
        schema_class = "SchemaExchangeRequestRecordSchema"

    def __init__(
        self,
        payload: str = None,
        author: str = None,
        connection_id: str = None,
        state: str = None,
        exchange_id: str = None,
        *,
        record_id: str = None,
        **kwargs,
    ):
        super().__init__(record_id, state, **kwargs)
        self.author = author
        self.payload = payload
        self.connection_id = connection_id

        if exchange_id is None:
            self.exchange_id = str(uuid.uuid4())
        else:
            self.exchange_id = exchange_id

    @property
    def record_value(self) -> dict:
        """Accessor to the JSON record value properties"""
        return {
            prop: getattr(self, prop)
            for prop in ("payload", "connection_id", "state", "author", "exchange_id",)
        }

    @property
    def record_tags(self) -> dict:
        """Get tags for record, 
            NOTE: relevent when filtering by tags"""
        return {
            "connection_id": self.connection_id,
            "exchange_id": self.exchange_id,
        }

    @classmethod
    async def retrieve_by_exchange_id(
        cls, context: InjectionContext, exchange_id: str
    ) -> "SchemaExchangeRequest":
        return await cls.retrieve_by_tag_filter(context, {"exchange_id": exchange_id},)


class SchemaExchangeRequestRecordSchema(BaseRecordSchema):
    class Meta:
        model_class = "SchemaExchangeRequest"

    connection_id = fields.Str(required=False)
    payload = fields.Str(required=False)
    state = fields.Str(required=False)
    author = fields.Str(required=False)
    exchange_id = fields.Str(required=False)
