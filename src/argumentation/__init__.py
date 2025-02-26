import argparse
import os
import sys
from argparse import ArgumentParser
from copy import deepcopy
from dataclasses import dataclass
from inspect import signature, isclass
from types import GenericAlias
from typing import (
    Any,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
    get_origin,
    get_args,
)

from pydantic import BaseModel, ConfigDict, ValidationError, create_model
from pydantic.fields import FieldInfo


def partial_model(model: Type[BaseModel]) -> type[BaseModel]:
    def make_field_optional(
        field: FieldInfo, default: Any = None
    ) -> Tuple[Any, FieldInfo]:
        new = deepcopy(field)
        new.default = default
        new.annotation = Optional[field.annotation]  # type: ignore
        return new.annotation, new

    return create_model(
        f"Partial{model.__name__}",
        __base__=model,
        __module__=model.__module__,
        **{
            field_name: make_field_optional(field_info)
            for field_name, field_info in model.__fields__.items()
        },
    )


class NoopAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        pass


class ConfigFileAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not isinstance(values, str):
            raise ValueError("Config file must be a string")
        if not os.path.isfile(values):
            raise ValueError(f"File {values} does not exist")
        parse_function = None
        if values.endswith(".toml"):
            if sys.version_info < (3, 11):
                import tomli

                parse_function = tomli.loads
            else:
                import tomllib

                parse_function = tomllib.loads
        if (
            values.endswith(".yaml")
            or values.endswith(".yml")
            or values.endswith(".json")
        ):
            import yaml

            parse_function = yaml.safe_load

        try:
            data = parse_function(open(values, "r"))
            data["__file__"] = values
        except Exception as e:
            raise ValueError(f"Config file {values} is not valid") from e

        setattr(namespace, self.dest, data)


class ArgumentationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def add_arg(arg_parser, config, config_path, arg_name, arg_type, arg_kwargs):
    if arg_type is bool:
        arg_kwargs["action"] = arg_kwargs.get("action", "store_true")
        arg_parser.add_argument(
            f"--{arg_name.replace('_', '-')}",
            **arg_kwargs,
        )
        return
    if arg_type in [bool, int, float, str]:
        arg_kwargs["type"] = arg_type
        arg_parser.add_argument(
            f"--{arg_name.replace('_', '-')}",
            **arg_kwargs,
        )
        return
    if get_origin(arg_type) is list:
        inner_type = get_args(arg_type)[0]
        arg_kwargs["nargs"] = arg_kwargs.get("nargs", "+")
        arg_kwargs["action"] = arg_kwargs.get("action", "extend")
        add_arg(arg_parser, config, config_path, arg_name, inner_type, arg_kwargs)
        return
    if get_origin(arg_type) is tuple:
        inner_types = get_args(arg_type)
        arg_kwargs["nargs"] = arg_kwargs.get("nargs", len(inner_types))
        arg_kwargs["action"] = arg_kwargs.get("action", "extend")
        add_arg(
            arg_parser, config, config_path, arg_name, Union[inner_types], arg_kwargs
        )
        return
    if get_origin(arg_type) is Literal:
        allowed_values = get_args(arg_type)
        arg_kwargs["choices"] = allowed_values
        # Determine the type from the allowed values
        if allowed_values and all(
            isinstance(val, type(allowed_values[0])) for val in allowed_values
        ):
            arg_kwargs["type"] = type(allowed_values[0])
        arg_parser.add_argument(
            f"--{arg_name.replace('_', '-')}",
            **arg_kwargs,
        )
        return
    if get_origin(arg_type) is Union:
        inner_types = get_args(arg_type)

        def try_parse(val):
            for typ in inner_types:
                try:
                    return typ(val)
                except ValueError:
                    pass
            raise ValueError(f"Could not parse {val} as {inner_types}")

        arg_kwargs["type"] = try_parse
        arg_parser.add_argument(
            f"--{arg_name.replace('_', '-')}",
            **arg_kwargs,
        )
        return

    if (
        type(arg_type) is not GenericAlias
        and isclass(arg_type)
        and issubclass(arg_type, ArgumentationModel)
    ):
        raise NotImplementedError(
            f"Nested ArgumentationModels are not supported yet. Got {arg_type}"
        )
        for key, field in arg_type.model_fields.items():
            add_arg(
                arg_parser,
                config,
                config_path,
                key,
                field.annotation,
                {
                    "required": field.is_required()
                    and getattr(config, key, None) is None,
                    "help": field.description,
                },
            )
        return

    if (
        type(arg_type) is not GenericAlias
        and isclass(arg_type)
        and issubclass(arg_type, BaseModel)
    ):
        arg_kwargs["type"] = arg_type.model_validate
    del arg_kwargs["help"]
    arg_parser.add_argument(
        f"--{arg_name.replace('_', '-')}-config",
        action=ConfigFileAction,
        dest=arg_name,
        help=f"Path to config file for {arg_name} (defaults to main config file)",
        default=config_path,
        **arg_kwargs,
    )


@dataclass
class Argumentation:
    description: str

    def run(func: callable, *args, **kwargs):
        args_type = list(signature(func).parameters.values())[0].annotation
        if not issubclass(args_type, ArgumentationModel):
            raise TypeError("First argument must be a Pydantic model")

        config_arg_parser = ArgumentParser(func.__name__, add_help=False)
        config_arg_parser.add_argument(
            "--config", action=ConfigFileAction, type=str, required=False
        )
        config_args = config_arg_parser.parse_known_args()[0]
        config = None
        config_file = None
        if config_args.config is not None:
            partial_args_type = partial_model(args_type)
            config_file = config_args.config["__file__"]
            del config_args.config["__file__"]
            config = partial_args_type.model_validate(config_args.config)

        arg_parser = ArgumentParser(func.__name__)
        arg_parser.add_argument(
            "--config",
            action=NoopAction,
            type=str,
            help="Path to external config file",
            default=None,
        )
        for key, field in args_type.model_fields.items():
            add_arg(
                arg_parser,
                config,
                config_file,
                key,
                field.annotation,
                {
                    "required": field.is_required()
                    and getattr(config, key, None) is None,
                    "default": field.get_default(),
                    "help": field.description,
                },
            )
        argv = arg_parser.parse_args()

        argv_dict = vars(argv)
        argv_dict.pop("config", None)
        if config is not None:
            argv_dict.update(config.model_dump(exclude_defaults=True))
        try:
            argv = args_type.model_validate(argv_dict)
        except ValidationError as e:
            print(
                f"Invalid arguments: {e}\n\nRun with --help for more information",
                file=sys.stderr,
            )
            sys.exit(1)
        func(argv, *args, **kwargs)
