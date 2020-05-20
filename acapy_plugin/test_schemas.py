from .schemas import NewSchemaMessage, SCHEMAS, NEW_SCHEMA

from unittest import mock, TestCase


class TestNewSchemaMessage(TestCase):
    payload = """[
        {
            "data1": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0/message",
            "data2": [],
        }
    ]"""

    def test_init(self):
        newSchemaMessage = NewSchemaMessage(self.payload)
        assert newSchemaMessage.payload == self.payload
        assert newSchemaMessage.schema_id == None

    def test_type(self):
        newSchemaMessage = NewSchemaMessage(self.payload)
        assert newSchemaMessage._type == NEW_SCHEMA

    @mock.patch(f"{SCHEMAS}.NewSchema.load")
    def test_deserialize(self, mock_new_schema_load):
        obj = {"obj": "obj"}

        newSchemaMessage = NewSchemaMessage.deserialize(obj)
        mock_new_schema_load.assert_called_once_with(obj)

        assert newSchemaMessage is mock_new_schema_load.return_value

    @mock.patch(f"{SCHEMAS}.NewSchema.dump")
    def test_serialize(self, mock_new_schema_dump):
        newSchemaMessage = NewSchemaMessage(self.payload)

        newSchemaMessage_dict = newSchemaMessage.serialize()
        mock_new_schema_dump.assert_called_once_with(newSchemaMessage)

        assert newSchemaMessage_dict is mock_new_schema_dump.return_value


class TestNewSchema(TestCase):

    newSchemaMessage = NewSchemaMessage("")

    def test_make_model(self):
        data = self.newSchemaMessage.serialize()
        model_instance = NewSchemaMessage.deserialize(data)
        assert isinstance(model_instance, NewSchemaMessage)
