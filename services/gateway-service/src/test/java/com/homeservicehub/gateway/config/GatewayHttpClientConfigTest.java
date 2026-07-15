package com.homeservicehub.gateway.config;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.client.ClientHttpRequest;
import org.springframework.http.client.ClientHttpResponse;

class GatewayHttpClientConfigTest {
    @Test
    void postsToUpstreamsUsingHttp11AndPreservesTheBody() throws Exception {
        AtomicReference<String> protocol = new AtomicReference<>();
        AtomicReference<String> body = new AtomicReference<>();
        HttpServer backend = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        backend.createContext("/transactions/", exchange -> {
            protocol.set(exchange.getProtocol());
            body.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            byte[] response = "{\"code\":400}".getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", MediaType.APPLICATION_JSON_VALUE);
            exchange.sendResponseHeaders(400, response.length);
            exchange.getResponseBody().write(response);
            exchange.close();
        });
        backend.start();
        try {
            URI uri = URI.create("http://127.0.0.1:" + backend.getAddress().getPort() + "/transactions/");
            ClientHttpRequest request = new GatewayHttpClientConfig().gatewayClientHttpRequestFactory()
                    .createRequest(uri, HttpMethod.POST);
            request.getHeaders().setContentType(MediaType.APPLICATION_JSON);
            request.getBody().write("{\"payment_method\":\"invalid\"}".getBytes(StandardCharsets.UTF_8));
            try (ClientHttpResponse response = request.execute()) {
                assertThat(response.getStatusCode().value()).isEqualTo(400);
            }
            assertThat(protocol.get()).isEqualTo("HTTP/1.1");
            assertThat(body.get()).isEqualTo("{\"payment_method\":\"invalid\"}");
        } finally {
            backend.stop(0);
        }
    }
}
