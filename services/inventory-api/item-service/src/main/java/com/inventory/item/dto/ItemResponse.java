package com.inventory.item.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

@Schema(description = "代表庫存品項的響應對象")
public record ItemResponse(
        @Schema(description = "品項唯一識別碼", example = "1")
        Long id,
        @Schema(description = "品項名稱", example = "螺絲起子")
        String name,
        @Schema(description = "分類", example = "工具")
        String category,
        @Schema(description = "收納位置", example = "車庫 A 層架")
        String location,
        @Schema(description = "庫存數量", example = "5")
        Integer quantity,
        @Schema(description = "備註說明", example = "十字頭，帶磁性")
        String note,
        @Schema(description = "品項圖片 URL", example = "http://example.com/image.jpg")
        String imageUrl,
        @Schema(description = "建立時間")
        LocalDateTime createdAt,
        @Schema(description = "最後更新時間")
        LocalDateTime updatedAt
) {
}
