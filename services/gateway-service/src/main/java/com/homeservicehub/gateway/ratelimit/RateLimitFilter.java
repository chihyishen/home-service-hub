package com.homeservicehub.gateway.ratelimit;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import io.github.bucket4j.Bandwidth;
import io.github.bucket4j.Bucket;
import io.github.bucket4j.ConsumptionProbe;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.HexFormat;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.filter.OncePerRequestFilter;

public class RateLimitFilter extends OncePerRequestFilter {
    private static final Logger LOG = LoggerFactory.getLogger(RateLimitFilter.class);
    private final Cache<String, Bucket> buckets = Caffeine.newBuilder().expireAfterAccess(1, TimeUnit.HOURS).maximumSize(10_000).build();
    private final long capacity;
    private final long refill;

    public RateLimitFilter(long capacity, long refill) { this.capacity = capacity; this.refill = refill; }

    @Override protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain) throws ServletException, IOException {
        String route = routeClass(request.getRequestURI());
        String identity = trustedIdentity(request);
        Bucket bucket = buckets.get(identity + ":" + route, ignored -> Bucket.builder().addLimit(
                Bandwidth.builder().capacity(capacity).refillGreedy(refill, Duration.ofMinutes(1)).build()).build());
        ConsumptionProbe probe = bucket.tryConsumeAndReturnRemaining(1);
        if (!probe.isConsumed()) {
            String correlation = String.valueOf(request.getAttribute("correlationId"));
            response.setStatus(429);
            response.setContentType("application/json");
            response.setHeader("Retry-After", String.valueOf(Math.max(1, Duration.ofNanos(probe.getNanosToWaitForRefill()).toSeconds())));
            response.getWriter().write("{\"error\":\"rate_limited\",\"correlationId\":\"" + correlation + "\"}");
            LOG.warn("rate_limit.rejected route={} key_hash={}", route, hash(identity));
            return;
        }
        chain.doFilter(request, response);
    }

    String trustedIdentity(HttpServletRequest request) {
        return "source:" + request.getRemoteAddr();
    }

    String routeClass(String path) {
        if (path.startsWith("/images/")) return "image";
        if (path.startsWith("/api/")) return "business";
        return "unknown";
    }

    private String hash(String value) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)), 0, 8); }
        catch (Exception ignored) { return "unavailable"; }
    }
}
