import os
import sys
import time
import shutil
import logging
import argparse
import hashlib
import json
from typing import Tuple, Set, List
from logging.handlers import RotatingFileHandler


class FolderSynchronizer:
    """
    Class responsible for synchronizing a source folder with a replica folder.
    This ensures a unidirectional copy from the source to the replica.

    Features include:
    - MD5-based file comparison for accuracy (optional).
    - Hash caching for improved performance (optional).
    - Ignore patterns to exclude certain files or directories.
    - Dry-run mode to simulate operations without modifying the replica.
    """

    def __init__(
        self,
        source_folder: str,
        replica_folder: str,
        logger: logging.Logger,
        use_md5: bool = False,
        use_hash_cache: bool = False,
        ignore_patterns: List[str] = None,
        dry_run: bool = False,
        max_retries: int = 3
    ):
        """
        Constructor of the FolderSynchronizer class.

        :param source_folder: Absolute path of the source folder.
        :param replica_folder: Absolute path of the replica folder.
        :param logger: Logger instance to record operations.
        :param use_md5: If True, use MD5 hash to compare files.
        :param use_hash_cache: If True, use a hash cache to
            improve performance.
        :param ignore_patterns: List of file/directory patterns to ignore.
        :param dry_run: If True, does not modify the replica,
            only logs actions.
        :param max_retries: Maximum number of retries for I/O operations.
        """
        self.source_folder = source_folder
        self.replica_folder = replica_folder
        self.logger = logger
        self.use_md5 = use_md5
        self.use_hash_cache = use_hash_cache
        self.ignore_patterns = ignore_patterns if ignore_patterns else []
        self.dry_run = dry_run
        self.max_retries = max_retries
        self.hash_cache_file = os.path.join(replica_folder, "hash_cache.json")

        if self.use_hash_cache and os.path.exists(self.hash_cache_file):
            with open(self.hash_cache_file, "r", encoding="utf-8") as f:
                self.hash_cache = json.load(f)
        else:
            self.hash_cache = {}

    def ensure_dir_exists(self, path: str) -> None:
        if not os.path.exists(path) and not self.dry_run:
            os.makedirs(path)

    def get_all_items(self, root: str) -> Tuple[Set[str], Set[str]]:
        """
        Scans the given folder and returns all files and
        directories as separate sets.
        """
        files = set()
        dirs = set()
        for dirpath, dirnames, filenames in os.walk(root):
            rel_dir = os.path.relpath(dirpath, root)
            if rel_dir == ".":
                rel_dir = ""
            if rel_dir:
                dirs.add(rel_dir.replace("\\", "/"))
            for f in filenames:
                rel_file_path = os.path.join(rel_dir, f).replace("\\", "/")
                if not self.should_ignore(rel_file_path):
                    files.add(rel_file_path)
            dirnames[:] = [
                d for d in dirnames
                if not self.should_ignore(os.path.join(rel_dir, d))
            ]
        return files, dirs

    def should_ignore(self, path: str) -> bool:
        """
        Determines if the given path matches any ignore patterns.
        """
        for pattern in self.ignore_patterns:
            if self.match_pattern(path, pattern):
                return True
        return False

    def match_pattern(self, path: str, pattern: str) -> bool:
        """
        Checks if 'path' matches the given 'pattern'.

        Supported simple patterns:
        - '*' matches any sequence of characters.
        - If the pattern ends with '/', ignore everything in that directory.
        """
        path = path.replace("\\", "/")
        pattern = pattern.replace("\\", "/")

        if pattern.endswith("/"):
            # Ignore entire directory
            if path.startswith(pattern[:-1]):
                return True
        else:
            # Simple patterns like *.ext
            if "*" in pattern:
                base, ext = pattern.split("*", 1)
                if pattern.startswith("*"):
                    return path.endswith(ext)
            else:
                # Exact match
                return path == pattern
        return False

    def md5(self, file_path: str) -> str:
        """
        Calculates the MD5 hash of the specified file.
        Uses the hash cache if enabled.
        """
        if not os.path.exists(file_path):
            return ""

        stat = os.stat(file_path)
        key = f"{file_path}-{stat.st_size}-{int(stat.st_mtime)}"

        if self.use_hash_cache and key in self.hash_cache:
            return self.hash_cache[key]

        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        hash_val = hasher.hexdigest()

        if self.use_hash_cache:
            self.hash_cache[key] = hash_val

        return hash_val

    def files_differ(self, source_file: str, replica_file: str) -> bool:
        """
        Checks if files differ.
        If use_md5 is True, compares MD5 hashes (with cache if enabled);
        otherwise, compares file size and modification time.
        """
        if not os.path.exists(replica_file):
            return True

        if self.use_md5:
            source_hash = self.md5(source_file)
            replica_hash = self.md5(replica_file)
            return source_hash != replica_hash
        else:
            source_stat = os.stat(source_file)
            replica_stat = os.stat(replica_file)
            if source_stat.st_size != replica_stat.st_size:
                return True
            if abs(source_stat.st_mtime - replica_stat.st_mtime) > 1:
                return True
            return False

    def copy_item(self, rel_path: str) -> None:
        """
        Copies or updates a file/directory from the source to the replica.
        """
        src_path = os.path.join(self.source_folder, rel_path)
        dst_path = os.path.join(self.replica_folder, rel_path)
        if os.path.isdir(src_path):
            self.ensure_dir_exists(dst_path)
            self.logger.info(f"Directory created/updated: {dst_path}")
        else:
            self.ensure_dir_exists(os.path.dirname(dst_path))
            if not self.dry_run:
                self._retry_operation(shutil.copy2, src_path, dst_path)
            self.logger.info(f"File copied/updated: {dst_path}")

    def remove_item(self, rel_path: str) -> None:
        """
        Removes a file or directory from the replica folder.
        """
        path = os.path.join(self.replica_folder, rel_path)
        if not self.dry_run:
            if os.path.isdir(path) and not os.path.islink(path):
                self._retry_operation(shutil.rmtree, path)
            else:
                self._retry_operation(os.remove, path)
        self.logger.info(f"Removed: {path}")

    def _retry_operation(self, func, *args, **kwargs):
        """
        Tries to execute an I/O operation multiple times in case of failure.
        """
        for attempt in range(self.max_retries):
            try:
                func(*args, **kwargs)
                return
            except Exception as e:
                self.logger.warning(
                    f"Failed to execute {func.__name__} {args}: {e}, "
                    f"attempt {attempt+1}/{self.max_retries}")
                time.sleep(1)
        self.logger.error(
            f"Permanent failure executing {func.__name__} on {args}")

    def synchronize(self) -> None:
        """
        Synchronizes the replica folder with the source folder.

        Steps:
        1. Identifies items (files/directories) to:
        - Add: Items present in the source but missing in the replica.
        - Remove: Items present in the replica but missing in the source.
        - Update: Items present in both but differing in content.
        2. Adds/updates items in the replica:
        - Uses `files_differ` to check for differences in files.
        - Copies items from the source to the replica as needed.
        3. Removes items from the replica that no longer exist in the source.
        4. Saves hash cache to disk if the `use_hash_cache` option is enabled.

        All actions are logged, and no changes are made in dry-run mode.
        """
        source_files, source_dirs = self.get_all_items(self.source_folder)
        replica_files, replica_dirs = self.get_all_items(self.replica_folder)

        source_all = source_files.union(source_dirs)
        replica_all = replica_files.union(replica_dirs)

        to_add = source_all.difference(replica_all)
        to_remove = replica_all.difference(source_all)
        in_both = source_all.intersection(replica_all)

        # Add/update items
        for item in to_add:
            self.copy_item(item)

        # Remove items that no longer exist in the source
        for item in to_remove:
            self.remove_item(item)

        # Update items that exist in both but differ
        for item in in_both:
            src_item = os.path.join(self.source_folder, item)
            rep_item = os.path.join(self.replica_folder, item)
            if os.path.isfile(src_item) and self.files_differ(
                src_item, rep_item
            ):
                self.copy_item(item)

        # Save cache if enabled
        if self.use_hash_cache and not self.dry_run:
            with open(self.hash_cache_file, "w", encoding="utf-8") as f:
                json.dump(self.hash_cache, f)


