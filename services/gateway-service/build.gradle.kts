plugins {
    java
    id("org.springframework.boot") version "4.0.1"
    id("io.spring.dependency-management") version "1.1.7"
}

group = "com.homeservicehub"
version = "0.1.0"

java { toolchain { languageVersion.set(JavaLanguageVersion.of(21)) } }

repositories { mavenCentral() }

extra["springCloudVersion"] = "2025.1.0"

dependencyManagement {
    imports { mavenBom("org.springframework.cloud:spring-cloud-dependencies:${property("springCloudVersion")}") }
}

dependencies {
    implementation("org.springframework.cloud:spring-cloud-starter-gateway-server-webmvc")
    implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-opentelemetry")
    implementation("io.opentelemetry:opentelemetry-exporter-otlp")
    implementation("com.bucket4j:bucket4j_jdk17-core:8.15.0")
    implementation("com.github.ben-manes.caffeine:caffeine")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.security:spring-security-test")
}

tasks.test { useJUnitPlatform() }

// 載入根目錄 .env（pm2 的 env_file 不會生效，比照 inventory-api 的做法）
val dotEnvFile = File(projectDir.parentFile.parentFile, ".env")
val envMap = mutableMapOf<String, String>()
if (dotEnvFile.exists()) {
    dotEnvFile.readLines().forEach { line ->
        if (line.isNotBlank() && !line.startsWith("#") && line.contains("=")) {
            val parts = line.split("=", limit = 2)
            envMap[parts[0].trim()] = parts[1].trim()
        }
    }
}

// ponytail: 根 .env 的 SPRING_APPLICATION_NAME 是給 item-service 用的（它的 application.yml
// 寫 ${SPRING_APPLICATION_NAME} 且無預設值），但 env var 會蓋掉本服務 application.yml 的
// spring.application.name，害 gateway 的 trace 全部掛在 inventory-item-service 名下。
envMap.remove("SPRING_APPLICATION_NAME")

tasks.withType<org.springframework.boot.gradle.tasks.run.BootRun> {
    environment(envMap)
}
