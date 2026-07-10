package com.inventory.item.config;

import io.opentelemetry.api.OpenTelemetry;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.filter.CommonsRequestLoggingFilter;

import static org.assertj.core.api.Assertions.assertThat;

class LoggingConfigTest {

    private final LoggingConfig loggingConfig = new LoggingConfig(OpenTelemetry.noop());

    @Test
    void requestDetailsAreExcludedByDefault() {
        CommonsRequestLoggingFilter filter = loggingConfig.logFilter(false, false);

        assertThat(readBoolean(filter, "isIncludeQueryString")).isFalse();
        assertThat(readBoolean(filter, "isIncludePayload")).isFalse();
        assertThat(readBoolean(filter, "isIncludeHeaders")).isFalse();
    }

    @Test
    void sensitiveRequestDetailsRequireExplicitOptIn() {
        CommonsRequestLoggingFilter filter = loggingConfig.logFilter(true, true);

        assertThat(readBoolean(filter, "isIncludeQueryString")).isTrue();
        assertThat(readBoolean(filter, "isIncludePayload")).isTrue();
        assertThat(ReflectionTestUtils.<Integer>invokeMethod(filter, "getMaxPayloadLength"))
                .isEqualTo(10000);
    }

    private boolean readBoolean(CommonsRequestLoggingFilter filter, String methodName) {
        return Boolean.TRUE.equals(ReflectionTestUtils.invokeMethod(filter, methodName));
    }
}
