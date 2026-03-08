package com.inventory.item.dto;

import com.inventory.item.model.ShoppingListItemSource;
import com.inventory.item.model.ShoppingListItemStatus;
import io.swagger.v3.oas.annotations.media.Schema;

import java.time.LocalDateTime;

@Schema(description = "採買清單回應")
public record ShoppingListItemResponse(
        Long id,
        Long itemId,
        String itemNameSnapshot,
        Integer suggestedQuantity,
        ShoppingListItemStatus status,
        ShoppingListItemSource source,
        String note,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {
}
