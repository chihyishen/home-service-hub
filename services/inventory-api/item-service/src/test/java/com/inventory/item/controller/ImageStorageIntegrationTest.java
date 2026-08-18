package com.inventory.item.controller;

import com.inventory.item.exception.GlobalExceptionHandler;
import com.inventory.item.service.StorageService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.nio.file.Path;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.head;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class ImageStorageIntegrationTest {

    @TempDir
    Path tempDir;

    private MockMvc mockMvc;
    private StorageService storageService;

    @BeforeEach
    void setUp() {
        storageService = new StorageService(tempDir.toString(), "/minio", "inventory-items");
        mockMvc = MockMvcBuilders.standaloneSetup(new ImageController(storageService))
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    void getReturnsStoredImage() throws Exception {
        String imageUrl = storageService.uploadFile(new MockMultipartFile(
                "file", "photo.jpg", "image/jpeg", new byte[]{1, 2, 3}));
        String filename = imageUrl.substring(imageUrl.lastIndexOf('/') + 1);

        mockMvc.perform(get("/inventory-items/" + filename))
                .andExpect(status().isOk())
                .andExpect(content().contentType("image/jpeg"))
                .andExpect(content().bytes(new byte[]{1, 2, 3}))
                .andExpect(header().string("Cache-Control", org.hamcrest.Matchers.containsString("max-age=31536000")));
    }

    @Test
    void headReturnsOkForStoredImage() throws Exception {
        String imageUrl = storageService.uploadFile(new MockMultipartFile(
                "file", "photo.jpg", "image/jpeg", new byte[]{1, 2, 3}));
        String filename = imageUrl.substring(imageUrl.lastIndexOf('/') + 1);

        mockMvc.perform(head("/inventory-items/" + filename))
                .andExpect(status().isOk())
                .andExpect(content().contentType("image/jpeg"));
    }

    @Test
    void getMissingImageReturns404() throws Exception {
        mockMvc.perform(get("/inventory-items/00000000-0000-0000-0000-000000000000.jpg"))
                .andExpect(status().isNotFound());
    }

    @Test
    void getTraversalReturns404() throws Exception {
        mockMvc.perform(get("/inventory-items/{filename}", "..secret.jpg"))
                .andExpect(status().isNotFound());
    }
}
