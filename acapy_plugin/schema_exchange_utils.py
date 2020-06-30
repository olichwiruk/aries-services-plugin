from aries_cloudagent.config.injection_context import InjectionContext
from .records import SchemaExchangeRecord

# Exceptions
from aries_cloudagent.storage.error import StorageDuplicateError, StorageNotFoundError
from aries_cloudagent.protocols.problem_report.v1_0.message import ProblemReport


async def schemaExchangeRecordSave(
    context: InjectionContext, record: SchemaExchangeRecord
):
    try:
        return await record.save(context, reason="Saved, SchemaExchangeRecord")
    except StorageDuplicateError:
        report = ProblemReport(explain_ltxt="Duplicate", who_retries="none")
        report.assign_thread_from(context.message)
        await responder.send_reply(report)
        return


async def problemReportHandle(context, message):
    report = ProblemReport(explain_ltxt=message, who_retries="none")
    report.assign_thread_from(context.message)
    await responder.send_reply(report)
