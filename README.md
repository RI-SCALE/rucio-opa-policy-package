# rucio-opa-policy-package

Rucio policy package that delegates permission checks to [OPA](https://www.openpolicyagent.org/),
deciding by the token's claims (role-based, ADR-008). Used by the RI-SCALE DEP DLM
[testbed](https://github.com/RI-SCALE/dep-dlm-testbed) and deployment.

## How it works

Rucio calls `has_permission(issuer, action, kwargs)`; the package builds an input document
and asks OPA. Any error fails closed (deny).

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
- `kwargs` are forwarded for OPA's decision log only; the policy does not read them.
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
| `OPA_POLICY_PATH` | `vo/authz/v1/allow` | Rule queried under `/v1/data/` |
| `OPA_TIMEOUT` | `2` | OPA request timeout (s) |
| `RUCIO_OPA_USERINFO_TIMEOUT` | `3` | Userinfo request timeout (s) |
| `RUCIO_OPA_DEBUG_INPUT` | off | `1`: log every input document at WARNING |

## Development

Needs [uv](https://docs.astral.sh/uv/). Targets Python 3.9 (Rucio server image) and later.

```bash
make sync lint typecheck test
```

## Releasing

Bump `version` in `pyproject.toml`, commit, push a `vX.Y.Z` tag; `release.yml` checks the
version, builds wheel and sdist and creates the GitHub Release. Consumers vendor a tag
(e.g. `make vendor-policy-package POLICY_PKG_REF=vX.Y.Z` in the testbed).
