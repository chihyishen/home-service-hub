#!/bin/sh
set -eu
realm=${1:-infra/keycloak/realm-home-service-hub.json}
jq -e '
  .registrationAllowed == false and
  ([.clientScopes[] | select(.name == "home-service-api-audience") | .protocolMappers[] | select(.protocolMapper == "oidc-audience-mapper") | .config["included.custom.audience"]] | index("home-service-api") != null) and
  ([.clients[] | select(.clientId == "home-service-ui") | .defaultClientScopes[]] | index("home-service-api-audience") != null) and
  ([.clients[] | select(.clientId == "home-service-smoke-agent") | .defaultClientScopes[]] | index("home-service-api-audience") != null)
' "$realm" >/dev/null
