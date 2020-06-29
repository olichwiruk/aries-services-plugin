from aries_cloudagent.messaging.models.base_record import BaseRecord, BaseRecordSchema
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.storage.error import StorageDuplicateError
from aries_cloudagent.messaging.util import datetime_to_str, time_now

import hashlib
from marshmallow import fields
from typing import Mapping, Any


class SchemaExchangeRecord(BaseRecord):
    RECORD_TYPE = "SchemaExchange"
    RECORD_ID_NAME = "hashid"
    AUTHOR_OTHER = "other"
    AUTHOR_SELF = "self"
    STATE_SENT = "sent"
    STATE_RECV = "recv"

    class Meta:
        schema_class = "SchemaExchangeRecordSchema"

    def __init__(
        self,
        payload: str,
        author: str,
        *,
        state: str = None,
        hashid: str = None,
        **kwargs,
    ):
        super().__init__(hashid, state or self.STATE_SENT, **kwargs)
        self.author = author
        self.payload = payload

    @property
    def record_value(self) -> dict:
        """Get record value."""
        return {prop: getattr(self, prop) for prop in ("payload", "author")}

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
    state = fields.Str(required=False)