def setup_logging(log_file_path: str, level: str) -> logging.Logger:
    """
    Configures a logger to record synchronization actions to both
    a file and the console.
    """
    logger = logging.getLogger("folder_sync")
    logger.setLevel(level)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    fh = RotatingFileHandler(
        log_file_path, maxBytes=1024 * 1024, backupCount=5, encoding='utf-8')
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def load_config(config_file: str) -> dict:
    """
    Loads configurations from a JSON file, if it exists.
    """
    if config_file and os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def main():
    """
    Main function to execute the folder synchronization process.

    Steps:
    1. Parse command-line arguments and load configurations.
    2. Validate input paths and ensure the replica folder exists.
    3. Initialize the FolderSynchronizer with specified options.
    4. Start the synchronization loop with the specified interval.
    """
    parser = argparse.ArgumentParser(
        description="Unidirectional folder synchronization script."
        )
    parser.add_argument("source_folder", nargs='?',
                        help="Path to the source folder.")
    parser.add_argument("replica_folder", nargs='?',
                        help="Path to the replica folder.")
    parser.add_argument("sync_interval", nargs='?', type=int,
                        help="Synchronization interval in seconds.")
    parser.add_argument("log_file", nargs='?',
                        help="Path to the log file.")
    parser.add_argument("--use-md5", action="store_true",
                        help=(
                            "Use MD5 hash verification to detect file changes."
                        ))
    parser.add_argument("--use-hash-cache", action="store_true",
                        help="Use a hash cache to improve performance.")
    parser.add_argument("--ignore-file",
                        help="File containing ignore patterns.")
    parser.add_argument("--dry-run", action="store_true",
                        help=(
                            "If enabled, does not modify the replica,"
                            "only logs the actions."
                        ))
    parser.add_argument("--log-level", default="INFO",
                        help=(
                            "Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
                            "Default: INFO"
                        ))
    parser.add_argument("--config-file",
                        help="JSON configuration file to load parameters from")

    args = parser.parse_args()
    config = load_config(args.config_file) if args.config_file else {}

    source_folder = args.source_folder or config.get("source_folder")
    replica_folder = args.replica_folder or config.get("replica_folder")
    sync_interval = (
        args.sync_interval if args.sync_interval is not None
        else config.get("sync_interval", 30)
    )
    log_file = args.log_file or config.get("log_file", "sync.log")
    use_md5 = args.use_md5 or config.get("use_md5", False)
    use_hash_cache = args.use_hash_cache or config.get("use_hash_cache", False)
    ignore_file = args.ignore_file or config.get("ignore_file")
    dry_run = args.dry_run or config.get("dry_run", False)
    log_level = (
        args.log_level.upper() if args.log_level
        else config.get("log_level", "INFO").upper()
    )

    logger = setup_logging(log_file, log_level)

    # Validations
    if not source_folder or not replica_folder:
        logger.error(
            "Source and replica paths are required (via args or config)."
        )
        sys.exit(1)

    if not os.path.exists(source_folder):
        logger.error(f"Source folder '{source_folder}' does not exist.")
        sys.exit(1)

    if sync_interval <= 0:
        logger.error("Sync interval must be a positive integer.")
        sys.exit(1)

    ignore_patterns = []
    if ignore_file:
        if os.path.exists(ignore_file):
            with open(ignore_file, "r", encoding="utf-8") as f:
                for line in f:
                    pattern = line.strip()
                    if pattern:
                        ignore_patterns.append(pattern)
        else:
            logger.warning(
                f"Ignore file '{ignore_file}' not found. "
                "Continuing without ignore patterns."
            )

    if not os.path.exists(replica_folder) and not dry_run:
        try:
            os.makedirs(replica_folder)
        except Exception as e:
            logger.error(
                f"Failed to create replica folder '{replica_folder}': {e}"
            )
            sys.exit(1)

    synchronizer = FolderSynchronizer(
        source_folder=source_folder,
        replica_folder=replica_folder,
        logger=logger,
        use_md5=use_md5,
        use_hash_cache=use_hash_cache,
        ignore_patterns=ignore_patterns,
        dry_run=dry_run
    )

    logger.info("Starting folder synchronization...")
    logger.info(f"Source: {source_folder}")
    logger.info(f"Replica: {replica_folder}")
    logger.info(f"Interval: {sync_interval} seconds")
    logger.info(f"Log file: {log_file}")
    logger.info(f"MD5 verification: {'Yes' if use_md5 else 'No'}")
    logger.info(f"Hash cache: {'Yes' if use_hash_cache else 'No'}")
    logger.info(f"Ignore file: {ignore_file if ignore_file else 'None'}")
    logger.info(f"Dry-run: {'Yes' if dry_run else 'No'}")

    try:
        while True:
            try:
                synchronizer.synchronize()
                logger.info("Synchronization completed.")
            except Exception as e:
                logger.exception(f"Error during synchronization: {e}")
            time.sleep(sync_interval)
    except KeyboardInterrupt:
        logger.info("User requested interruption. Exiting.")


if __name__ == "__main__":
    main()
