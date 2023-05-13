#!/usr/bin/env python3
"""
Use lintr to lint R files
https://github.com/r-lib/lintr
"""
import os
from shutil import copyfile

from megalinter import Linter


class RLinter(Linter):
    # Build the CLI command to call to lint a file
    def build_lint_command(self, file=None):
        # lintr requires .lintr in folder: copy it there if necessary
        dir_name = os.path.dirname(file)
        if not os.path.isfile(dir_name + os.path.sep + self.config_file_name):
            copyfile(self.config_file, dir_name + os.path.sep + self.config_file_name)
        # Build command in R format
        r_commands = [
            f"lints <- lintr::lint('{file}');",
            "print(lints);",
            "errors <- purrr::keep(lints, ~ .type == 'error');",
            "quit(save = 'no', status = if (length(errors) > 0) 1 else 0)",
        ]
        return ["R", "--slave", "-e", "".join(r_commands)]

    # Build the CLI command to request lintr version
    def build_version_command(self):
        # Build command in R format
        r_commands = ['packageVersion("lintr");']
        return ["R", "--slave", "-e", "".join(r_commands)]

    # Build the CLI command to request lintr help
    def build_help_command(self):
        # Build command in R format
        r_commands = ['help("lintr");']
        return ["R", "--slave", "-e", "".join(r_commands)]
