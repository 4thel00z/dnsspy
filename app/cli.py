import logging
from argparse import ArgumentParser

from app import run, Mode

logger = logging.getLogger(__name__)

parser = ArgumentParser("dnsspy")

sub_parsers = parser.add_subparsers(help='[command] help', dest="command")

enum_parser = sub_parsers.add_parser("enum", help="Enumerate the given network. Requires a host prefix like 'google'")

# FIXME: Research how to make a parameter not required
#enum_parser.add_argument("host", type=str, default="", )


def enumerate_hosts(args):
    run(args, Mode.HOST_ENUMERATION)


def main():
    args = parser.parse_args()
    if args.command == "enum":
        enumerate_hosts(args)


if __name__ == '__main__':
    main()

# from prompt_toolkit.shortcuts import prompt
# from prompt_toolkit.completion import Completer, Completion
#
#
# class MyCustomCompleter(Completer):
#     def get_completions(self, document, complete_event):
#         if complete_event.completion_requested:
#             completion = Completion('completion', start_position=0)
#             for i in range(10):
#                 yield completion
#
#
# text = prompt('> ', completer=MyCustomCompleter())
# print()
