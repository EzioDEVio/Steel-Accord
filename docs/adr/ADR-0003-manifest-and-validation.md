# ADR-0003 Asset manifest + reference validation as a build gate
Status: Accepted
**Decision.** Every file under `content/` and `maps/` has a manifest entry (path, sha256, origin, creator, tool, source/prompt, third-party inputs, licence, ship_status, history). `tools/validate_content.py` checks engine-schema validity (field/module/enum names extracted from the pinned engine source), cross-references, binary formats, manifest coverage and hashes, and BIG contents; build stops on failure. Base-game references are allowed only from an explicit allow-list and are printed every build (B2 target: empty list).
**Self-test.** `tests/test_validator_negative.sh` proves each check fires (11 mutations).
