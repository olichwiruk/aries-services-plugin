# Acapy
from aries_cloudagent.messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.core.plugin_registry import PluginRegistry
from aries_cloudagent.ledger.base import BaseLedger
from aries_cloudagent.issuer.base import BaseIssuer
from aries_cloudagent.ledger.error import LedgerError
from aries_cloudagent.ledger.error import BadLedgerRequestError
from aries_cloudagent.issuer.base import IssuerError
from aries_cloudagent.protocols.connections.v1_0.manager import ConnectionManager

# Records, messages and schemas
from aries_cloudagent.messaging.agent_message import AgentMessage, AgentMessageSchema
from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.storage.record import StorageRecord

# Exceptions
from aries_cloudagent.storage.error import StorageDuplicateError, StorageNotFoundError
from aries_cloudagent.protocols.problem_report.v1_0.message import ProblemReport

# Internal
from ..util import generate_model_schema
from .message_types import *
from .models import ServiceIssueRecord
from ..discovery.models import ServiceRecord

# External
from asyncio import shield
from marshmallow import fields, Schema
import hashlib
import uuid
import json


async def send_confirmation(context, responder, record: ServiceIssueRecord):
    print("send_confirmation")
    confirmation = Confirmation(exchange_id=record.exchange_id, state=record.state,)

    confirmation.assign_thread_from(context.message)
    await responder.send_reply(confirmation)


async def send_confirmation_long(context, responder, exchange_id, state):
    print("send_confirmation_long")
    confirmation = Confirmation(exchange_id=exchange_id, state=state,)

    confirmation.assign_thread_from(context.message)
    await responder.send_reply(confirmation)


class ApplicationHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        print("APPLICATION HANDLER")
        print(context.message)
        assert isinstance(context.message, Application)

        try:
            service: ServiceRecord = await ServiceRecord().retrieve_by_id(
                context, context.message.service_id
            )
            print("SERVICE_RECORD", service)
        except StorageNotFoundError:
            send_confirmation_long(
                context,
                responder,
                context.message.exchange_id,
                ServiceIssueRecord.ISSUE_SERVICE_NOT_FOUND,
            )
            return

        print("before record")

        record = ServiceIssueRecord(
            state=ServiceIssueRecord.ISSUE_PENDING,
            author=ServiceIssueRecord.AUTHOR_OTHER,
            service_schema=service.service_schema,
            consent_schema=service.consent_schema,
            connection_id=context.connection_record.connection_id,
            exchange_id=context.message.exchange_id,
            service_id=context.message.service_id,
            label=service.label,
        )

        await send_confirmation(context, responder, record)

        # NOTE(Krzosa): check if schema and credential definition are registered on ledger
        ledger: BaseLedger = await context.inject(BaseLedger)
        issuer: BaseIssuer = await context.inject(BaseIssuer)

        # NOTE(Krzosa): Register the schema on ledger if not registered
        # and save the results in ServiceRecord
        if service.ledger_schema_id == None:
            async with ledger:
                try:
                    schema_id, schema_definition = await shield(
                        ledger.create_and_send_schema(
                            issuer,
                            service.label,
                            "1.0",
                            ["consent_schema", "service_schema"],
                        )
                    )
                    service.ledger_schema_id = schema_id
                    service.ledger_schema_definition = schema_definition
                    await service.save(context)
                    print("LEDGER SCHEMA ID SAVE", schema_id, schema_definition)
                except (IssuerError, LedgerError) as err:
                    print(err)
                    print("LEDGER_ERROR", err.roll_up)
                    record.state = ServiceIssueRecord.ISSUE_SERVICE_NOT_FOUND
                    await send_confirmation(context, responder, record)
                    return

        # NOTE(Krzosa): Register the credential definition on ledger if not registered
        # and save the results in ServiceRecord
        if (
            service.ledger_schema_id != None
            and service.ledger_credential_definition_id == None
        ):
            try:
                async with ledger:
                    credential_definition_id, credential_definition = await shield(
                        ledger.create_and_send_credential_definition(
                            issuer,
                            service.ledger_schema_id,
                            signature_type=None,
                            tag="Services",
                            support_revocation=False,
                        )
                    )
                print(
                    "LEDGER CRED DEF SAVE",
                    credential_definition_id,
                    credential_definition,
                )
                service.ledger_credential_definition = credential_definition
                service.ledger_credential_definition_id = credential_definition_id
                await service.save(context)
            except (LedgerError, IssuerError, BadLedgerRequestError) as err:
                print(err)

        # TODO: Some kind of decision mechanism

        record.state = ServiceIssueRecord.ISSUE_ACCEPTED
        print("before save %s", record)
        await record.save(context)
        print("after save %s", record)

        await send_confirmation(context, responder, record)


class ConfirmationHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        print("CONFIRMATION:\n %s", context.message)
        assert isinstance(context.message, Confirmation)

        try:
            record = await ServiceIssueRecord.retrieve_by_exchange_id_and_connection_id(
                context,
                context.message.exchange_id,
                context.connection_record.connection_id,
            )
        except StorageNotFoundError:
            print("\n\nConfirmation Error\n\n")
            return

        record.state = context.message.state

        await record.save(context)
