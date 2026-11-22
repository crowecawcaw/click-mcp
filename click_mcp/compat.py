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


def parameter_arity(param: click.Parameter) -> tuple[int, bool]:
    return param.nargs, bool(getattr(param, "multiple", False))


def parameter_value_schema(param: click.Parameter) -> dict[str, Any]:
    """Describe one occurrence of a parameter, before wrapping repeatable options."""
    click_type = getattr(param, "type", None)
    annotation = getattr(getattr(param, "type_descriptor", None), "annotation", None)
    if get_origin(annotation) is list:
        (annotation,) = get_args(annotation)

    nargs, _ = parameter_arity(param)
    if nargs == 1:
        return (
            _click_type_schema(click_type)
            if click_type is not None
            else _annotation_schema(annotation)
        )

    if click_type is not None and hasattr(click_type, "types"):
        items = [_click_type_schema(item) for item in click_type.types]
        return {
            "type": "array",
            "prefixItems": items,
            "minItems": nargs,
            "maxItems": nargs,
        }
    if get_origin(annotation) is tuple and nargs > 1:
        items = [_annotation_schema(item) for item in get_args(annotation)]
        return {
            "type": "array",
            "prefixItems": items,
            "minItems": nargs,
            "maxItems": nargs,
        }

    items_schema = (
        _click_type_schema(click_type)
        if click_type is not None
        else _annotation_schema(annotation)
    )
    schema: dict[str, Any] = {"type": "array", "items": items_schema}
    if nargs > 1:
        schema.update(minItems=nargs, maxItems=nargs)
    return schema


def _click_type_schema(click_type: Any) -> dict[str, Any]:
    # The class names are shared by Click and Typer's vendored Click.
    names = {cls.__name__ for cls in type(click_type).__mro__}
    for cls, schema in (
        ("IntParamType", "integer"),
        ("FloatParamType", "number"),
        ("BoolParamType", "boolean"),
    ):
        if cls in names:
            return {"type": schema}
    choices = getattr(click_type, "choices", None)
    if isinstance(choices, (list, tuple)):
        return {"type": "string", "enum": list(choices)}
    return {"type": "string"}


def _annotation_schema(annotation: Any) -> dict[str, Any]:
    json_types = {int: "integer", float: "number", bool: "boolean", str: "string"}
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return {"type": "string", "enum": [str(choice.value) for choice in annotation]}
    if get_origin(annotation) is Literal:
        choices = [
            choice.value if isinstance(choice, Enum) else choice
            for choice in get_args(annotation)
        ]
        if choices and all(type(choice) in json_types for choice in choices):
            schema_types = sorted({json_types[type(choice)] for choice in choices})
            return {
                "type": schema_types[0] if len(schema_types) == 1 else schema_types,
                "enum": choices,
            }
        return {"type": "string", "enum": [str(choice) for choice in choices]}
    return {
        "type": json_types.get(
            annotation if isinstance(annotation, type) else str, "string"
        )
    }


def invoke_command(group: click.Group, args: list[str]) -> Any:
    if isinstance(group, click.Group):
        if type(group).main is not click.Group.main:
            return group.main(args=args, standalone_mode=False)
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
