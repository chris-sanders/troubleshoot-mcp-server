#!/bin/bash
set -euo pipefail

# Generate temporary melange signing keys for testing
# These keys are only used for testing builds and should never be used for production

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Key files
PRIVATE_KEY="$PROJECT_ROOT/melange-test.rsa"
PUBLIC_KEY="$PROJECT_ROOT/melange-test.rsa.pub"

echo "Generating temporary melange signing keys for testing..."

# Check if keys already exist
if [[ -f "$PRIVATE_KEY" && -f "$PUBLIC_KEY" ]]; then
    echo "Test keys already exist, skipping generation"
    echo "Private key: $PRIVATE_KEY"
    echo "Public key: $PUBLIC_KEY"
    exit 0
fi

# Generate RSA key pair
if ! command -v openssl &> /dev/null; then
    echo "ERROR: openssl is required to generate test keys"
    exit 1
fi

# Generate private key
openssl genrsa -out "$PRIVATE_KEY" 2048

# Generate public key
openssl rsa -in "$PRIVATE_KEY" -pubout -out "$PUBLIC_KEY"

# Set appropriate permissions
chmod 600 "$PRIVATE_KEY"
chmod 644 "$PUBLIC_KEY"

echo "✅ Generated test signing keys:"
echo "Private key: $PRIVATE_KEY"
echo "Public key: $PUBLIC_KEY"
echo ""
echo "⚠️  IMPORTANT: These are temporary test keys only!"
echo "   - They are ignored by git (.gitignore)"
echo "   - They should never be used for production builds"
echo "   - Real production builds use the MELANGE_RSA secret"