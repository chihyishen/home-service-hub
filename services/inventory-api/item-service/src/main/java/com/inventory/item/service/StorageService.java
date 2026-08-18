package com.inventory.item.service;

import com.inventory.item.exception.ResourceNotFoundException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;
import java.util.UUID;

@Service
@Slf4j
public class StorageService {

    private final Path storageDirectory;
    private final String publicEndpoint;
    private final String publicPrefix;

    public StorageService(
            @Value("${storage.images.directory}") String storageDirectory,
            @Value("${storage.images.public-endpoint:/minio}") String publicEndpoint,
            @Value("${storage.images.public-prefix:inventory-items}") String publicPrefix) {
        this.storageDirectory = Path.of(storageDirectory).toAbsolutePath().normalize();
        this.publicEndpoint = publicEndpoint.endsWith("/")
                ? publicEndpoint.substring(0, publicEndpoint.length() - 1)
                : publicEndpoint;
        this.publicPrefix = publicPrefix;
        try {
            Files.createDirectories(this.storageDirectory);
        } catch (IOException e) {
            throw new IllegalStateException("Failed to create image storage directory: " + this.storageDirectory, e);
        }
    }

    public String uploadFile(MultipartFile file) {
        String extension = extensionOf(file.getOriginalFilename());
        String objectName = UUID.randomUUID() + extension;
        Path destination = resolveSafe(objectName);
        try (InputStream inputStream = file.getInputStream()) {
            Files.copy(inputStream, destination);
        } catch (Exception e) {
            log.error("Error writing uploaded image", e);
            throw new RuntimeException("Failed to store uploaded image", e);
        }
        return String.format("%s/%s/%s", publicEndpoint, publicPrefix, objectName);
    }

    public void deleteFile(String fileUrl) {
        if (fileUrl == null || fileUrl.isEmpty()) {
            return;
        }
        try {
            String[] parts = fileUrl.split("/");
            Path target = resolveSafe(parts[parts.length - 1]);
            Files.deleteIfExists(target);
        } catch (Exception e) {
            log.error("Error deleting stored image: {}", fileUrl, e);
        }
    }

    public StoredImage loadFile(String filename) {
        Path path = resolveSafe(filename);
        if (!Files.isRegularFile(path)) {
            throw new ResourceNotFoundException("Image not found");
        }
        try {
            return new StoredImage(new FileSystemResource(path), contentType(path), Files.size(path));
        } catch (IOException e) {
            throw new ResourceNotFoundException("Image not found");
        }
    }

    private Path resolveSafe(String filename) {
        if (filename == null || filename.isBlank() || filename.contains("/") || filename.contains("\\")
                || filename.contains("..")) {
            throw new ResourceNotFoundException("Image not found");
        }
        Path resolved = storageDirectory.resolve(filename).normalize();
        if (!resolved.startsWith(storageDirectory)) {
            throw new ResourceNotFoundException("Image not found");
        }
        return resolved;
    }

    private static String extensionOf(String originalFilename) {
        if (originalFilename != null && originalFilename.contains(".")) {
            return originalFilename.substring(originalFilename.lastIndexOf('.'));
        }
        return "";
    }

    private static String contentType(Path file) throws IOException {
        String probed = Files.probeContentType(file);
        if (probed != null) {
            return probed;
        }
        String name = file.getFileName().toString().toLowerCase(Locale.ROOT);
        if (name.endsWith(".jpg") || name.endsWith(".jpeg")) {
            return "image/jpeg";
        }
        if (name.endsWith(".png")) {
            return "image/png";
        }
        if (name.endsWith(".webp")) {
            return "image/webp";
        }
        if (name.endsWith(".gif")) {
            return "image/gif";
        }
        return "application/octet-stream";
    }

    public record StoredImage(Resource resource, String contentType, long size) {}
}
