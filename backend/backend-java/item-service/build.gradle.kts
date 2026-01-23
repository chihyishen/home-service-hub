plugins {
    java
    id("org.springframework.boot") version "4.0.1"
    id("io.spring.dependency-management") version "1.1.7"
}

description = "item-service"

dependencies {
    // === 1. 引入共用庫 ===
    implementation(project(":common-library"))

    // === 2. 編譯時期處理器 (Annotation Processors) ===
    // 處理器不會透過 'api' 傳遞，必須在每個服務中顯式宣告
    annotationProcessor("org.springframework.boot:spring-boot-configuration-processor")
    annotationProcessor("org.mapstruct:mapstruct-processor:1.6.3")

    // (Lombok 已在 Root build.gradle.kts 定義，此處無需重複)

    // === 3. 開發工具 (僅開發時使用) ===
    developmentOnly("org.springframework.boot:spring-boot-devtools")
}

tasks.withType<Test> {
    useJUnitPlatform()
}
