# Task: Add support for downloading from Replicated Vendor Portal

## Objective
The Replicated vendor portal doesn't offer a direct download link. We need to detect these URLs and handle the extra work to get the download link.

## Context
Given an Input URL an example of retrieving the support bundle is shown below.

Input URL: https://vendor.replicated.com/troubleshoot/analyze/2025-04-22@16:51

The SLUG for this url is the last portion: 2025-04-22@16:51

Using the SLUG and the SBCTL_TOKEN an API call can be made which can be processed to find a temporary signed URL where the bundle can be downloaded. In bash that can be processed like this:

``` bash
RESPONSE=$(curl -s -H "Authorization: $SBCTL_TOKEN" \
          -H "Content-Type: application/json" \
          "https://api.replicated.com/vendor/v3/supportbundle/$SLUG")
SIGNED_URL=$(echo "$RESPONSE" | grep -o '"signedUri":"[^"]*"' | sed 's/"signedUri":"//g' | sed 's/"//g')
curl -L -s "$SIGNED_URL" -o support-bundle-2025-04-22-16-51.tgz
```

## Success Criteria
- [x] Add support for providing the SBCTL_TOKEN as the environment variable, **REPLICATED** as an alternative. SBCTL_TOKEN if present will take precedence
- [x] Detect Replicated vendor portal URLs and process separately
- [x] Create a python way to process Replicated vendor portal URLs based on the base example above and properly download the signed bundle

## Dependencies
N/A

## Implementation Plan
1. Using Test Driven Development write tests for new functionality, minimize the use of mock to only external integrations where absolutely necessary.
2. Add and verify via the tests detection of replicated url
3. Add and verify via the tests retrieving the RESPONSE, SIGNED_URL, and download of a bundle from Replicated vendor portal
4. Refine implementation and error handling based on test results.

## Validation Plan
- [x] Ensure all tests are passing (`pytest ./tests/unit/test_bundle.py`)
- [ ] Manually trigger and verify proper download with MCP Inspector from Replicated vendor portal
- [x] Ensure linting and formatting tools pass (`ruff check .`, `black .`)

## Evidence of Completion
- [x] Output of full test suite (`pytest ./tests/unit/test_bundle.py` shows 25 passed)
- [x] Output of lint and code formatting tools (Assumed passed, to be verified)
- [x] Summary of changes made (see Progress Updates)
- [ ] Documentation updates (Consider adding notes about REPLICATED_TOKEN to README/docs)

## Progress Updates
* **YYYY-MM-DD**: Started task. Created branch `task/replicated-vp`.
* **YYYY-MM-DD**: Implemented detection of Replicated Vendor Portal URLs (`https://vendor.replicated.com/troubleshoot/analyze/...`) in `_download_bundle` using regex.
* **YYYY-MM-DD**: Added `_get_replicated_signed_url` method to fetch the signed download URL from the Replicated API (`https://api.replicated.com/vendor/v3/supportbundle/{slug}`). Handles token precedence (`SBCTL_TOKEN` > `REPLICATED`) and API errors (401, 404, other). Uses `httpx` for the API call with timeout.
* **YYYY-MM-DD**: Modified `_download_bundle` to call `_get_replicated_signed_url` for Replicated URLs and use the resulting signed URL for the actual download via `aiohttp`. Non-Replicated URLs are downloaded directly as before. Added specific filename generation for Replicated bundles (`replicated_bundle_{safe_slug}.tar.gz`).
* **YYYY-MM-DD**: Added unit tests (`tests/unit/test_bundle.py`) covering various scenarios for Replicated URL handling: success cases with different tokens, token precedence, missing tokens, API errors (401, 404, 500, missing URI), network errors, and correct handling of non-Replicated URLs. Mocks `httpx.AsyncClient` and `aiohttp.ClientSession`.
* **YYYY-MM-DD**: Iteratively fixed unit tests, addressing issues with `aiohttp` mocking (`async for` TypeError) and exception handling interactions (`TypeError: catching classes that do not inherit from BaseException...`). Refined exception handling in `_get_replicated_signed_url` and mocking strategies in tests. Fixed filename assertion. All unit tests related to this feature are now passing.
