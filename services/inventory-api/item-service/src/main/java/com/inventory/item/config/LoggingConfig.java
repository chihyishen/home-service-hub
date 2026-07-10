package com.inventory.item.config;

import io.micrometer.observation.ObservationRegistry;
import io.micrometer.observation.aop.ObservedAspect;
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.instrumentation.logback.appender.v1_0.OpenTelemetryAppender;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.filter.CommonsRequestLoggingFilter;

@Configuration
public class LoggingConfig {

    private final OpenTelemetry openTelemetry;

    public LoggingConfig(OpenTelemetry openTelemetry) {
        this.openTelemetry = openTelemetry;
    }

    @Bean
    public ObservedAspect observedAspect(ObservationRegistry observationRegistry) {
        return new ObservedAspect(observationRegistry);
    }

    @PostConstruct
    public void setupLogbackAppender() {
        // 這行是關鍵：將 Spring 建立的 OpenTelemetry 實例安裝到 Logback Appender 中
        OpenTelemetryAppender.install(openTelemetry);
    }

    @Bean
    public CommonsRequestLoggingFilter logFilter(
            @Value("${INVENTORY_HTTP_QUERY_LOGGING_ENABLED:false}") boolean includeQueryString,
            @Value("${INVENTORY_HTTP_PAYLOAD_LOGGING_ENABLED:false}") boolean includePayload) {
        CommonsRequestLoggingFilter filter = new CommonsRequestLoggingFilter();
        filter.setIncludeQueryString(includeQueryString);
        filter.setIncludePayload(includePayload);
        if (includePayload) {
            filter.setMaxPayloadLength(10000);
        }
        filter.setIncludeHeaders(false);
        filter.setAfterMessagePrefix("API REQUEST: "); // 設定一個好搜的前綴
        return filter;
    }
}
