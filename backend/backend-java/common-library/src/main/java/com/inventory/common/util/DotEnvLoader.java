package com.inventory.common.util;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;

public class DotEnvLoader {

    public static void load() {
        // 向上查找 .env 檔案
        File currentDir = new File(System.getProperty("user.dir"));
        File dotEnv = findDotEnv(currentDir);

        if (dotEnv != null && dotEnv.exists()) {
            System.out.println("[DotEnvLoader] Loading: " + dotEnv.getAbsolutePath());
            try (BufferedReader reader = new BufferedReader(new FileReader(dotEnv))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    line = line.trim();
                    if (line.isEmpty() || line.startsWith("#") || !line.contains("=")) {
                        continue;
                    }

                    int separatorIndex = line.indexOf("=");
                    String key = line.substring(0, separatorIndex).trim();
                    String value = line.substring(separatorIndex + 1).trim();

                    // 移除引號
                    if (value.length() >= 2) {
                        if ((value.startsWith("\"") && value.endsWith("\"")) || 
                            (value.startsWith("'") && value.endsWith("'"))) {
                            value = value.substring(1, value.length() - 1);
                        }
                    }

                    System.setProperty(key, value);
                }
            } catch (Exception e) {
                System.err.println("[DotEnvLoader] Failed to load .env: " + e.getMessage());
            }
        } else {
            System.out.println("[DotEnvLoader] No .env file found in root hierarchy.");
        }
    }

    private static File findDotEnv(File dir) {
        if (dir == null) return null;
        File file = new File(dir, ".env");
        if (file.exists()) return file;
        return findDotEnv(dir.getParentFile());
    }
}
