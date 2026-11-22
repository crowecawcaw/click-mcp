import json

import click
from mcp import types
from mcp.shared.exceptions import MCPError

from click_mcp import ToolCompletion, click_mcp

PROJECTS = {"alpha": "draft"}
AUDIT = []
SUMMARY = "inventory://projects/summary"
TEMPLATE = "inventory://projects/{project}"


async def list_resources(_ctx, _params):
    return types.ListResourcesResult(
        resources=[types.Resource(uri=SUMMARY, name="Project summary")]
    )


async def list_templates(_ctx, _params):
    return types.ListResourceTemplatesResult(
        resource_templates=[
            types.ResourceTemplate(uri_template=TEMPLATE, name="Project details")
        ]
    )


async def read_resource(_ctx, params):
    uri = str(params.uri)
    prefix = "inventory://projects/"
    project = uri.removeprefix(prefix)
    if uri == SUMMARY:
        content = {"projects": PROJECTS, "audit": AUDIT}
    elif uri.startswith(prefix) and project in PROJECTS:
        content = PROJECTS[project]
    else:
        raise MCPError(code=-32002, message="Unknown resource")
    return types.ReadResourceResult(
        contents=[types.TextResourceContents(uri=uri, text=json.dumps(content))]
    )


def configure(server):
    server.add_request_handler(
        "resources/list", types.PaginatedRequestParams, list_resources
    )
    server.add_request_handler(
        "resources/templates/list", types.PaginatedRequestParams, list_templates
    )
    server.add_request_handler(
        "resources/read", types.ReadResourceRequestParams, read_resource
    )


async def record_completion(event: ToolCompletion):
    AUDIT.append(
        {
            "tool": event.tool_name,
            "path": event.command_path,
            "failed": event.is_error,
            "has_request_id": event.context.request_id is not None,
            "seconds": event.duration_seconds,
        }
    )
    if event.tool_name == "projects_publish" and not event.is_error:
        await event.context.session.send_resource_updated(SUMMARY)
    if event.tool_name == "status":
        raise RuntimeError("Telemetry unavailable")


@click_mcp("inventory", configure_server=configure, on_tool_complete=record_completion)
@click.group()
def cli():
    pass


@cli.group()
def projects():
    pass


@projects.command()
@click.argument("project")
def publish(project):
    if project not in PROJECTS:
        raise click.ClickException("Unknown project")
    PROJECTS[project] = "published"
    click.echo("Published")


@cli.command()
def status():
    click.echo("Online")


if __name__ == "__main__":
    cli()
