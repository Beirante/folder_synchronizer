
# Folder Synchronizer

## Overview
Folder Synchronizer is a Python script that ensures a unidirectional synchronization between a source folder and a replica folder. It maintains an exact copy of the source folder at the replica location, periodically updating based on changes.

## Features
- **File Synchronization**: Mirrors the source folder to the replica.
- **Periodic Updates**: Syncs at specified intervals.
- **MD5-based Comparison**: Optional file comparison using MD5 hashes.
- **Hash Caching**: Optionally caches file hashes for improved performance.
- **Ignore Patterns**: Exclude specific files or directories from synchronization.
- **Dry-Run Mode**: Simulates operations without modifying the replica folder.
- **Logging**: Logs operations to both the console and a log file.

## Directory Structure
```
synchronizer_project
│
├── src/
│   ├── synchronizer.py          # Main synchronization logic
│   ├── __init__.py              # Package initializer
│   ├── __pycache__/             # Compiled Python files
│
├── source_folder/               # Example source folder
│   ├── teste_txtfile.txt
│   ├── test_image.jpg
│   ├── test_wordfile.docx
│
├── replica_folder/              # Example replica folder
│   ├── teste_txtfile.txt
│   ├── test_image.jpg
│   ├── test_wordfile.docx
│
├── tests/                       # Testing folder
│   ├── test_integration.py      # Integration test
│   ├── test_synchronizer_unit.py # Unit tests
│   ├── __init__.py
│   ├── .pytest_cache/           # pytest cache files
│
├── logfile.log                  # Example log file
├── pytest.ini                   # pytest configuration
├── .vscode/
│   ├── launch.json              # Debugging configuration
```

## Usage
### Running the Program
1. **Navigate to the Project Directory**:
   ```bash
   cd synchronizer_project
   ```

2. **Run the Synchronizer**:
   ```bash
   python src/synchronizer.py source_folder replica_folder 30 logfile.log
   ```
   - `source_folder`: Path to the source folder.
   - `replica_folder`: Path to the replica folder.
   - `30`: Synchronization interval in seconds.
   - `logfile.log`: Path to the log file.

3. **Dry-Run Mode**:
   To simulate the synchronization without making changes to the replica folder:
   ```bash
   python src/synchronizer.py source_folder replica_folder 30 logfile.log --dry-run
   ```

4. **Ignore Patterns**:
   Create an `ignore.txt` file with patterns to exclude (e.g., `.tmp` files):
   ```
   *.tmp
   ignore_this/
   ```
   Then run:
   ```bash
   python src/synchronizer.py source_folder replica_folder 30 logfile.log --ignore-file ignore.txt
   ```

5. **Using a Configuration File**:
   Specify all settings in a JSON configuration file (e.g., `config.json`):
   ```json
   {
       "source_folder": "source_folder",
       "replica_folder": "replica_folder",
       "sync_interval": 30,
       "log_file": "logfile.log",
       "ignore_patterns": ["*.tmp", "ignore_this/"]
   }
   ```
   Run the synchronizer with:
   ```bash
   python src/synchronizer.py --config-file config.json
   ```

### Running Tests
1. **Run All Tests**:
   ```bash
   pytest tests/
   ```

2. **Run Specific Test**:
   For unit tests:
   ```bash
   pytest tests/test_synchronizer_unit.py
   ```
   For integration tests:
   ```bash
   pytest tests/test_integration.py
   ```

## Installing Dependencies
This project requires `pytest` for running the tests. Install it using pip:
```bash
pip install pytest
```

## Debugging
The `.vscode/launch.json` file is included for debugging. Open the project in Visual Studio Code and use the predefined configurations to debug the script.


### Example: Using MD5 and Hash Caching
MD5 file comparison and hash caching can improve synchronization precision and performance.

1. **Enable MD5 Comparison**:
   Use the `--use-md5` option to compare files using their MD5 hash:
   ```bash
   python src/synchronizer.py source_folder replica_folder 30 logfile.log --use-md5
   ```

2. **Enable Hash Caching**:
   Use the `--use-hash-cache` option to cache file hashes for subsequent synchronizations:
   ```bash
   python src/synchronizer.py source_folder replica_folder 30 logfile.log --use-hash-cache
   ```

3. **Combine Both Features**:
   To use both MD5 comparison and hash caching:
   ```bash
   python src/synchronizer.py source_folder replica_folder 30 logfile.log --use-md5 --use-hash-cache
   ```

   This will compute MD5 hashes for files and store them in a cache for faster checks in subsequent runs. The cache is saved in the replica folder as `hash_cache.json`.
