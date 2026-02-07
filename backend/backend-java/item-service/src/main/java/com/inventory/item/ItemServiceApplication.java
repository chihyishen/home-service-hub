package com.inventory.item;

import com.inventory.common.util.DotEnvLoader;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = "com.inventory")
public class ItemServiceApplication {

    public static void main(String[] args) {
        DotEnvLoader.load();
        SpringApplication.run(ItemServiceApplication.class, args);
    }
}
