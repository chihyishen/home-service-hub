package com.homeservicehub.gateway.ratelimit;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.core.context.SecurityContextHolder;

class RateLimitFilterTest {
    @AfterEach void clear() { SecurityContextHolder.clearContext(); }

    @Test void rejectsBurstWithStableResponseAndRetryAfter() throws Exception {
        RateLimitFilter filter = new RateLimitFilter(1, 1);
        MockHttpServletRequest first = request("/api/items", "10.0.0.2");
        filter.doFilter(first, new MockHttpServletResponse(), (req, res) -> {});
        MockHttpServletResponse rejected = new MockHttpServletResponse();
        filter.doFilter(request("/api/items", "10.0.0.2"), rejected, (req, res) -> {});
        assertThat(rejected.getStatus()).isEqualTo(429);
        assertThat(rejected.getHeader("Retry-After")).isNotBlank();
        assertThat(rejected.getContentAsString()).contains("rate_limited").doesNotContain("10.0.0.2");
    }

    @Test void separatesRouteClassesAndIgnoresSpoofedForwardingAddress() throws Exception {
        RateLimitFilter filter = new RateLimitFilter(1, 1);
        MockHttpServletRequest business = request("/api/items", "10.0.0.2");
        business.addHeader("X-Forwarded-For", "203.0.113.9");
        filter.doFilter(business, new MockHttpServletResponse(), (req, res) -> {});
        MockHttpServletResponse telemetry = new MockHttpServletResponse();
        filter.doFilter(request("/otlp/v1/traces", "10.0.0.2"), telemetry, (req, res) -> {});
        assertThat(telemetry.getStatus()).isEqualTo(200);
        MockHttpServletResponse sameSource = new MockHttpServletResponse();
        filter.doFilter(request("/api/items", "10.0.0.2"), sameSource, (req, res) -> {});
        assertThat(sameSource.getStatus()).isEqualTo(429);
    }

    private MockHttpServletRequest request(String path, String address) {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", path);
        request.setRemoteAddr(address);
        request.setAttribute("correlationId", "test-id");
        return request;
    }
}
