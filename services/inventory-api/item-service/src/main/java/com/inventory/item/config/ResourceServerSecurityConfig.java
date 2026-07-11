package com.inventory.item.config;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.convert.converter.Converter;
import org.springframework.security.authorization.AuthorizationDecision;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2TokenValidatorResult;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoders;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@ConditionalOnProperty(name = "security.oauth2.enforcement-enabled", havingValue = "true")
public class ResourceServerSecurityConfig {
    @Bean
    NimbusJwtDecoder inventoryJwtDecoder(@Value("${security.oauth2.issuer-uri}") String issuer,
                                         @Value("${security.oauth2.jwk-set-uri}") String jwkSetUri,
                                         @Value("${security.oauth2.audience:home-service-api}") String audience) {
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withJwkSetUri(jwkSetUri).build();
        decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(JwtValidators.createDefaultWithIssuer(issuer), jwt ->
                jwt.getAudience().contains(audience) ? OAuth2TokenValidatorResult.success() :
                        OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "Required audience missing", null))));
        return decoder;
    }

    @Bean
    SecurityFilterChain inventorySecurity(HttpSecurity http) throws Exception {
        http.csrf(csrf -> csrf.disable()).authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health/**").permitAll()
                .requestMatchers("/api/items/**", "/api/shopping-list/**").access((authentication, context) -> {
                    String suffix = switch (context.getRequest().getMethod()) { case "GET", "HEAD" -> "read"; default -> "write"; };
                    boolean allowed = authentication.get().getAuthorities().stream().anyMatch(a -> a.getAuthority().equals("SCOPE_inventory." + suffix));
                    if (authentication.get().getPrincipal() instanceof Jwt jwt && "home-service-ui".equals(jwt.getClaimAsString("azp"))) {
                        Map<String, Object> realm = jwt.getClaim("realm_access");
                        allowed = allowed && realm != null && realm.get("roles") instanceof Collection<?> roles &&
                                roles.stream().anyMatch(role -> role.equals("household-user") || role.equals("household-admin"));
                    }
                    return new AuthorizationDecision(allowed);
                }).anyRequest().denyAll())
                .oauth2ResourceServer(oauth -> oauth.jwt(jwt -> jwt.jwtAuthenticationConverter(jwtConverter())));
        return http.build();
    }

    private JwtAuthenticationConverter jwtConverter() {
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(jwt -> {
            Collection<GrantedAuthority> result = new ArrayList<>();
            String scope = jwt.getClaimAsString("scope");
            if (scope != null) for (String value : scope.split(" ")) result.add(new SimpleGrantedAuthority("SCOPE_" + value));
            return result;
        });
        return converter;
    }
}
