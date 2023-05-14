#!/usr/bin/env python3
"""
GitHub Comment reporter
Post a comment on Github Pull Requests
"""
import logging
import os
import re

import github
from megalinter import Reporter, config
from megalinter.constants import ML_REPO_URL
from megalinter.utils_reporter import build_markdown_summary


class GithubCommentReporter(Reporter):
    name = "GITHUB_COMMENT"
    scope = "mega-linter"

    github_api_url = "https://api.github.com"
    github_server_url = "https://github.com"
    issues_root = ML_REPO_URL + "/issues"

    def manage_activation(self):
        if (
            config.get(self.master.request_id, "GITHUB_COMMENT_REPORTER", "true")
            != "true"
        ):
            self.is_active = False
        elif (
            config.get(self.master.request_id, "POST_GITHUB_COMMENT", "true") == "true"
        ):  # Legacy - true by default
            self.is_active = True

    @property
    def comment_marker(self):
        """Generate the comment marker

        This marker is used to find the same comment again so it can be updated.

        The marker includes the workflow name and jobid if available (via the
        GITHUB_WORKFLOW and GITHUB_JOB environment variables) to avoid clashes
        between multiple Mega-Linter jobs operating on the same PR:

          <!-- megalinter: github-comment-reporter workflow='…' jobid='…' -->

        """
        workflow = os.getenv("GITHUB_WORKFLOW")
        jobid = os.getenv("GITHUB_JOB")
        workflow = workflow and f"workflow={workflow!r}"
        jobid = jobid and f"jobid={jobid!r}"
        identifier = " ".join(
            ["github-comment-reporter", *filter(None, (workflow, jobid))]
        )
        return f"<!-- megalinter: {identifier} -->"

    def produce_report(self):
        # Post comment on GitHub pull request
        if config.get(self.master.request_id, "GITHUB_TOKEN", "") != "":
            github_repo = config.get(self.master.request_id, "GITHUB_REPOSITORY")
            github_server_url = config.get(
                self.master.request_id, "GITHUB_SERVER_URL", self.github_server_url
            )
            github_api_url = config.get(
                self.master.request_id, "GITHUB_API_URL", self.github_api_url
            )
            run_id = config.get(self.master.request_id, "GITHUB_RUN_ID")
            sha = config.get(self.master.request_id, "GITHUB_SHA")

            if config.get(self.master.request_id, "CI_ACTION_RUN_URL", "") != "":
                action_run_url = config.get(
                    self.master.request_id, "CI_ACTION_RUN_URL", ""
                )
            elif run_id is not None:
                action_run_url = (
                    f"{github_server_url}/{github_repo}/actions/runs/{run_id}"
                )
            else:
                action_run_url = ""

            # add comment marker, with extra newlines in between.
            marker = self.comment_marker
            p_r_msg = "\n".join(
                [build_markdown_summary(self, action_run_url), "", marker, ""]
            )

            # Post comment on pull request if found
            github_auth = (
                config.get(self.master.request_id, "PAT")
                if config.get(self.master.request_id, "PAT", "") != ""
                else config.get(self.master.request_id, "GITHUB_TOKEN")
            )
            g = github.Github(base_url=github_api_url, login_or_token=github_auth)
            repo = g.get_repo(github_repo)

            # Try to get PR from GITHUB_REF
            pr_list = []
            ref = os.environ.get("GITHUB_REF", "")
            m = re.compile("refs/pull/(\\d+)/merge").match(ref)
            if m is not None:
                pr_id = m[1]
                logging.debug(f"Identified PR#{pr_id} from environment")
                try:
                    pr_list = [repo.get_pull(int(pr_id))]
                except Exception as e:
                    logging.warning(f"Could not fetch PR#{pr_id}: {e}")
            if pr_list is None or not pr_list:
                # If not found with GITHUB_REF, try to find PR from commit
                commit = repo.get_commit(sha=sha)
                pr_list = commit.get_pulls()
                if pr_list.totalCount == 0:
                    logging.info(
                        "[GitHub Comment Reporter] No pull request has been found, so no comment has been posted"
                    )
                    return
            for pr in pr_list:
                # Ignore if PR is already merged
                if pr.is_merged():
                    continue
                existing_comment = next(
                    (
                        comment
                        for comment in pr.get_issue_comments().reversed
                        if marker in comment.body
                    ),
                    None,
                )
                # Process comment
                try:
                    # Edit if there is already a MegaLinter comment
                    if existing_comment is not None:
                        existing_comment.edit(p_r_msg)
                    # Or create a new PR comment
                    else:
                        pr.create_issue_comment(p_r_msg)
                    logging.debug(f"Posted Github comment: {p_r_msg}")
                    logging.info(
                        f"[GitHub Comment Reporter] Posted summary as comment on {github_repo} #PR{pr.number}"
                    )
                except github.GithubException as e:
                    logging.warning(
                        f"[GitHub Comment Reporter] Unable to post pull request comment: {str(e)}.\n"
                        "To enable this function, please :\n"
                        "1. Create a Personal Access Token (https://docs.github.com/en/free-pro-team@"
                        "latest/github/authenticating-to-github/creating-a-personal-access-token)\n"
                        "2. Create a secret named PAT with its value on your repository (https://docs."
                        "github.com/en/free-pro-team@latest/actions/reference/encrypted-secrets#"
                        "creating-encrypted-secrets-for-a-repository)"
                        "3. Define PAT={{secrets.PAT}} in your GitHub action environment variables"
                    )
                except Exception as e:
                    logging.warning(
                        f"[GitHub Comment Reporter] Error while posting comment: \n{str(e)}"
                    )
        else:
            logging.debug(
                "[GitHub Comment Reporter] No GitHub Token has been found, so skipped post of PR comment"
            )
