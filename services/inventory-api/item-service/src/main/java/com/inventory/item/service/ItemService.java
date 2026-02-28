package com.inventory.item.service;

import com.inventory.item.dto.ItemRequest;
import com.inventory.item.dto.ItemResponse;
import java.util.List;

import org.springframework.web.multipart.MultipartFile;

public interface ItemService {

    List<ItemResponse> getAllItems(String keyword);
    List<String> getAllCategories();
    List<String> getAllLocations();
    ItemResponse getItemById(Long id);
    ItemResponse createItem(ItemRequest item);
    ItemResponse updateItem(Long id, ItemRequest itemDetails);
    ItemResponse uploadImage(Long id, MultipartFile file);
    void deleteItem(Long id);
}