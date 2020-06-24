from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.messaging.models.base_record import BaseRecord, BaseRecordSchema

import hashlib
from marshmallow import fields

class SchemaExchangeRecord(BaseRecord):
    RECORD_TYPE="SchemaExchange"
    AUTHOR_OTHER="other"
    AUTHOR_SELF="self"

    class Meta:
        schema_class = "SchemaExchangeRecordSchema"

    def __init__(self, *, payload, author, hashid = None):
        state="test"
        super().__init__()
        self.author = author
        self.payload = payload
        if hashid is None:
            self.hashid = hashlib.sha256(payload.encode("UTF-8")).hexdigest()
        else:
            self.hashid = hashid 

    @classmethod
    async def retrieve_by_hashid(
        cls, context: InjectionContext, hashid: str) -> "SchemaExchangeRecord":
        return await cls.retrieve_by_tag_filter(context, {"hashid": hashid})



class SchemaExchangeRecordSchema(BaseRecordSchema):
    class Meta:
        model_class="SchemaExchange"
    
    author = fields.Str(required=False)
    payload = fields.Str(required=False)
    hashid = fields.Str(required=False)