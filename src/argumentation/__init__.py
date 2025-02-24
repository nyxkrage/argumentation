import argparse
import os
import sys
from argparse import ArgumentParser
from copy import deepcopy
from dataclasses import dataclass
from inspect import signature
from typing import Any, Optional, Tuple, Type

from pydantic import BaseModel, ConfigDict, create_model
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
        except Exception as e:
            raise ValueError(f"Config file {values} is not valid") from e

        setattr(namespace, self.dest, data)


class ArgumentationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


@dataclass
class Argumentation:
    description: str
    external_config: str = None

    def run(func: callable, *args, **kwargs):
        args_type = list(signature(func).parameters.values())[0].annotation
        if not issubclass(args_type, ArgumentationModel):
            raise TypeError("First argument must be a Pydantic model")

        sys.argv = [arg.replace("_", "-") if "_" in arg else arg for arg in sys.argv]

        config_arg_parser = ArgumentParser(func.__name__, add_help=False)
        config_arg_parser.add_argument(
            "--config", action=ConfigFileAction, type=str, required=False
        )
        config_args = config_arg_parser.parse_known_args()[0]
        config = None
        if config_args.config is not None:
            partial_args_type = partial_model(args_type)
            config = partial_args_type.model_validate(config_args.config, strict=True)

        arg_parser = ArgumentParser(func.__name__)
        arg_parser.add_argument(
            "--config",
            action=NoopAction,
            type=str,
            help="Path to external config file",
            default=None,
        )
        for key, field in args_type.model_fields.items():
            arg_parser.add_argument(
                f"--{key.replace('_', '-')}",
                type=field.annotation,
                required=field.is_required() and getattr(config, key, None) is None,
                default=field.get_default(),
                help=field.description,
            )
        argv = arg_parser.parse_args()

        # merge argv and config excluding the config key from argv
        argv_dict = vars(argv)
        argv_dict.pop("config", None)
        if config is not None:
            argv_dict.update(config.model_dump(exclude_defaults=True))
        argv = args_type.model_validate(vars(argv))
        func(argv, *args, **kwargs)
