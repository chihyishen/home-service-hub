package com.inventory.item;

import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest(properties = {
        "server.port=0",
        "spring.application.name=item-service-test",
        "spring.datasource.url=jdbc:h2:mem:itemdb;MODE=PostgreSQL;DB_CLOSE_DELAY=-1;DATABASE_TO_LOWER=TRUE",
        "spring.datasource.driver-class-name=org.h2.Driver",
        "spring.datasource.username=sa",
        "spring.datasource.password=",
        "spring.jpa.hibernate.ddl-auto=create-drop",
        "spring.jpa.show-sql=false",
        "management.tracing.enabled=false",
        "management.otlp.tracing.endpoint=http://localhost:4318/v1/traces"
})
@ActiveProfiles("test")
public abstract class IntegrationTestBase {
}
