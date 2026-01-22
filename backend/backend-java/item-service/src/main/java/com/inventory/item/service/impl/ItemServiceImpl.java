package com.inventory.item.service.impl;

import com.inventory.item.dto.ItemRequest;
import com.inventory.item.dto.ItemResponse;
import com.inventory.item.mapper.ItemMapper;
import com.inventory.item.model.Item;
import com.inventory.item.repository.ItemRepository;
import com.inventory.item.service.ItemService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class ItemServiceImpl implements ItemService {

    private final ItemRepository itemRepository;
    private final ItemMapper itemMapper; // 注入 Mapper

    @Override
    public List<ItemResponse> getAllItems() {
        return itemRepository.findAll().stream()
                .map(itemMapper::toResponse) // 串流轉換
                .toList();
    }

    @Override
    public ItemResponse getItemById(Long id) {
        Item item = itemRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Item not found with id: " + id));
        return itemMapper.toResponse(item);
    }

    @Override
    @Transactional
    public ItemResponse createItem(ItemRequest request) {
        // 1. DTO -> Entity
        Item item = itemMapper.toEntity(request);
        // 2. Save
        Item savedItem = itemRepository.save(item);
        // 3. Entity -> DTO
        return itemMapper.toResponse(savedItem);
    }

    @Override
    @Transactional
    public ItemResponse updateItem(Long id, ItemRequest request) {
        // 1. 查出舊資料
        Item item = itemRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Item not found with id: " + id));

        // 2. 使用 Mapper 自動將 request 的非空欄位更新進 item
        itemMapper.updateEntityFromRequest(request, item);

        // 3. 存檔並回傳
        Item updatedItem = itemRepository.save(item);
        return itemMapper.toResponse(updatedItem);
    }

    @Override
    @Transactional
    public void deleteItem(Long id) {
        itemRepository.deleteById(id);
    }
}
