package com.inventory.common.util;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;

class DotEnvLoaderTest {

    @TempDir
    Path tempDir;

    private String originalUserDir;

    @BeforeEach
    void setup() {
        originalUserDir = System.getProperty("user.dir");
        System.setProperty("user.dir", tempDir.toString());
    }

    @AfterEach
    void tearDown() {
        System.setProperty("user.dir", originalUserDir);
        System.clearProperty("KEY1");
        System.clearProperty("KEY2");
        System.clearProperty("KEY3");
        System.clearProperty("KEY4");
    }

    @Test
    void testLoadQuotedValues() throws IOException {
        Path dotEnv = tempDir.resolve(".env");
        String content = "KEY1=\"VALUE1\"\n" +
                         "KEY2='VALUE2'\n" +
                         "KEY3=VALUE3\n" +
                         "KEY4=\"VALUE WITH SPACES\"\n";
        Files.writeString(dotEnv, content);

        DotEnvLoader.load();

        assertEquals("VALUE1", System.getProperty("KEY1"));
        assertEquals("VALUE2", System.getProperty("KEY2"));
        assertEquals("VALUE3", System.getProperty("KEY3"));
        assertEquals("VALUE WITH SPACES", System.getProperty("KEY4"));
    }
}