package com.homeservicehub.gateway.ratelimit;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RateLimitConfig {
    @Bean RateLimitFilter rateLimitFilter(@Value("${gateway.rate-limit.capacity:120}") long capacity,
                                          @Value("${gateway.rate-limit.refill-per-minute:60}") long refill) {
        return new RateLimitFilter(capacity, refill);
    }

    @Bean ApplicationRunner singleInstanceGuard(@Value("${gateway.instance-count:1}") int instances,
                                                 @Value("${gateway.rate-limit.store:local}") String store) {
        return args -> {
            if (instances > 1 && "local".equals(store)) throw new IllegalStateException("Multiple gateway instances require a shared rate-limit store");
        };
    }
}
