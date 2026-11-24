# Contract fixture for the integration tests: a minimal policy at the same
# path deployments use (vo/authz/v1/allow). It decides from the fields the
# package sends, so a change to the input document's shape breaks a test.
# Deployment policies (e.g. the testbed's authz.rego with its ODRL tiers)
# are tested where they live.
package vo.authz.v1

import rego.v1

default allow := false

# Token-less (userpass) admin account.
allow if {
	input.issuer == "root"
	not input.token.sub
}

# Entitlement-based, read-only action.
allow if {
	input.action == "list_requests_history"
	"urn:test:group:reporter:role=member" in input.token.entitlements
}

# kwargs arrive as plain JSON (externalised accounts and enums).
allow if {
	input.action == "attach_dids"
	"urn:test:group:user:role=member" in input.token.entitlements
	some did in input.kwargs.dids
	did.scope == "user.jdoe"
	did.type == "F"
}
