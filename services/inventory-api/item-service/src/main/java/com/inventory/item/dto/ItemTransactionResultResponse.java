package com.inventory.item.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "庫存異動結果")
public record ItemTransactionResultResponse(
        ItemResponse item,
        InventoryTransactionResponse transaction
) {
}
