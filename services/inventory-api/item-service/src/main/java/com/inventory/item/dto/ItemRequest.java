package com.inventory.item.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "Request object for creating or updating an item")
public record ItemRequest(
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
        String imageUrl) {

}
