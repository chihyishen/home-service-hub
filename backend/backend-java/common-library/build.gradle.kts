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

    // 監控與追蹤 (Actuator, OTel)
    api("org.springframework.boot:spring-boot-starter-actuator")
    api("org.springframework.boot:spring-boot-starter-opentelemetry")

    // 日誌 (Loki)
    api("com.github.loki4j:loki-logback-appender:1.5.1")

    // API 文件 (Swagger/OpenAPI)
    api("org.springdoc:springdoc-openapi-starter-webmvc-ui:3.0.0")

    // === 2. 資料庫相關 (Database) ===
    // 如果您的所有服務都會用到 DB，放在這裡最方便；否則可移回個別 Service
    api("org.springframework.boot:spring-boot-starter-data-jpa")
    api("org.postgresql:postgresql") // Driver

    // === 3. 工具 (Utils) ===
    // MapStruct Core (介面定義)
    api("org.mapstruct:mapstruct:1.6.3")

    // === 4. 測試依賴 (Test) ===
    // 讓所有服務都自動擁有測試能力
    api("org.springframework.boot:spring-boot-starter-test")

    implementation("io.opentelemetry:opentelemetry-exporter-otlp")
}

tasks.test {
    useJUnitPlatform()
}