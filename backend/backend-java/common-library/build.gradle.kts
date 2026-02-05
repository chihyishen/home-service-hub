plugins {
    id("java-library")
    id("org.springframework.boot")
    id("io.spring.dependency-management")
}

// 停用 Spring Boot 的可執行 Jar 打包，只產生普通 Jar
tasks.getByName<org.springframework.boot.gradle.tasks.bundling.BootJar>("bootJar") {
    enabled = false
}

tasks.getByName<Jar>("jar") {
    enabled = true
}

dependencies {
    // Web 基礎 (MVC, Validation...)
    api("org.springframework.boot:spring-boot-starter-webmvc")

    // === 2. 監控與可觀測性 (Observability) ===
    api("org.springframework.boot:spring-boot-starter-actuator")
    api("org.springframework.boot:spring-boot-starter-opentelemetry")

    // OTLP 導出器 (負責送出 Traces 和 Metrics)
    implementation("io.opentelemetry:opentelemetry-exporter-otlp")

    // === 3. 日誌  ===
    api("io.opentelemetry.instrumentation:opentelemetry-logback-appender-1.0:2.12.0-alpha")
    // 補齊實驗性 API 模組，對齊 Spring Boot 4.0.1 內部使用的 1.55.0
    api("io.opentelemetry:opentelemetry-api-incubator:1.55.0-alpha")
    api("org.zalando:logbook-spring-boot-starter:4.0.0-RC.1")

    // === 4. API 文件 ===
    api("org.springdoc:springdoc-openapi-starter-webmvc-ui:3.0.0")

    // === 5. 工具 ===
    api("org.mapstruct:mapstruct:1.6.3")
    api("org.springframework.boot:spring-boot-starter-jackson")
}

tasks.test {
    useJUnitPlatform()
}