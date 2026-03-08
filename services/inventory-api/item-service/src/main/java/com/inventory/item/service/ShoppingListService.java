package com.inventory.item.service;

import com.inventory.item.dto.ShoppingListItemRequest;
import com.inventory.item.dto.ShoppingListItemResponse;
import com.inventory.item.model.ShoppingListItemStatus;

import java.util.List;

public interface ShoppingListService {
    List<ShoppingListItemResponse> getShoppingList(ShoppingListItemStatus status);

    List<ShoppingListItemResponse> generateFromLowStock();

    ShoppingListItemResponse createItem(ShoppingListItemRequest request);

    ShoppingListItemResponse updateItem(Long id, ShoppingListItemRequest request);

    void deleteItem(Long id);
}
