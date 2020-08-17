# Copyright 2020 Canonical Ltd.
# Licensed under the Apache License, Version 2.0; see LICENCE file for details.

import io
import itertools
import os
import re
import subprocess
import sys
import unittest
from unittest.mock import patch

from flake8.api.legacy import get_style_guide
import ops.lib

from k8s import __version__

FLAKE8_OPTIONS = {"max_line_length": 99, "select": ["E", "W", "F", "C", "N"]}


def _get_python_filepaths():
    """Helper to retrieve paths of Python files."""
    python_paths = ["setup.py"]
    for root in ["k8s", "test"]:
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if filename.endswith(".py"):
                    python_paths.append(os.path.join(dirpath, filename))
    return python_paths


class TestInfra(unittest.TestCase):
    def test_pep8(self):
        """Verify all files are nicely styled."""
        python_filepaths = _get_python_filepaths()
        style_guide = get_style_guide(**FLAKE8_OPTIONS)
        fake_stdout = io.StringIO()
        with patch("sys.stdout", fake_stdout):
            report = style_guide.check_files(python_filepaths)

        # if flake8 didnt' report anything, we're done
        if report.total_errors == 0:
            return

        # grab on which files we have issues
        flake8_issues = fake_stdout.getvalue().split("\n")

        if flake8_issues:
            msg = "Please fix the following flake8 issues!\n" + "\n".join(flake8_issues)
            self.fail(msg)

    def test_ensure_copyright(self):
        """Check that all non-empty Python files have copyright somewhere in the first 5 lines."""
        issues = []
        regex = re.compile(r"# Copyright \d{4}(-\d{4})? Canonical Ltd.$")
        for filepath in _get_python_filepaths():
            if os.stat(filepath).st_size == 0:
                continue

            with open(filepath, "rt", encoding="utf8") as fh:
                for line in itertools.islice(fh, 5):
                    if regex.match(line):
                        break
                else:
                    issues.append(filepath)
        if issues:
            msg = "Please add copyright headers to the following files:\n" + "\n".join(issues)
            self.fail(msg)

    def test_setup_version(self):
        """Verify that setup.py is picking up the version correctly."""
        cmd = [sys.executable, os.path.abspath("setup.py"), "--version"]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE)
        output = proc.stdout.decode("utf8")
        assert output.strip() == __version__

    def test_ops_lib_use(self):
        # just check it works :)
        k8s = ops.lib.use("k8s", 0, "chipaca@canonical.com")
        assert k8s.LIBAPI == 0
