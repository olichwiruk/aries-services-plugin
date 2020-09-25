from aiohttp import web

from .issue.routes import *
from .discovery.routes import *

# NOTE: define functions in sub routes files (i.e issue.routes) and register
# them here


async def register(app: web.Application):
    app.add_routes(
        [
            web.post("/verifiable-services/add", add_service),
            web.post("/verifiable-services/apply", apply),
            web.post("/verifiable-services/get-issue-self", get_issue_self,),
            web.post("/verifiable-services/process-application", process_application,),
            web.get(
                "/verifiable-services/request-service-list/{connection_id}",
                request_services_list,
                allow_head=False,
            ),
            web.get(
                "/verifiable-services/self-service-list",
                self_service_list,
                allow_head=False,
            ),
            web.get(
                "/verifiable-services/DEBUGrequest/{connection_id}",
                DEBUGrequest_services_list,
                allow_head=False,
            ),
            # web.get(
            #     "/verifiable-services/get-credential-data/{data_dri}",
            #     DEBUGget_credential_data,
            #     allow_head=False,
            # ),
            # web.get(
            #     "/verifiable-services/apply-status",
            #     DEBUGapply_status,
            #     allow_head=False,
            # ),
        ]
    )
