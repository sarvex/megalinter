#!/usr/bin/env python3
"""
Class for all linters using dotnet tools
"""

from megalinter import Linter


class DotnetLinter(Linter):
    def build_lint_command(self, file=None):
        return ["dotnet"] + super().build_lint_command(file)

    def build_version_command(self):
        return ["dotnet"] + super().build_version_command()

    def build_help_command(self):
        return ["dotnet"] + super().build_help_command()
