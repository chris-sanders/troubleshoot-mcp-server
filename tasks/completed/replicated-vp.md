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
- [x] Add support for providing the SBCTL_TOKEN as the environment REPLICATED, SBCTL_TOKEN if present will take precedence
- [x] Detect Replicated vendor portal URLs and process separately
- [x] Create a python way to process Replicated vendor portal URLs based on the base example above and properly download the signed bundle

## Dependencies
N/A

## Implementation Plan
1. Using Test Driven Development write tests for new functionality, minimize the use of mock to only external integrations where absolutely necessary.
2. Add and verify via the tests detection of replicated url
3. Add and verify via the tests retrieving the RESPONSE, SIGNED_URL, and download of a bundle from Replicated vendor portal

## Validation Plan
- Ensure all tests are passing
- Manually trigger and verify proper download with MCP Inspector from Replicated vendor portal

## Evidence of Completion
- [x] Output of full test suite
- [x] Output of lint and code formatting tools
- [x] Summary of changes made, including documentation updates

## Implementation Summary
### Key Changes
1. **URL Detection and Processing**
   - Implemented URL pattern detection for Replicated vendor portal URLs
   - Added slug extraction from portal URLs to use in API requests
   - Created a dedicated download flow specific to Replicated URLs

2. **Authentication Handling**
   - Added support for `REPLICATED` environment variable for authentication tokens
   - Maintained compatibility with existing `SBCTL_TOKEN` variable
   - Implemented token precedence logic where `SBCTL_TOKEN` takes priority if both are present

3. **API Integration**
   - Implemented API calls to Replicated's vendor API to retrieve signed download URLs
   - Added proper error handling for API responses
   - Integrated the API flow with the existing download functionality

4. **Testing**
   - Created comprehensive test suite following Test-Driven Development principles
   - Implemented tests for URL detection, authentication, API response parsing, error handling, and end-to-end download flow

5. **Files Changed**
   - `bundle.py`: Added Replicated URL detection and handling methods
   - `config.py`: Updated recommended client configuration
   - `DOCKER.md`: Updated documentation for container usage
   - Added new test file: `test_replicated_vendor_portal.py`

## Progress Updates
* Created comprehensive test suite for all aspects of Replicated Vendor Portal support
* Implemented the Replicated URL detection and slug extraction
* Added authentication token handling (SBCTL_TOKEN takes precedence over REPLICATED)
* Implemented API call to get the signed URL for bundle download
* Added proper error handling for all potential API issues
* Updated documentation to include the new functionality
* All tests are passing, and code formatting is clean
* Made sure the Docker configuration and documentation are updated to include the new REPLICATED environment variable
* Recursive call issue in the download_bundle method was fixed for reliable integration testing
* Fixed the URL extraction to handle the actual Replicated API response format with nested bundle object
* Added new test for original format support to ensure backward compatibility
* Fixed issues with direct S3 URL download by implementing a custom download function specific to Replicated bundles
* Updated tests to use proper async mocking for the download process
* Added URL sanitization to remove spaces in URLs, fixing issue with improperly formatted log output
* Enhanced URL handling to properly parse and extract slugs from URLs with spaces
* Added tests to verify sanitization works correctly with various URL formats
* Implemented a robust download strategy using httpx which correctly handles S3 signed URLs
* Added additional logging and error handling to make debugging easier
* Improved the filename generation to include the slug for better identification
* Successfully simplified the implementation by removing subprocess-based curl approach
* Standardized on a single HTTP client (httpx) throughout the codebase
* Removed all aiohttp usage in favor of consistent httpx implementation
* Removed multiple download approaches in favor of a single reliable one
* Ensured all tests pass with the simplified implementation
* Added appropriate error handling and diagnostics for the simplified approach
