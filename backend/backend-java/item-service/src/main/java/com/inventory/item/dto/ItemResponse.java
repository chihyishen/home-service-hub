package com.inventory.item.dto;

import java.time.LocalDateTime;

public record ItemResponse(
        Long id,
        String name,
        String category,
        String location,
        Integer quantity,
        String note,
        String imageUrl,
        LocalDateTime createdAt, // 這是唯讀的，只有 Response 會有
        LocalDateTime updatedAt
) {
}
