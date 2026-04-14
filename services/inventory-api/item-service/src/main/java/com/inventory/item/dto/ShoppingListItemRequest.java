package com.inventory.item.dto;

import com.inventory.item.model.ShoppingListItemSource;
import com.inventory.item.model.ShoppingListItemStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

@Schema(description = "採買清單請求")
public record ShoppingListItemRequest(
        @Schema(description = "關聯品項 ID（手動項目可為空）", example = "1")
        Long itemId,
        @NotBlank
        @Schema(description = "名稱快照", example = "衛生紙")
        String itemNameSnapshot,
        @NotNull
        @Min(1)
        @Schema(description = "建議購買數量", example = "3")
        Integer suggestedQuantity,
        @Schema(description = "狀態", example = "PENDING")
        ShoppingListItemStatus status,
        @Schema(description = "來源", example = "MANUAL")
        ShoppingListItemSource source,
        @Schema(description = "備註", example = "全聯補貨")
        String note
) {
}
