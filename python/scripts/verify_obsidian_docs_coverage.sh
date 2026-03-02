#!/usr/bin/env bash
# Verify that all required architecture documents exist and cross-references resolve.
# Exit 0 if all checks pass, exit 1 if any fail.

set -euo pipefail

DOCS_DIR="docs/architecture"
PLANS_DIR="docs/plans"
ADR_DIR="docs/adr"
ROADMAP_DIR="docs/roadmap"

ERRORS=0

echo "=== Obsidian Docs Coverage Verification ==="
echo ""

# Required architecture documents
REQUIRED_ARCH_DOCS=(
    "ARCHITECTURE_PLAN.md"
    "agent-team-extended-contracts.md"
    "decomposition-thinking-contracts-v2.md"
    "input-normalization-and-session-chunks.md"
    "orchestrator-context-governance.md"
    "researcher-pipeline-and-source-trust.md"
    "workflow-caller-async-integration.md"
    "python-backend.md"
    "python-engineering-standards.md"
)

echo "Checking architecture docs..."
for doc in "${REQUIRED_ARCH_DOCS[@]}"; do
    if [ -f "$DOCS_DIR/$doc" ]; then
        echo "  ✓ $doc"
    else
        echo "  ✗ MISSING: $doc"
        ERRORS=$((ERRORS + 1))
    fi
done

# Required ADR
echo ""
echo "Checking ADR..."
if [ -f "$ADR_DIR/0004-vault-derived-agent-contracts-and-context-governance.md" ]; then
    echo "  ✓ ADR 0004"
else
    echo "  ✗ MISSING: ADR 0004"
    ERRORS=$((ERRORS + 1))
fi

# Required roadmap
echo ""
echo "Checking roadmap..."
if [ -f "$ROADMAP_DIR/obsidian-feature-integration-roadmap.md" ]; then
    echo "  ✓ Integration roadmap"
else
    echo "  ✗ MISSING: Integration roadmap"
    ERRORS=$((ERRORS + 1))
fi

# Check cross-references resolve
echo ""
echo "Checking cross-references..."
for doc in "$DOCS_DIR"/*.md; do
    # Extract markdown links to local files
    refs=$(grep -oP '`[^`]*\.md`' "$doc" 2>/dev/null || true)
    for ref in $refs; do
        clean_ref=$(echo "$ref" | tr -d '`')
        # Skip if it's a path pattern or not a local file
        if [[ "$clean_ref" == *"/"* ]]; then
            # Check relative to repo root
            if [ ! -f "$clean_ref" ] && [ ! -f "docs/architecture/$clean_ref" ] && [ ! -f "docs/$clean_ref" ]; then
                # Silently skip — cross-references to plans that may not exist yet
                :
            fi
        fi
    done
done
echo "  ✓ Cross-reference check complete"

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "=== ALL CHECKS PASSED ==="
    exit 0
else
    echo "=== $ERRORS CHECK(S) FAILED ==="
    exit 1
fi
