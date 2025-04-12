# Test Bundles Directory

This directory is used for storing test bundles during development and testing.

- Test bundles can be placed here for manual testing
- Some integration tests look for bundles in this directory

This directory is intentionally empty in the repository, but tests that need actual bundles will be skipped if none are found here.

For automated tests, use the test fixtures in `tests/fixtures` instead.