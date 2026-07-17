"""
============================================================
MINI TEMPLATE — JWT Auth for MCP (XSUAA / IAS on BTP)
============================================================
Use this when: your MCP server is about to go on the public
internet (or even a private CF route real users can reach) and
needs to reject callers who don't hold a valid token issued by
your BTP subaccount's identity service.

How SAP identity services expose JWKS:
  - XSUAA : GET {uaa_url}/token_keys   → JWKS-formatted public keys
  - IAS   : GET {ias_url}/oauth2/certs → JWKS-formatted public keys
  Both are OIDC-adjacent — FastMCP's built-in JWTVerifier can
  validate tokens from either as long as you point it at the
  right jwks_uri / issuer / audience.

Setup:
  pip install fastmcp
  Set XSUAA_URL / XSUAA_XSAPPNAME (or IAS_URL / IAS_AUDIENCE)
  in your .env before running this module standalone.
============================================================
"""

import os
from fastmcp.server.auth.providers.jwt import JWTVerifier


def build_xsuaa_verifier(required_scope: str = None) -> JWTVerifier:
    """
    Build a JWTVerifier that validates tokens issued by an XSUAA
    service instance. XSUAA embeds authorization scopes in the
    token's `scope` claim as "<xsappname>.<ScopeName>" — the
    audience check (via xsappname) stops a token minted for a
    DIFFERENT app in the same subaccount from being accepted here.
    `required_scopes` is enforced natively by JWTVerifier — pass
    the fully-qualified scope string, e.g. "mcp-server!t1234.Invoke".
    """
    uaa_url = os.environ["XSUAA_URL"]           # e.g. https://<sub>.authentication.<region>.hana.ondemand.com
    xsappname = os.environ["XSUAA_XSAPPNAME"]   # e.g. mcp-server-app!t1234

    return JWTVerifier(
        jwks_uri=f"{uaa_url}/token_keys",
        issuer=uaa_url,
        audience=xsappname,
        required_scopes=[required_scope] if required_scope else None,
    )


def build_ias_verifier(required_scope: str = None) -> JWTVerifier:
    """
    Build a JWTVerifier that validates tokens issued by SAP
    Identity Authentication Service (IAS) — the OIDC-native
    alternative to XSUAA, common when the MCP server needs to
    accept end-user (not just technical-user) identities.
    """
    ias_url = os.environ["IAS_URL"]         # e.g. https://<tenant>.accounts.ondemand.com
    audience = os.environ["IAS_AUDIENCE"]   # the OAuth client ID registered in IAS

    return JWTVerifier(
        jwks_uri=f"{ias_url}/oauth2/certs",
        issuer=ias_url,
        audience=audience,
        required_scopes=[required_scope] if required_scope else None,
    )


def build_verifier_from_env() -> JWTVerifier:
    """
    Picks XSUAA or IAS based on which env vars are present. This
    is the single entry point mcp_server_secured.py imports — it
    keeps the "which identity service are we using" decision in
    one place instead of scattered across the codebase.
    """
    required_scope = os.environ.get("MCP_REQUIRED_SCOPE") or None

    if os.environ.get("XSUAA_URL"):
        return build_xsuaa_verifier(required_scope)
    elif os.environ.get("IAS_URL"):
        return build_ias_verifier(required_scope)
    else:
        raise EnvironmentError(
            "No identity service configured — set XSUAA_URL+XSUAA_XSAPPNAME "
            "or IAS_URL+IAS_AUDIENCE in your .env. See .env.example."
        )


if __name__ == "__main__":
    # Standalone sanity check: confirms your env vars are set and
    # the verifier object builds without hitting the network yet
    # (the JWKS fetch itself happens lazily, on the first real
    # token verification — so this script succeeding does NOT
    # prove your JWKS endpoint is reachable, only that config is present).
    verifier = build_verifier_from_env()
    print(f"✅ Built verifier: {type(verifier).__name__}")
    print(f"   issuer   = {verifier.issuer}")
    print(f"   audience = {verifier.audience}")
    print("   (JWKS keys are fetched lazily on first token check, not now)")


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: What's the difference between authentication and authorization
   in this file?
A: JWTVerifier's issuer/audience/signature checks answer "was this
   token genuinely issued by our identity service, unexpired, for
   the right app?" — that's authentication. The `required_scopes`
   check answers "does THIS caller have permission to use THIS
   tool set?" — that's authorization. A token can pass
   authentication and still fail authorization if it lacks the scope.

Q: Why validate `audience` at all — isn't issuer + signature enough?
A: Without an audience check, ANY valid token from your identity
   tenant — including one minted for a completely unrelated app —
   would be accepted. Audience scoping confines a token to the
   specific application it was actually granted for.

Q: Why is JWKS fetched from a URL instead of a hardcoded public key?
A: Identity providers rotate signing keys periodically for
   security. JWKS lets the verifier always fetch (and cache) the
   CURRENT valid key set rather than breaking every time a key
   rotates — a hardcoded key would need a redeploy on every rotation.

Q: XSUAA vs IAS — when would you pick one over the other?
A: XSUAA is BTP's native OAuth authorization server, tightly
   integrated with role collections/scopes and best for
   service-to-service or technical-user calls. IAS is SAP's OIDC
   identity provider, better when you need real end-user identity
   (SSO, user attributes) rather than just an app-level scope.

Q: Why does build_verifier_from_env() raise on missing env vars
   instead of silently returning an unauthenticated server?
A: A silent fallback to "no auth" is exactly the kind of bug that
   ships an unauthenticated production server by accident — failing
   loudly at startup forces the misconfiguration to be caught in
   testing, not discovered later as a security incident.
------------------------------------------------------------
"""
