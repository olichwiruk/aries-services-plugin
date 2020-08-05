from aiohttp import web

from .issue.routes import *
from .discovery.routes import *
from .action_issue.routes import *

# NOTE: define functions in sub routes files (i.e issue.routes) and register
# them here


async def register(app: web.Application):
    app.add_routes(
        [
            web.post("/verifiable-services/add", add_service),
            web.post("/verifiable-services/apply", apply),
            web.get(
                "/verifiable-services/apply-status",
                application_status,
                allow_head=False,
            ),
            web.get(
                "/verifiable-services/request/{connection_id}",
                request_services_list,
                allow_head=False,
            ),
            web.get(
                "/verifiable-services/fetch-list/{connection_id}",
                fetch_services,
                allow_head=False,
            ),
            web.get(
                "/verifiable-services/fetch-self",
                fetch_services_self,
                allow_head=False,
            ),
        ]
    )
