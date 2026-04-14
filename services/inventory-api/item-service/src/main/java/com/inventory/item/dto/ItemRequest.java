package com.inventory.item.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

@Schema(description = "建立或修改品項的請求對象")
public record ItemRequest(
        @NotBlank(message = "名稱不可為空")
        @Schema(description = "品項名稱", example = "螺絲起子")
        String name,
        @Schema(description = "分類 (例如：工具、生活、電器)", example = "工具")
        String category,
        @Schema(description = "收納位置", example = "車庫 A 層架")
        String location,
        @NotNull
        @Min(value = 0, message = "數量不可為負數")
        @Schema(description = "庫存數量", example = "5")
        Integer quantity,
        @Min(value = 0)
        @Schema(description = "低庫存門檻", example = "2")
        Integer minQuantity,
        @Min(value = 0)
        @Schema(description = "理想庫存量", example = "8")
        Integer targetQuantity,
        @Schema(description = "是否為可消耗品", example = "true")
        Boolean isConsumable,
        @Schema(description = "狀態", example = "ACTIVE")
        String status,
        @Schema(description = "備註說明", example = "十字頭，帶磁性")
        String note,
        @Schema(description = "品項圖片 URL", example = "http://example.com/image.jpg")
        String imageUrl) {

}
