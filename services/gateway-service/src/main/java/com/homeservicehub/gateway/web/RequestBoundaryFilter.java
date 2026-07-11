package com.homeservicehub.gateway.web;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletRequestWrapper;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Set;
import java.util.UUID;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestBoundaryFilter extends OncePerRequestFilter {
    private static final Set<String> UNTRUSTED = Set.of("forwarded", "x-forwarded-for", "x-forwarded-host", "x-forwarded-port", "x-forwarded-proto");

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String correlationId = UUID.randomUUID().toString();
        request.setAttribute("correlationId", correlationId);
        response.setHeader("X-Correlation-ID", correlationId);
        HttpServletRequest sanitized = new HttpServletRequestWrapper(request) {
            @Override public String getHeader(String name) { return UNTRUSTED.contains(name.toLowerCase()) ? null : super.getHeader(name); }
            @Override public java.util.Enumeration<String> getHeaders(String name) { return UNTRUSTED.contains(name.toLowerCase()) ? java.util.Collections.emptyEnumeration() : super.getHeaders(name); }
        };
        chain.doFilter(sanitized, response);
    }
}
