import click

from click_mcp import click_mcp


@click_mcp("execution-errors")
@click.group()
def cli():
    pass


@cli.command()
@click.option("--mode", type=click.Choice(["basic", "full"]))
def select(mode):
    click.echo(mode)


@cli.command()
@click.argument("kind")
def fail(kind):
    if kind == "expected":
        raise click.ClickException("The requested record is unavailable")
    if kind == "abort":
        raise click.Abort()
    if kind == "click-exit":
        click.echo("Rerun after refreshing the cache", err=True)
        raise click.exceptions.Exit(7)
    if kind == "system-exit":
        raise SystemExit(9)
    if kind == "unexpected":
        click.echo("private diagnostic", err=True)
        raise RuntimeError("private detail")
    click.echo("Finished")
    if kind == "success-exit":
        raise click.exceptions.Exit(0)
    return 5


if __name__ == "__main__":
    cli()
