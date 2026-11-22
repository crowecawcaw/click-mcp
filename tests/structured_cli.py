import json

import click

from click_mcp import ToolAdapter, click_mcp
from click_mcp.decorator import register_mcp_metadata


@click_mcp("directory")
@click.group()
def cli():
    pass


@cli.command()
@click.option("--query-json", required=True)
def lookup(query_json):
    query = json.loads(query_json)
    return {"matched": [query["name"].upper()], "limit": query["limit"]}


@cli.command()
def status():
    click.echo("Directory online")


@cli.command()
def broken():
    return {"invalid": float("nan")}


def encode_query(args):
    if not args["query"]["name"].strip():
        raise ValueError("Name cannot be blank")
    return {"query_json": json.dumps(args["query"])}


register_mcp_metadata(
    "lookup",
    {
        "adapter": ToolAdapter(
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "object",
                        "required": ["name", "limit"],
                        "properties": {
                            "name": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                        },
                    }
                },
            },
            adapt_arguments=encode_query,
            adapt_result=dict,
        )
    },
)
register_mcp_metadata("broken", {"adapter": ToolAdapter(adapt_result=dict)})


if __name__ == "__main__":
    cli()
