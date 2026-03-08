package com.inventory.item.dto;

import com.inventory.item.model.InventoryTransactionSource;
import com.inventory.item.model.InventoryTransactionType;
import io.swagger.v3.oas.annotations.media.Schema;

import java.time.LocalDateTime;

@Schema(description = "庫存異動回應")
public record InventoryTransactionResponse(
        Long id,
        Long itemId,
        InventoryTransactionType type,
        Integer deltaQuantity,
        Integer beforeQuantity,
        Integer afterQuantity,
        String reason,
        InventoryTransactionSource source,
        String operatorName,
        LocalDateTime occurredAt,
        LocalDateTime createdAt
) {
}
