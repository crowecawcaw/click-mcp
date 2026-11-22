"""Shared command and parameter inspection for Click and Typer."""

from enum import Enum
from typing import Any, Literal, get_args, get_origin

import click


def is_group(command: click.Command) -> bool:
    return callable(getattr(command, "list_commands", None)) and callable(
        getattr(command, "get_command", None)
    )


def is_exposed_parameter(param: click.Parameter) -> bool:
    # Typer adds CLI-only actions such as shell completion management.
    return not getattr(param, "hidden", False) and (
        not type(param).__module__.startswith("typer.") or param.expose_value
    )


def parameter_type(param: click.Parameter) -> tuple[str, list[Any] | None]:
    click_type = getattr(param, "type", None)
    if click_type is not None:
        # The class names are shared by Click and Typer's vendored Click.
        names = {cls.__name__ for cls in type(click_type).__mro__}
        for cls, schema in (
            ("IntParamType", "integer"),
            ("FloatParamType", "number"),
            ("BoolParamType", "boolean"),
        ):
            if cls in names:
                return schema, None
        choices = getattr(click_type, "choices", None)
        return "string", list(choices) if isinstance(choices, (list, tuple)) else None

    annotation = getattr(getattr(param, "type_descriptor", None), "annotation", None)
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return "string", [str(choice.value) for choice in annotation]
    if get_origin(annotation) is Literal:
        return "string", [str(choice) for choice in get_args(annotation)]
    return {int: "integer", float: "number", bool: "boolean"}.get(
        annotation if isinstance(annotation, type) else str, "string"
    ), None


def invoke_command(group: click.Group, args: list[str]) -> Any:
    if isinstance(group, click.Group):
        with group.make_context(group.name or "cli", args) as ctx:
            return group.invoke(ctx)

    from typer import Abort, Exit
    from typer._click import exceptions

    try:
        with group.make_context(group.name or "cli", args) as ctx:
            return group.invoke(ctx)
    except exceptions.UsageError as exc:
        raise click.UsageError(exc.format_message()) from exc
    except exceptions.ClickException as exc:
        error = click.ClickException(exc.format_message())
        error.exit_code = exc.exit_code
        raise error from exc
    except Abort as exc:
        raise click.Abort() from exc
    except Exit as exc:
        raise click.exceptions.Exit(exc.exit_code) from exc
