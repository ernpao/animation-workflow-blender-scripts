import os


def clear():
    os.system("cls")  # Windows


class __Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    YELLOW = "\033[1;33;40m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_okgreen(text: str):
    print(__Colors.OKGREEN + text + __Colors.ENDC)


def print_okblue(text: str):
    print(__Colors.OKBLUE + text + __Colors.ENDC)


def print_fail(text: str):
    print(__Colors.FAIL + text + __Colors.ENDC)


def print_yellow(text: str):
    print(__Colors.YELLOW + text + __Colors.ENDC)


def print_done():
    print_okgreen("Done!")
