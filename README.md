# rucio-opa-policy-package

Rucio policy package that delegates permission checks to [OPA](https://www.openpolicyagent.org/),
deciding by the token's claims. Used by the RI-SCALE DEP DLM
[testbed](https://github.com/RI-SCALE/dep-dlm-testbed) and deployment. Supports Rucio 35 and later.

## How it works

Rucio calls `has_permission(issuer, action, kwargs)`; the package builds an input document
and asks OPA. Only a boolean `true` allows; anything else, including errors, denies.

```json
{
  "issuer": "root",
  "action": "add_rule",
  "token": {"entitlements": ["urn:..."], "sub": "...", "iss": "...", "aud": "...", "acr": "..."},
  "kwargs": {"account": "jdoe"}
}
```

- `token` comes from the decoded JWT of the request (`request.environ["token_claims"]`, set by
  the patched Rucio REST layer). Entitlements are read from `entitlements`, then
  `eduperson_entitlement`, then the issuer's userinfo endpoint (cached per token).
- `kwargs` (an allow-listed subset) are available to the policy and land in OPA's decision log;
  the testbed's policy decides without them.
- The Rego policy lives with the deployment (e.g. `configs/opa/authz.rego` in the testbed).

## Configuration

Rucio (`rucio.cfg`):

```ini
[policy]
package = rucio_opa_v1_policy
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPA_URL` | `http://localhost:8181` | OPA base URL |
| `OPA_POLICY_PATH` | `vo/authz/v1/allow` | Rule queried under `/v1/data/`; must evaluate to a boolean |
| `OPA_TIMEOUT` | `2` | OPA request timeout (s) |
| `RUCIO_OPA_USERINFO_TIMEOUT` | `3` | Userinfo request timeout (s) |
| `RUCIO_OPA_DEBUG_INPUT` | off | `1`: log every input document at WARNING |

## Development

Needs [uv](https://docs.astral.sh/uv/). Targets Python 3.9 (Rucio server image) and later.

```bash
make sync lint typecheck audit test-unit   # no Docker needed
make test-integration                      # real OPA via testcontainers (Docker)
```

The integration tests run against a minimal contract policy in `tests/integration/policies/`.
To reuse a running OPA: `make up`, then
`POLICY_TEST_OPA_URL=http://localhost:8181 make test-integration`.

## Releasing

Bump the version in `pyproject.toml`, commit, push a `vX.Y.Z` tag; `release.yml`
checks that tag and version match, builds wheel and sdist with provenance
attestation and creates the GitHub Release.

```bash
uv version X.Y.Z
git commit -am "chore(release): X.Y.Z"
git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin main vX.Y.Z
```

Wheel: `https://github.com/RI-SCALE/rucio-opa-policy-package/releases/download/vX.Y.Z/rucio_opa_v1_policy-X.Y.Z-py3-none-any.whl`.

Verify (needs gh auth login or GH_TOKEN):

```bash
gh attestation verify rucio_opa_v1_policy-X.Y.Z-py3-none-any.whl --repo RI-SCALE/rucio-opa-policy-package
```