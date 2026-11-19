package com.homeservicehub.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "OTEL_COLLECTOR_ENDPOINT_HTTP=http://localhost:4318",
        "management.tracing.export.otlp.enabled=false",
        "gateway.rate-limit.capacity=1000",
        "GATEWAY_ACCOUNTING_URI=http://127.0.0.1:1"
})
class GatewayExposureTest {
    @LocalServerPort int port;

    private int get(String path) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + path)).GET().build();
        return HttpClient.newHttpClient().send(req, HttpResponse.BodyHandlers.ofString()).statusCode();
    }

    @Test void unknownPathIs404() throws Exception { assertThat(get("/nope")).isEqualTo(404); }

    @Test void actuatorEnvNotExposed() throws Exception { assertThat(get("/actuator/env")).isEqualTo(404); }

    @Test void livenessIsUp() throws Exception { assertThat(get("/actuator/health/liveness")).isEqualTo(200); }

    @Test void browserTraceIngestionIsNotExposed() throws Exception {
        HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + "/otlp/v1/traces"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString("{}"))
                .build();
        assertThat(HttpClient.newHttpClient().send(request, HttpResponse.BodyHandlers.discarding()).statusCode())
                .isEqualTo(404);
    }

    @Test void apiRequestWithoutTokenIsNotRejected() throws Exception {
        assertThat(get("/api/accounting/transactions")).isNotIn(401, 403);
    }
}
