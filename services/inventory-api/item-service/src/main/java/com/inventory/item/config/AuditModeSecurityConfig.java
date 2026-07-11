package com.inventory.item.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;

/**
 * 審計模式（enforcement 未啟用）時放行所有請求，認證由 gateway 負責。
 * 沒有這個 fallback 時，spring-boot-starter-security 的預設行為會把所有請求擋成 401。
 */
@Configuration
@ConditionalOnProperty(name = "security.oauth2.enforcement-enabled", havingValue = "false", matchIfMissing = true)
public class AuditModeSecurityConfig {

    @Bean
    SecurityFilterChain auditModeSecurity(HttpSecurity http) throws Exception {
        http.csrf(csrf -> csrf.disable())
                .authorizeHttpRequests(auth -> auth.anyRequest().permitAll());
        return http.build();
    }
}
