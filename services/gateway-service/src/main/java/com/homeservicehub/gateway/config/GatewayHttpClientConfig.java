package com.homeservicehub.gateway.config;

import java.net.http.HttpClient;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.http.client.JdkClientHttpRequestFactory;

@Configuration
public class GatewayHttpClientConfig {
    @Bean
    ClientHttpRequestFactory gatewayClientHttpRequestFactory() {
        return new JdkClientHttpRequestFactory(HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .build());
    }
}
