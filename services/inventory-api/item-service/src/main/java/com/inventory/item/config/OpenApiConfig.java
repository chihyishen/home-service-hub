package com.inventory.item.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.Contact;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("Home Service Hub - Inventory Item Service")
                        .version("1.1.0")
                        .description("家用品庫存管理微服務。提供品項、分類與收納位置的管理功能。")
                        .contact(new Contact()
                                .name("Service Maintainer")
                                .email("admin@example.com")));
    }
}
