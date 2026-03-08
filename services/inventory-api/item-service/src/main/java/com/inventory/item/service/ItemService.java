package com.inventory.item.service;

import com.inventory.item.dto.ItemRequest;
import com.inventory.item.dto.ItemResponse;
import com.inventory.item.dto.ItemTransactionResultResponse;
import com.inventory.item.dto.InventoryTransactionRequest;
import com.inventory.item.dto.InventoryTransactionResponse;
import java.util.List;

import org.springframework.web.multipart.MultipartFile;

public interface ItemService {

    List<ItemResponse> getAllItems(String keyword, Boolean lowStockOnly, String category, String location);
    List<String> getAllCategories();
    List<String> getAllLocations();
    ItemResponse getItemById(Long id);
    ItemResponse createItem(ItemRequest item);
    ItemResponse updateItem(Long id, ItemRequest itemDetails);
    ItemResponse uploadImage(Long id, MultipartFile file);
    ItemTransactionResultResponse createTransaction(Long id, InventoryTransactionRequest request);
    List<InventoryTransactionResponse> getTransactionsByItemId(Long id, Integer limit);
    void deleteItem(Long id);
}
