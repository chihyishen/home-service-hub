package com.homeservicehub.gateway.security;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;

class SecurityConfigTest {
    private final SecurityConfig config = new SecurityConfig();

    private JwtAuthenticationToken token(String azp, List<String> scopes, List<String> roles) {
        Jwt jwt = new Jwt("token", Instant.now(), Instant.now().plusSeconds(60), Map.of("alg", "none"),
                Map.of("sub", "subject", "azp", azp, "scope", String.join(" ", scopes), "realm_access", Map.of("roles", roles)));
        var authorities = new java.util.ArrayList<SimpleGrantedAuthority>();
        scopes.forEach(scope -> authorities.add(new SimpleGrantedAuthority("SCOPE_" + scope)));
        roles.forEach(role -> authorities.add(new SimpleGrantedAuthority("ROLE_" + role)));
        return new JwtAuthenticationToken(jwt, authorities);
    }

    @Test void uiRequiresHouseholdRole() {
        assertThat(config.hasScopeForMethod(token("home-service-ui", List.of("inventory.read"), List.of()), "GET", "inventory")).isFalse();
        assertThat(config.hasScopeForMethod(token("home-service-ui", List.of("inventory.read"), List.of("household-user")), "GET", "inventory")).isTrue();
    }

    @Test void scopedAgentDoesNotRequireHouseholdRole() {
        assertThat(config.hasScopeForMethod(token("agent-one", List.of("accounting.read"), List.of()), "GET", "accounting")).isTrue();
    }

    @Test void portfolioDeleteRequiresAdminAndWriteScope() {
        assertThat(config.hasScopeForMethod(token("home-service-ui", List.of("portfolio.write"), List.of("household-user")), "DELETE", "portfolio")).isFalse();
        assertThat(config.hasScopeForMethod(token("home-service-ui", List.of("portfolio.write"), List.of("household-admin")), "DELETE", "portfolio")).isTrue();
    }
}
