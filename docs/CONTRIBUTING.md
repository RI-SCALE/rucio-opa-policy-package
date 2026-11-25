# Contributing

Lean on purpose: follow the standards below, keep changes small. This
package runs inside every Rucio server request, so prefer boring, obvious
code over abstractions.

## Layout

```
src/rucio_opa_v1_policy/
  __init__.py      the policy package Rucio loads ([policy] package = ...)
  permission.py    has_permission(): builds the input document, token claims
  opa_client.py    the OPA call; anything but a boolean true is a deny
tests/
  unit/            no network: permission, OPA client, token claims
  integration/     real OPA via testcontainers against policies/contract.rego
docker/            local OPA for `make up`
```

## Rules worth knowing

- **Fail closed:** only a boolean `true` from OPA allows; errors, timeouts
  and anything else deny.
- **Python 3.9** (the Rucio server image): no `match`, no `X | Y` outside
  annotations, no newer stdlib.
- **The input document is a contract** with the deployments' policy (e.g.
  the testbed's [authz.rego](https://github.com/RI-SCALE/dep-dlm-testbed/blob/main/configs/opa/authz.rego)):
  change `tests/integration/policies/contract.rego` and the README example
  with it.
- **No secrets or personal data** in logs or allow-listed `kwargs` (they
  land in OPA's decision log); inputs are logged only with
  `RUCIO_OPA_DEBUG_INPUT=1`.

## Style

- [PEP 8] for layout (ruff), [PEP 257] for docstrings: one line saying
  what, more only when the why isn't obvious.
- Type hints everywhere ([PEP 484]), `from __future__ import annotations`
  at the top.
- Log with `%`-style arguments (`log.info("x=%s", x)`), not f-strings
  ([logging HOWTO][logging]).
- Comments explain why, not what.

## Tests

- Unit tests for every behaviour change, with no network; every new deny
  path gets a test.
- Integration tests when the input document or the OPA call changes
  (`make test-integration`, needs Docker).
- CI (`.github/workflows/ci.yml`) runs `lint`, `typecheck`, `audit`,
  `test-unit` and `test-integration`; run the same make targets locally
  before opening a PR.

## Commits and releases

- [Conventional Commits][cc]: `feat:`, `fix:`, `refactor:`, `chore:`,
  `docs:`, `test:`, `ci:`. Squash-merge PRs with one message describing
  the end state.
- Releases: README, *Releasing*. `pyproject.toml` is the only version
  source; don't add `__version__`.

[PEP 8]: https://peps.python.org/pep-0008/
[PEP 257]: https://peps.python.org/pep-0257/
[PEP 484]: https://peps.python.org/pep-0484/
[logging]: https://docs.python.org/3/howto/logging.html#optimization
[cc]: https://www.conventionalcommits.org/en/v1.0.0/