package com.inventory.item.dto;

import com.inventory.item.model.InventoryTransactionType;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

@Schema(description = "庫存異動請求")
public record InventoryTransactionRequest(
        @NotNull
        @Schema(description = "異動類型", example = "CONSUME")
        InventoryTransactionType type,
        @NotNull
        @Schema(description = "異動量（正數）", example = "1")
        Integer deltaQuantity,
        @Schema(description = "盤點後實際數量（ADJUST 專用）", example = "5")
        Integer actualQuantity,
        @Schema(description = "異動原因", example = "每週補貨")
        String reason,
        @Schema(description = "操作人", example = "chihyi")
        String operatorName
) {
}
