package com.inventory.item.service.impl;

import com.inventory.item.dto.ItemRequest;
import com.inventory.item.dto.ItemResponse;
import com.inventory.item.mapper.ItemMapper;
import com.inventory.item.model.Item;
import com.inventory.item.repository.ItemRepository;
import com.inventory.item.service.ItemService;
import io.micrometer.observation.Observation;
import io.micrometer.observation.ObservationRegistry;
import io.micrometer.observation.annotation.Observed;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
@Observed(name = "item.service", contextualName = "Layer: Service")
public class ItemServiceImpl implements ItemService {

    private final ItemRepository itemRepository;
    private final ItemMapper itemMapper;
    private final ObservationRegistry observationRegistry;

    @Override
    public List<ItemResponse> getAllItems() {
        return itemRepository.findAll().stream()
                .map(itemMapper::toResponse)
                .toList();
    }

    @Override
    public ItemResponse getItemById(Long id) {
        // 在當前觀測中添加業務標籤
        Observation observation = observationRegistry.getCurrentObservation();
        if (observation != null) {
            observation.lowCardinalityKeyValue("item.id", String.valueOf(id));
        }

        Item item = itemRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Item not found with id: " + id));
        return itemMapper.toResponse(item);
    }

    @Override
    @Transactional
    public ItemResponse createItem(ItemRequest request) {
        Item item = itemMapper.toEntity(request);
        Item savedItem = itemRepository.save(item);

        // 紀錄新建立的資源 ID
        Observation observation = observationRegistry.getCurrentObservation();
        if (observation != null) {
            observation.lowCardinalityKeyValue("item.id", String.valueOf(savedItem.getId()));
        }

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
