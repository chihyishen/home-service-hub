plugins {
    id("java")
    id("org.springframework.boot")
    id("io.spring.dependency-management")
}

description = "item-service"

dependencies {
    annotationProcessor("org.springframework.boot:spring-boot-configuration-processor")

    // === 1. 引入共用庫 ===
    implementation(project(":common-library"))

    // 2. Lombok
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")

    // 3. MapStruct (DTO 轉換)
    annotationProcessor("org.mapstruct:mapstruct-processor:1.6.3")

    // 4. 資料庫相關
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    runtimeOnly("org.postgresql:postgresql")

    // 4.1 MinIO (物件儲存)
    implementation("io.minio:minio:8.5.17")

    // 5. 開發工具 (熱重載等)
    // 這行確保 DevTools 不會被打包進 Production
    developmentOnly("org.springframework.boot:spring-boot-devtools")

    // 6. 測試 (僅測試時使用)
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.boot:spring-boot-starter-data-jpa-test")
    testRuntimeOnly("com.h2database:h2")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.withType<Test> {
    useJUnitPlatform()
}
