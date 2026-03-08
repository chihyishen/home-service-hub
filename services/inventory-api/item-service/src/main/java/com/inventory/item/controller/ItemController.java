package com.inventory.item.controller;

import com.inventory.item.dto.ItemRequest;
import com.inventory.item.dto.ItemResponse;
import com.inventory.item.dto.ItemTransactionResultResponse;
import com.inventory.item.dto.InventoryTransactionRequest;
import com.inventory.item.dto.InventoryTransactionResponse;
import com.inventory.item.service.ItemService;
import io.micrometer.observation.annotation.Observed;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/items")

@RequiredArgsConstructor

@Observed(name = "item.api", contextualName = "Layer: Controller")

@Tag(name = "Items", description = "品項管理 (Item API) - 提供庫存品項的增刪查改功能")

public class ItemController {





    private final ItemService itemService;



    @GetMapping

    @Operation(summary = "獲取所有品項", description = "取得目前系統中所有庫存品項的完整清單，可選用關鍵字搜尋")

    public ResponseEntity<List<ItemResponse>> getAllItems(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) Boolean lowStockOnly,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String location
    ) {

        return ResponseEntity.ok(itemService.getAllItems(keyword, lowStockOnly, category, location));

    }



    @GetMapping("/categories")

    @Operation(summary = "獲取所有分類", description = "取得目前系統中已存在的所有分類名稱")

    public ResponseEntity<List<String>> getAllCategories() {

        return ResponseEntity.ok(itemService.getAllCategories());

    }



    @GetMapping("/locations")

    @Operation(summary = "獲取所有位置", description = "取得目前系統中已存在的所有收納位置")

    public ResponseEntity<List<String>> getAllLocations() {

        return ResponseEntity.ok(itemService.getAllLocations());

    }



    @GetMapping("/{id}")

    @Operation(summary = "獲取單一品項詳情", description = "透過 ID 查詢特定庫存品項的詳細資訊")

    @ApiResponse(responseCode = "200", description = "查詢成功")

    @ApiResponse(responseCode = "404", description = "找不到該品項")

    public ResponseEntity<ItemResponse> getItemById(@PathVariable Long id) {

        return ResponseEntity.ok(itemService.getItemById(id));

    }



    @PostMapping

    @Operation(summary = "建立新品項", description = "在系統中建立一個新的庫存品項紀錄")

    @ApiResponse(responseCode = "200", description = "建立成功")

    public ResponseEntity<ItemResponse> createItem(@RequestBody ItemRequest request) {

        return ResponseEntity.ok(itemService.createItem(request));

    }



    @PostMapping(value = "/{id}/image", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @Operation(summary = "上傳品項圖片", description = "上傳圖片並更新品項的圖片連結")
    @ApiResponse(responseCode = "200", description = "上傳成功")
    @ApiResponse(responseCode = "404", description = "找不到該品項")
    public ResponseEntity<ItemResponse> uploadImage(
            @PathVariable Long id,
            @RequestParam("file") MultipartFile file) {
        return ResponseEntity.ok(itemService.uploadImage(id, file));
    }

    @PostMapping("/{id}/transactions")
    @Operation(summary = "建立庫存異動", description = "建立使用/補貨/盤點異動並更新品項數量")
    public ResponseEntity<ItemTransactionResultResponse> createTransaction(
            @PathVariable Long id,
            @RequestBody InventoryTransactionRequest request) {
        return ResponseEntity.ok(itemService.createTransaction(id, request));
    }

    @GetMapping("/{id}/transactions")
    @Operation(summary = "查詢品項異動歷史", description = "取得指定品項的異動紀錄，依時間新到舊")
    public ResponseEntity<List<InventoryTransactionResponse>> getTransactions(
            @PathVariable Long id,
            @RequestParam(required = false) Integer limit) {
        return ResponseEntity.ok(itemService.getTransactionsByItemId(id, limit));
    }

    @PutMapping("/{id}")

    @Operation(summary = "修改品項資訊", description = "更新現有庫存品項的各項屬性")

    @ApiResponse(responseCode = "200", description = "更新成功")

    @ApiResponse(responseCode = "404", description = "找不到該品項")

    public ResponseEntity<ItemResponse> updateItem(@PathVariable Long id, @RequestBody ItemRequest request) {

        return ResponseEntity.ok(itemService.updateItem(id, request));

    }



    @DeleteMapping("/{id}")

    @Operation(summary = "刪除品項", description = "將特定品項從庫存系統中移除")

    @ApiResponse(responseCode = "204", description = "刪除成功")

    @ApiResponse(responseCode = "404", description = "找不到該品項")

    public ResponseEntity<Void> deleteItem(@PathVariable Long id) {

        itemService.deleteItem(id);

        return ResponseEntity.noContent().build();

    }

}
