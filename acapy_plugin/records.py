from aries_cloudagent.messaging.models.base_record import BaseRecord, BaseRecordSchema

class SchemaExchangeRecord(BaseRecord):
    RECORD_TYPE="SchemaExchange"
    AUTHOR_OTHER="other"
    AUTHOR_SELF="self"

    class Meta:
        schema_class = "SchemaExchangeRecordSchema"

    def __init__(self, *, id, payload, author, **keywordArguments):
        super().__init__(id, **keywordArguments)
        self.author = author
        self.payload = payload