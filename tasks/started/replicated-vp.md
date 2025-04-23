# Task: Add support for downloading from Replicated Vendor Portal

## Objective
The Replicated vendor portal doesn't offer a direct download link. We need to detect these URLs and hanlde the extra work to get the download link.

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
- [ ] Add support for providing the SBCTL_TOKEN as the environment REPLICATED, SBCTL_TOKEN if present will take precedence
- [ ] Detect Replicated vendor portal URLs and process separately
- [ ] Create a python way to process Replicated vendor portal URLs based on the base example above and properly download the signed bundle

## Dependencies
N/A

## Implementation Plan
1. Using Test Driven Development write tests for new functionality, minimize the use of mock to only external integrations where absolutely necessary.
2. Add and verify via the tests detection of replicated url
3. Add and verify via the tests retrieving the RESPONSE, SIGNED_URL, and download of a bundle from Replicated vendor portal
4. ...

## Validation Plan
- Ensure all tests are passing
- Manually trigger and verify proper download with MCP Inspector from Replicated vendor portal
- ...

## Evidence of Completion
- [ ] Output of full test suite
- [ ] Output of lint and code formatting tools
- [ ] Summary of changes made, including documenation updates
- [ ] ...


## Progress Updates
(To be filled by AI during implementation)
* ...
