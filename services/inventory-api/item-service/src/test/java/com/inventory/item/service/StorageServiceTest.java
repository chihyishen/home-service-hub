package com.inventory.item.service;

import io.minio.MinioClient;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class StorageServiceTest {

    @Test
    void uploadReturnsBrowserFacingSameOriginUrl() throws Exception {
        MinioClient minioClient = mock(MinioClient.class);
        when(minioClient.bucketExists(any())).thenReturn(true);
        StorageService storageService = new StorageService(minioClient);
        ReflectionTestUtils.setField(storageService, "bucketName", "inventory-items");
        ReflectionTestUtils.setField(storageService, "publicEndpoint", "/minio");
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "photo.jpg",
                "image/jpeg",
                new byte[]{1, 2, 3}
        );

        String imageUrl = storageService.uploadFile(file);

        assertThat(imageUrl).matches("/minio/inventory-items/[0-9a-f-]+\\.jpg");
    }
}
