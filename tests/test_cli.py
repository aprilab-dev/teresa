import os

import pytest
from click.testing import CliRunner

from teresa.cli import main
from teresa.log import LOG_FNAME
from teresa.coregistration import COREG_DIR, format_date
from . import conftest

mocked_s1_slcstack = [
    conftest.create_multiple_masters_multiple_slaves,
    conftest.create_multiple_masters_single_slave,
    conftest.create_single_master_multiple_slaves,
    conftest.create_single_master_single_slave,
    conftest.create_stacks,
]


@pytest.mark.parametrize("mocked", mocked_s1_slcstack)
def test_cli_coregister(tmpdir, mocked):
    source_dir, _ = mocked(tmpdir)
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "coregister",
            "--dry-run",
            "--source-dir",
            source_dir,
            "--destination",
            source_dir,
            "--master",
            "20210507",
        ],
    )
    assert result.exit_code == 0
    assert os.path.join(source_dir, COREG_DIR) in open(LOG_FNAME).read()
