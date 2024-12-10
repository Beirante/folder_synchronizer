import os
import tempfile

import pytest

from src.synchronizer import FolderSynchronizer, setup_logging


@pytest.fixture
def logger():
    # Create a logger for unit tests
    return setup_logging("test_unit.log", "DEBUG")


def test_should_ignore(logger):
    # Test ignore patterns
    ignore_patterns = ["*.tmp", "ignore_dir/"]
    synchronizer = FolderSynchronizer(
        source_folder="/fake/source",
        replica_folder="/fake/replica",
        logger=logger,
        ignore_patterns=ignore_patterns
    )

    # Test cases
    assert synchronizer.should_ignore("file.tmp"), (
        "Files ending with '.tmp' should be ignored."
    )
    assert synchronizer.should_ignore("ignore_dir/sub/file.txt"), (
        "Directories listed in ignore patterns should be ignored."
    )
    assert not synchronizer.should_ignore("file.txt"), (
        "Regular files should not be ignored."
    )


def test_files_differ_no_md5(logger):
    # Test file comparison without MD5 hash
    with tempfile.TemporaryDirectory() as temp_dir:
        source_file = os.path.join(temp_dir, "source.txt")
        replica_file = os.path.join(temp_dir, "replica.txt")

        # Create two identical files
        with open(source_file, "w", encoding="utf-8") as f:
            f.write("Hello")
        with open(replica_file, "w", encoding="utf-8") as f:
            f.write("Hello")

        synchronizer = FolderSynchronizer(
            source_folder=temp_dir,
            replica_folder=temp_dir,
            logger=logger
        )

        # Test identical files
        assert not synchronizer.files_differ(source_file, replica_file), (
            "Identical files should not differ."
        )

        # Modify one file
        with open(replica_file, "w", encoding="utf-8") as f:
            f.write("Hello World")

        # Test different files
        assert synchronizer.files_differ(source_file, replica_file), (
            "Files should differ after modification."
        )


def test_md5_hash(logger):
    # Test MD5 hash generation
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test.txt")

        # Create a file
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Some content")

        synchronizer = FolderSynchronizer(
            source_folder=temp_dir,
            replica_folder=temp_dir,
            logger=logger
        )

        # Calculate hash
        md5_hash = synchronizer.md5(test_file)
        assert len(md5_hash) == 32, "MD5 hash should be 32 characters long."
        assert md5_hash.isalnum(), "MD5 hash should be alphanumeric."


def test_ensure_dir_exists(logger):
    # Test directory creation
    with tempfile.TemporaryDirectory() as temp_dir:
        dir_to_create = os.path.join(temp_dir, "new_dir")

        synchronizer = FolderSynchronizer(
            source_folder=temp_dir,
            replica_folder=temp_dir,
            logger=logger
        )

        # Ensure directory does not exist
        assert not os.path.exists(dir_to_create), (
            "Directory should not exist initially."
        )

        # Create directory
        synchronizer.ensure_dir_exists(dir_to_create)
        assert os.path.exists(dir_to_create), (
            "Directory should be created by ensure_dir_exists."
        )
