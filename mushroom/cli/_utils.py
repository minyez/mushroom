# -*- coding: utf-8 -*-
"""Helpers shared by the native click commands"""
from functools import partial

import click
from click.core import ParameterSource


def _is_flag_like(token: str) -> bool:
    """check if a token is an option flag, instead of a value such as a negative number"""
    if len(token) < 2 or not token.startswith("-"):
        return False
    try:
        float(token)
    except ValueError:
        return True
    return False


def expand_multi_values(args, flags):
    """expand ``--opt a b`` to ``--opt a --opt b`` for flags, keeping the order of values

    Values are consumed until the next flag or the end of arguments, in the same
    way as ``nargs="+"`` of argparse. Arguments after ``--`` are left untouched.
    """
    expanded = []
    i = 0
    while i < len(args):
        token = args[i]
        i += 1
        if token == "--":
            expanded.extend(args[i - 1:])
            break
        if token not in flags:
            expanded.append(token)
            continue
        ivalue = i
        while i < len(args) and args[i] != "--" and not _is_flag_like(args[i]):
            i += 1
        if i == ivalue:
            # leave it to click to report the missing value
            expanded.append(token)
        for value in args[ivalue:i]:
            expanded.extend([token, value])
    return expanded


def fill_optional_values(args, consts):
    """insert the constant after a flag in consts when the flag is not followed by a value

    It works as ``nargs="?"`` of argparse. Arguments after ``--`` are left untouched.
    """
    filled = []
    for i, token in enumerate(args):
        if token == "--":
            filled.extend(args[i:])
            break
        filled.append(token)
        if token in consts and (i + 1 == len(args) or _is_flag_like(args[i + 1])
                                or args[i + 1] == "--"):
            filled.append(consts[token])
    return filled


class MultiValueOption(click.Option):
    """option that takes several values after one flag. The value is a tuple"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, multiple=True, **kwargs)


class OptionalValueOption(click.Option):
    """option whose value can be omitted after the flag, using const in that case"""

    def __init__(self, *args, const: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.const = const


class MultiValueCommand(click.Command):
    """command that supports :class:`MultiValueOption` and :class:`OptionalValueOption`"""

    def parse_args(self, ctx, args):
        flags = set()
        consts = {}
        for param in self.params:
            if isinstance(param, MultiValueOption):
                flags.update(param.opts)
            elif isinstance(param, OptionalValueOption):
                consts.update(dict.fromkeys(param.opts, param.const))
        args = fill_optional_values(expand_multi_values(args, flags), consts)
        return super().parse_args(ctx, args)


class Group(click.Group):
    """group whose commands support the options in this module"""
    command_class = MultiValueCommand


multi_option = partial(click.option, cls=MultiValueOption)
optional_value_option = partial(click.option, cls=OptionalValueOption)


def check_exclusive(ctx: click.Context, *names):
    """raise usage error if more than one of the parameters are set in command line"""
    used = [p for p in ctx.command.params if p.name in names
            and ctx.get_parameter_source(p.name) == ParameterSource.COMMANDLINE]
    if len(used) > 1:
        flags = ", ".join(p.opts[0] for p in used)
        raise click.UsageError(f"options are mutually exclusive: {flags}", ctx=ctx)
