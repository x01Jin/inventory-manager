# Development Guide

Running Tests

- Test helper scripts are available in the `tests/` folder. They help populate sample items, requesters and requisitions for test and profiling.

Contributing

- Follow the repository style. Open a PR with a description of changes, update docs and add tests for features where appropriate.

Debugging

- Use the logger in `inventory_app/utils/logger.py` and run with a console to capture the output.

Packaging

- Use `PyInstaller` to package the GUI into an executable. The existing `build/` folder contains artifacts and references to build processes.

Notes on Schema Changes

- For schema updates, update `inventory_app/database/schema.sql` and add migrations to populate or alter fields if required.
