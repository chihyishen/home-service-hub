plugins {
    id("java-library")
    id("org.springframework.boot")
    id("io.spring.dependency-management")
}

// 停用 Spring Boot 的可執行 Jar 打包
tasks.getByName<org.springframework.boot.gradle.tasks.bundling.BootJar>("bootJar") {
    enabled = false
}

tasks.getByName<Jar>("jar") {
    enabled = true
}

dependencies {
    // 1. 核心 Web
    api("org.springframework.boot:spring-boot-starter-webmvc")

    // 2. 監控與可觀測性 (Observability)
    api("org.springframework.boot:spring-boot-starter-actuator")
    api("org.springframework.boot:spring-boot-starter-opentelemetry")
    api("org.springframework.boot:spring-boot-starter-aop:4.0.0-M2")

    // 3. SQL 觀測 (目前最穩定的橋接器版本)
    implementation("net.ttddyy.observation:datasource-micrometer-spring-boot:2.1.0")

    // 4. OTEL 相關
    implementation("io.opentelemetry:opentelemetry-exporter-otlp")
    api("io.opentelemetry.instrumentation:opentelemetry-logback-appender-1.0:2.24.0-alpha")

    // 5. 其他
    api("org.zalando:logbook-spring-boot-starter:4.0.0-RC.1")
    api("org.springdoc:springdoc-openapi-starter-webmvc-ui:3.0.0")
    api("org.mapstruct:mapstruct:1.6.3")
    api("org.springframework.boot:spring-boot-starter-jackson")
}

tasks.test {
    useJUnitPlatform()
}
