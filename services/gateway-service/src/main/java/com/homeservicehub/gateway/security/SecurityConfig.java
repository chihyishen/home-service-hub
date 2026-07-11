package com.homeservicehub.gateway.security;

import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.convert.converter.Converter;
import org.springframework.http.MediaType;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoders;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.oauth2.server.resource.web.authentication.BearerTokenAuthenticationFilter;
import com.homeservicehub.gateway.ratelimit.RateLimitFilter;

@Configuration
public class SecurityConfig {
    @Bean
    JwtDecoder jwtDecoder(@Value("${security.oidc.issuer-uri}") String issuer,
                          @Value("${security.oidc.audience}") String audience,
                          @Value("${security.oidc.jwk-set-uri:}") String jwkSetUri) {
        // Prefer the internal HTTP JWKS endpoint so the gateway never has to trust
        // the issuer's public TLS certificate (mkcert CA lives only on user devices).
        NimbusJwtDecoder decoder = jwkSetUri.isBlank()
                ? (NimbusJwtDecoder) JwtDecoders.fromIssuerLocation(issuer)
                : NimbusJwtDecoder.withJwkSetUri(jwkSetUri).build();
        OAuth2TokenValidator<Jwt> validator = new DelegatingOAuth2TokenValidator<>(
                JwtValidators.createDefaultWithIssuer(issuer), new AudienceValidator(audience));
        decoder.setJwtValidator(validator);
        return decoder;
    }

    @Bean
    SecurityFilterChain security(HttpSecurity http, RateLimitFilter rateLimitFilter) throws Exception {
        http.csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/minio/inventory-items/**", "/otlp/v1/traces").permitAll()
                .requestMatchers("/actuator/health/liveness", "/actuator/health/readiness").permitAll()
                .requestMatchers("/api/items/**", "/api/shopping-list/**").access((authentication, context) ->
                    new org.springframework.security.authorization.AuthorizationDecision(hasScopeForMethod(authentication.get(), context.getRequest().getMethod(), "inventory")))
                .requestMatchers("/api/accounting/**").access((authentication, context) ->
                    new org.springframework.security.authorization.AuthorizationDecision(hasScopeForMethod(authentication.get(), context.getRequest().getMethod(), "accounting")))
                .requestMatchers("/api/portfolio/**").access((authentication, context) ->
                    new org.springframework.security.authorization.AuthorizationDecision(hasScopeForMethod(authentication.get(), context.getRequest().getMethod(), "portfolio")))
                .anyRequest().denyAll())
            .oauth2ResourceServer(oauth -> oauth.jwt(jwt -> jwt.jwtAuthenticationConverter(jwtAuthenticationConverter()))
                .authenticationEntryPoint((req, res, ex) -> writeError(res, 401, "unauthorized", req.getAttribute("correlationId")))
                .accessDeniedHandler((req, res, ex) -> writeError(res, 403, "forbidden", req.getAttribute("correlationId"))))
            .headers(headers -> headers.contentTypeOptions(Customizer.withDefaults()));
        http.addFilterAfter(rateLimitFilter, BearerTokenAuthenticationFilter.class);
        return http.build();
    }

    boolean hasScopeForMethod(org.springframework.security.core.Authentication authentication, String method, String service) {
        String suffix = (method.equals("GET") || method.equals("HEAD")) ? "read" : "write";
        if (authentication == null) return false;
        boolean scoped = authentication.getAuthorities().stream()
                .anyMatch(a -> a.getAuthority().equals("SCOPE_" + service + "." + suffix));
        if (authentication.getPrincipal() instanceof Jwt jwt && "home-service-ui".equals(jwt.getClaimAsString("azp"))) {
            boolean household = authentication.getAuthorities().stream().anyMatch(a ->
                    a.getAuthority().equals("ROLE_household-user") || a.getAuthority().equals("ROLE_household-admin"));
            if (!household) return false;
        }
        if (method.equals("DELETE") && service.equals("portfolio")) {
            return scoped && authentication.getAuthorities().stream()
                    .anyMatch(a -> a.getAuthority().equals("ROLE_household-admin"));
        }
        return scoped;
    }

    private JwtAuthenticationConverter jwtAuthenticationConverter() {
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(jwt -> {
            java.util.List<GrantedAuthority> authorities = new java.util.ArrayList<>();
            String scope = jwt.getClaimAsString("scope");
            if (scope != null) for (String value : scope.split(" ")) authorities.add(new SimpleGrantedAuthority("SCOPE_" + value));
            Map<String, Object> realmAccess = jwt.getClaim("realm_access");
            if (realmAccess != null && realmAccess.get("roles") instanceof java.util.Collection<?> roles)
                roles.forEach(role -> authorities.add(new SimpleGrantedAuthority("ROLE_" + role)));
            return authorities;
        });
        return converter;
    }

    private void writeError(HttpServletResponse response, int status, String code, Object correlationId) throws IOException {
        response.setStatus(status);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        String id = correlationId == null ? "unknown" : correlationId.toString().replaceAll("[^A-Za-z0-9-]", "");
        response.getWriter().write("{\"error\":\"" + code + "\",\"correlationId\":\"" + id + "\"}");
    }
}
