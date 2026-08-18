package com.inventory.item.service;

import com.inventory.item.exception.ResourceNotFoundException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class StorageServiceTest {

    @TempDir
    Path tempDir;

    private StorageService storageService;

    @BeforeEach
    void setUp() {
        storageService = new StorageService(tempDir.toString(), "/minio", "inventory-items");
    }

    @Test
    void uploadReturnsBrowserFacingSameOriginUrlAndWritesBytes() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "photo.jpg",
                "image/jpeg",
                new byte[]{1, 2, 3}
        );

        String imageUrl = storageService.uploadFile(file);

        assertThat(imageUrl).matches("/minio/inventory-items/[0-9a-f-]+\\.jpg");
        String filename = imageUrl.substring(imageUrl.lastIndexOf('/') + 1);
        assertThat(tempDir.resolve(filename)).exists().hasBinaryContent(new byte[]{1, 2, 3});
    }

    @Test
    void deleteRemovesStoredFile() throws Exception {
        String imageUrl = storageService.uploadFile(new MockMultipartFile(
                "file", "photo.jpg", "image/jpeg", new byte[]{9, 8, 7}));
        String filename = imageUrl.substring(imageUrl.lastIndexOf('/') + 1);

        storageService.deleteFile(imageUrl);

        assertThat(tempDir.resolve(filename)).doesNotExist();
    }

    @Test
    void loadFileReturnsStoredBytesAndJpegType() throws Exception {
        String imageUrl = storageService.uploadFile(new MockMultipartFile(
                "file", "photo.jpg", "image/jpeg", new byte[]{4, 5, 6}));
        String filename = imageUrl.substring(imageUrl.lastIndexOf('/') + 1);

        StorageService.StoredImage image = storageService.loadFile(filename);

        assertThat(image.contentType()).isEqualTo("image/jpeg");
        assertThat(image.size()).isEqualTo(3);
        assertThat(image.resource().getContentAsByteArray()).containsExactly(4, 5, 6);
    }

    @Test
    void loadFileRejectsPathTraversal() {
        assertThatThrownBy(() -> storageService.loadFile("../secret.jpg"))
                .isInstanceOf(ResourceNotFoundException.class);
        assertThatThrownBy(() -> storageService.loadFile("..\\secret.jpg"))
                .isInstanceOf(ResourceNotFoundException.class);
    }

    @Test
    void loadFileRejectsMissingFile() {
        assertThatThrownBy(() -> storageService.loadFile("missing.jpg"))
                .isInstanceOf(ResourceNotFoundException.class);
    }
}
