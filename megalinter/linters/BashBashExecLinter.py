#!/usr/bin/env python3
"""
Use bash-exec to lint bash files
"""

import megalinter


class BashBashExecLinter(megalinter.Linter):
    # To execute before linting files
    def before_lint_files(self):
        self.disable_errors = (
            megalinter.config.get(
                self.request_id, "ERROR_ON_MISSING_EXEC_BIT", "false"
            )
            != "true"
        )
