plugins {
    id("java")
    id("org.springframework.boot")
    id("io.spring.dependency-management")
}

description = "item-service"

dependencies {
    annotationProcessor("org.springframework.boot:spring-boot-configuration-processor")

    // === 1. Web / Observability (formerly provided by common-library) ===
    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("org.springframework.boot:spring-boot-starter-opentelemetry")
    implementation("org.springframework.boot:spring-boot-starter-aop:4.0.0-M2")
    implementation("net.ttddyy.observation:datasource-micrometer-spring-boot:2.1.0")
    implementation("io.opentelemetry:opentelemetry-exporter-otlp")
    implementation("io.opentelemetry.instrumentation:opentelemetry-logback-appender-1.0:2.24.0-alpha")
    implementation("io.opentelemetry:opentelemetry-api-incubator")
    implementation("org.zalando:logbook-spring-boot-starter:4.0.0-RC.1")
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:3.0.0")
    implementation("org.springframework.boot:spring-boot-starter-jackson")

    // 2. Lombok
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")

    // 3. MapStruct (DTO 轉換)
    implementation("org.mapstruct:mapstruct:1.6.3")
    annotationProcessor("org.mapstruct:mapstruct-processor:1.6.3")

    // 4. 資料庫相關
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    runtimeOnly("org.postgresql:postgresql")
    implementation("org.flywaydb:flyway-core")
    runtimeOnly("org.flywaydb:flyway-database-postgresql")


    // 4.1 MinIO (物件儲存)
    implementation("io.minio:minio:8.5.17")

    // 4.2 Validation
    implementation("org.springframework.boot:spring-boot-starter-validation")

    // 4.3 Actuator (health)
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-security")
    implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")

    // 5. 開發工具 (熱重載等)
    // 這行確保 DevTools 不會被打包進 Production
    developmentOnly("org.springframework.boot:spring-boot-devtools")

    // 6. 測試 (僅測試時使用)
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.boot:spring-boot-starter-data-jpa-test")
    testImplementation("org.springframework.security:spring-security-test")
    testRuntimeOnly("com.h2database:h2")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.withType<Test> {
    useJUnitPlatform()
}
