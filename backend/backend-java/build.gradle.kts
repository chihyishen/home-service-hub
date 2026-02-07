plugins {
    id("java")
    id("org.springframework.boot") version "4.0.1" apply false
    id("io.spring.dependency-management") version "1.1.7" apply false
}

allprojects {
    group = "com.inventory"
    version = "0.0.1-SNAPSHOT"

    repositories {
        mavenCentral()
    }
}

subprojects {
    apply(plugin = "java")
    apply(plugin = "io.spring.dependency-management")

    java {
        toolchain {
            languageVersion.set(JavaLanguageVersion.of(21))
        }
    }

    // --- 載入 .env 邏輯 ---
    val dotEnvFile = File(rootProject.projectDir.parentFile.parentFile, ".env")
    val envMap = mutableMapOf<String, String>()
    if (dotEnvFile.exists()) {
        dotEnvFile.readLines().forEach { line ->
            if (line.isNotBlank() && !line.startsWith("#") && line.contains("=")) {
                val parts = line.split("=", limit = 2)
                envMap[parts[0].trim()] = parts[1].trim()
            }
        }
    }

    tasks.withType<org.springframework.boot.gradle.tasks.run.BootRun> {
        environment(envMap)
    }

    tasks.withType<Test> {
        environment(envMap)
    }
    // -------------------

    dependencies {
        // 共用 Lombok
        compileOnly("org.projectlombok:lombok:1.18.36")
        annotationProcessor("org.projectlombok:lombok:1.18.36")

        // 測試
        testImplementation("org.junit.jupiter:junit-jupiter")
        testRuntimeOnly("org.junit.platform:junit-platform-launcher")
    }

    tasks.withType<Test> {
        useJUnitPlatform()
    }
}