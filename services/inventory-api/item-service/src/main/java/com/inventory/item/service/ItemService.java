package com.inventory.item.service;

import com.inventory.item.dto.ItemRequest;
import com.inventory.item.dto.ItemResponse;
import java.util.List;

public interface ItemService {

    List<ItemResponse> getAllItems();
    ItemResponse getItemById(Long id);
    ItemResponse createItem(ItemRequest item);
    ItemResponse updateItem(Long id, ItemRequest itemDetails);
    void deleteItem(Long id);
}