import os
import tempfile

import pytest

from src.synchronizer import FolderSynchronizer, setup_logging


@pytest.fixture
def logger():
    # Create a logger for integration tests
    return setup_logging("test_integration.log", "DEBUG")


def test_integration_sync(logger):
    with tempfile.TemporaryDirectory() as source_dir:
        with tempfile.TemporaryDirectory() as replica_dir:
            source_file = os.path.join(source_dir, "test.txt")
            with open(source_file, "w", encoding="utf-8") as f:
                f.write("Some content")

            synchronizer = FolderSynchronizer(
                source_folder=source_dir,
                replica_folder=replica_dir,
                logger=logger
            )

            synchronizer.synchronize()
            replica_file = os.path.join(replica_dir, "test.txt")
            assert os.path.exists(replica_file), (
                "The file should have been copied to the replica."
            )

            os.remove(source_file)
            synchronizer.synchronize()
            assert not os.path.exists(replica_file), (
                "The file should have been removed from the replica "
                "after deletion."
            )
