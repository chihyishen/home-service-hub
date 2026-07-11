package com.inventory.item.config;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;

class ResourceServerSecurityConfigTest {
    @Test
    void buildsDecoderWithInternalJwksAndExternalIssuerValidation() {
        ResourceServerSecurityConfig config = new ResourceServerSecurityConfig();
        NimbusJwtDecoder decoder = config.inventoryJwtDecoder(
                "https://identity.example/realms/home-service-hub",
                "http://keycloak:8080/realms/home-service-hub/protocol/openid-connect/certs",
                "home-service-api");
        assertThat(decoder).isNotNull();
    }
}
