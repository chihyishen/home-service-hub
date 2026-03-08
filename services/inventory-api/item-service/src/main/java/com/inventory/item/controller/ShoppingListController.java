package com.inventory.item.controller;

import com.inventory.item.dto.ShoppingListItemRequest;
import com.inventory.item.dto.ShoppingListItemResponse;
import com.inventory.item.model.ShoppingListItemStatus;
import com.inventory.item.service.ShoppingListService;
import io.micrometer.observation.annotation.Observed;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/shopping-list")
@RequiredArgsConstructor
@Observed(name = "shopping-list.api", contextualName = "Layer: Controller")
@Tag(name = "Shopping List", description = "採買清單管理 API")
public class ShoppingListController {

    private final ShoppingListService shoppingListService;

    @GetMapping
    @Operation(summary = "查詢採買清單", description = "可依狀態篩選採買清單")
    public ResponseEntity<List<ShoppingListItemResponse>> getShoppingList(
            @RequestParam(required = false) ShoppingListItemStatus status) {
        return ResponseEntity.ok(shoppingListService.getShoppingList(status));
    }

    @PostMapping("/generate-from-low-stock")
    @Operation(summary = "從低庫存產生採買清單", description = "為低庫存品項建立待購買項，且避免重複")
    public ResponseEntity<List<ShoppingListItemResponse>> generateFromLowStock() {
        return ResponseEntity.ok(shoppingListService.generateFromLowStock());
    }

    @PostMapping
    @Operation(summary = "建立採買項目", description = "手動建立採買清單項目")
    public ResponseEntity<ShoppingListItemResponse> createShoppingListItem(@RequestBody ShoppingListItemRequest request) {
        return ResponseEntity.ok(shoppingListService.createItem(request));
    }

    @PatchMapping("/{id}")
    @Operation(summary = "更新採買項目", description = "更新採買清單狀態或欄位")
    public ResponseEntity<ShoppingListItemResponse> updateShoppingListItem(
            @PathVariable Long id,
            @RequestBody ShoppingListItemRequest request) {
        return ResponseEntity.ok(shoppingListService.updateItem(id, request));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "刪除採買項目", description = "刪除指定採買清單項目")
    public ResponseEntity<Void> deleteShoppingListItem(@PathVariable Long id) {
        shoppingListService.deleteItem(id);
        return ResponseEntity.noContent().build();
    }
}
