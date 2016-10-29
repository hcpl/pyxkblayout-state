#! /usr/bin/env python3

from __future__ import print_function

from xkblayout_state import *

import io
import sys


def print_usage(progname):
    print('\n'.join([
        "",
        "xkblayout-state version 1b",
        "",
        "Usage: ",
        "",
        "To get the current layout(s):",
        "  {} print format".format(progname),
        "",
        "This causes the 'format' string to be printed on stdout with the following substitutions:",
        "  %c -> current layout number",
        "  %n -> current layout name",
        "  %s -> current layout symbol",
        "  %v -> current layout variant",
        "  %e -> current layout variant (equals to %s if %v is empty)",
        "  %C -> layout count",
        "  %N -> layout names (one per line)",
        "  %S -> layout symbols (one per line)",
        "  %V -> layout variants (one per line)",
        "  %E -> layout variants (one per line; layout symbol is used if variant is empty)",
        "  %% -> A literal '%'",
        "",
        "For example:",
        "  {} print \"Current layout: %s(%e)\"".format(progname),
        "",
        "To set the current layout:",
        "  {} set layout_number".format(progname),
        "",
        "Here 'layout_number' is the number of the layout to be set (starting from 0)",
        "and can be either absolute (default) or relative (if preceded with a plus or minus sign).",
        "",
        "For example:",
        "  {} set 1".format(progname),
        "  {} set +1".format(progname),
    ]), end="\n\n", file=sys.stderr)

def print_status(xkb, format):
    r = io.StringIO()

    i = 0
    while i < len(format):
        if i < len(format)-1 and format[i] == '%':
            if format[i+1] == 'c':
                print(xkb.current_group_num, file=r, end="")
            elif format[i+1] == 'n':
                print(xkb.current_group_name, file=r, end="")
            elif format[i+1] == 's':
                print(xkb.current_group_symbol, file=r, end="")
            elif format[i+1] == 'v':
                print(xkb.current_group_variant, file=r, end="")
            elif format[i+1] == 'e':
                if len(xkb.current_group_variant) == 0:
                    print(xkb.current_group_symbol, file=r, end="")
                else:
                    print(xkb.current_group_variant, file=r, end="")

            elif format[i+1] == 'C':
                print(xkb.group_count, file=r, end="")
            elif format[i+1] == 'N':
                for j in range(len(xkb.group_names)):
                    print(xkb.group_names[j], file=r)
            elif format[i+1] == 'S':
                for j in range(len(xkb.group_symbols)):
                    print(xkb.group_symbols[j], file=r)
            elif format[i+1] == 'V':
                for j in range(len(xkb.group_variants)):
                    print(xkb.group_variants[j], file=r)
            elif format[i+1] == 'E':
                for j in range(len(xkb.group_variants)):
                    if xkb.group_variants[j] == "":
                        print(xkb.group_symbols[j], file=r)
                    else:
                        print(xkb.group_variants[j], file=r)

            elif format[i+1] == '%':
                print('%', file=r, end="")

            else:
                print("Unknown format character: ", format[i+1], file=sys.stderr)
                r.close()
                return False
            i += 1
        else:    # not '%'
            print(format[i], file=r, end="")

        i += 1

    print(r.getvalue(), end="")
    r.close()
    return True

def set_group(xkb, group):
    relative = False

    # Check that 'group' is a valid integer (and whether it's relative or not)
    i = 0
    if group[0] == '+' or group[0] == '-':
        relative = True
        i += 1

    for i in range(i, len(group)):
        if not group[i].isdigit():
            print("{} is not an integer".format(group), file=sys.stderr)
            return False

    group_int = int(group)
    if relative:
        if not xkb.change_group(group_int):
            print("Failed to change group", file=sys.stderr)
            return False
    else:
        if group_int >= xkb.group_count:
            print("layout_number must be between 0 and {}".format(xkb.group_count - 1), file=sys.stderr)
            return False
        else:
            if not xkb.set_group_by_num(group_int):
                print("Failed to change group", file.sys.stderr)
                return False

    return True


def main():
    try:
        xkb = XKeyboard()

        if len(sys.argv) != 3:
            print_usage(sys.argv[0])
            sys.exit(1)
        else:
            command = sys.argv[1]
            if command == "print":
                if not print_status(xkb, sys.argv[2]):
                    sys.exit(1)
            elif command == "set":
                if not set_group(xkb, sys.argv[2]):
                    sys.exit(1)
            else:
                print_usage(argv[0])
                sys.exit(1)
    except SystemExit:
        raise


if __name__ == "__main__":
    main()
