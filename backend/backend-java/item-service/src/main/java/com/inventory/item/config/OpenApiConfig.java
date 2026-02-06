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
                        .title("Home Inventory System API")
                        .version("0.0.1")
                        .description("API for managing home inventory items, categories, and locations.")
                        .contact(new Contact()
                                .name("Inventory Team")
                                .email("support@inventory.com")));
    }
}
