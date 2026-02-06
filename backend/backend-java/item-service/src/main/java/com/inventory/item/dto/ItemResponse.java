package com.inventory.item.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

@Schema(description = "Response object representing an inventory item")
public record ItemResponse(
        @Schema(description = "Unique identifier of the item", example = "1")
        Long id,
        @Schema(description = "Name of the item", example = "Screwdriver")
        String name,
        @Schema(description = "Category of the item", example = "Tools")
        String category,
        @Schema(description = "Storage location", example = "Garage Shelf A")
        String location,
        @Schema(description = "Quantity in stock", example = "5")
        Integer quantity,
        @Schema(description = "Additional notes", example = "Phillips head")
        String note,
        @Schema(description = "URL to an image of the item", example = "http://example.com/image.jpg")
        String imageUrl,
        @Schema(description = "Timestamp when the item was created")
        LocalDateTime createdAt,
        @Schema(description = "Timestamp when the item was last updated")
        LocalDateTime updatedAt
) {
}
