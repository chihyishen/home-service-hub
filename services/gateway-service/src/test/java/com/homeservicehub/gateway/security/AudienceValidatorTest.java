package com.homeservicehub.gateway.security;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.security.oauth2.jwt.Jwt;

class AudienceValidatorTest {
    @Test
    void acceptsRequiredAudience() {
        Jwt jwt = new Jwt("token", Instant.now(), Instant.now().plusSeconds(60),
                Map.of("alg", "none"), Map.of("aud", List.of("home-service-api")));
        assertThat(new AudienceValidator("home-service-api").validate(jwt).hasErrors()).isFalse();
    }

    @Test
    void rejectsWrongAudience() {
        Jwt jwt = new Jwt("token", Instant.now(), Instant.now().plusSeconds(60),
                Map.of("alg", "none"), Map.of("aud", List.of("another-api")));
        assertThat(new AudienceValidator("home-service-api").validate(jwt).hasErrors()).isTrue();
    }
}
