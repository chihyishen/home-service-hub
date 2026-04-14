package com.inventory.item.service.impl;

import com.inventory.item.dto.ItemRequest;
import com.inventory.item.dto.ItemResponse;
import com.inventory.item.dto.ItemTransactionResultResponse;
import com.inventory.item.dto.InventoryTransactionRequest;
import com.inventory.item.dto.InventoryTransactionResponse;
import com.inventory.item.exception.BadRequestException;
import com.inventory.item.exception.ResourceNotFoundException;
import com.inventory.item.mapper.ItemMapper;
import com.inventory.item.model.InventoryTransaction;
import com.inventory.item.model.InventoryTransactionSource;
import com.inventory.item.model.InventoryTransactionType;
import com.inventory.item.model.Item;
import com.inventory.item.repository.InventoryTransactionRepository;
import com.inventory.item.repository.ItemRepository;
import com.inventory.item.repository.ShoppingListItemRepository;
import com.inventory.item.service.ItemService;
import com.inventory.item.service.StorageService;
import io.micrometer.observation.Observation;
import io.micrometer.observation.ObservationRegistry;
import io.micrometer.observation.annotation.Observed;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
@Observed(name = "item.service", contextualName = "Layer: Service")
public class ItemServiceImpl implements ItemService {

    private final ItemRepository itemRepository;
    private final InventoryTransactionRepository inventoryTransactionRepository;
    private final ShoppingListItemRepository shoppingListItemRepository;
    private final ItemMapper itemMapper;
    private final ObservationRegistry observationRegistry;
    private final StorageService storageService;

    @Override
    public List<ItemResponse> getAllItems(String keyword, Boolean lowStockOnly, String category, String location) {
        List<Item> items = itemRepository.findByFilters(
                keyword == null ? null : keyword.trim(),
                Boolean.TRUE.equals(lowStockOnly),
                category == null ? null : category.trim(),
                location == null ? null : location.trim()
        );
        return items.stream()
                .map(itemMapper::toResponse)
                .toList();
    }

    @Override
    public List<String> getAllCategories() {
        return itemRepository.findDistinctCategories();
    }

    @Override
    public List<String> getAllLocations() {
        return itemRepository.findDistinctLocations();
    }

    @Override
    public ItemResponse getItemById(Long id) {
        // 在當前觀測中添加業務標籤
        Observation observation = observationRegistry.getCurrentObservation();
        if (observation != null) {
            observation.lowCardinalityKeyValue("item.id", String.valueOf(id));
        }

        Item item = itemRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Item not found with id: " + id));
        return itemMapper.toResponse(item);
    }

    @Override
    @Transactional
    public ItemResponse createItem(ItemRequest request) {
        Item item = itemMapper.toEntity(request);
        applyDefaultsAndValidate(item);
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
                .orElseThrow(() -> new ResourceNotFoundException("Item not found with id: " + id));

        // 2. 使用 Mapper 自動將 request 的非空欄位更新進 item
        itemMapper.updateEntityFromRequest(request, item);
        applyDefaultsAndValidate(item);

        // 3. 存檔並回傳
        Item updatedItem = itemRepository.save(item);
        return itemMapper.toResponse(updatedItem);
    }

    @Override
    @Transactional
    public ItemResponse uploadImage(Long id, MultipartFile file) {
        // 1. 查出 Item
        Item item = itemRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Item not found with id: " + id));

        // 2. 上傳圖片
        String imageUrl = storageService.uploadFile(file);

        // 3. 更新 URL
        item.setImageUrl(imageUrl);
        Item updatedItem = itemRepository.save(item);

        return itemMapper.toResponse(updatedItem);
    }

    @Override
    @Transactional
    public ItemTransactionResultResponse createTransaction(Long id, InventoryTransactionRequest request) {
        Item item = itemRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Item not found with id: " + id));

        if (request == null || request.type() == null) {
            throw new BadRequestException("Transaction type is required");
        }

        InventoryTransactionType type = request.type();
        Integer before = item.getQuantity();
        Integer after;
        Integer delta;

        if (before == null) {
            before = 0;
        }

        switch (type) {
            case CONSUME -> {
                validatePositive(request.deltaQuantity(), "deltaQuantity");
                delta = request.deltaQuantity();
                after = before - delta;
                if (after < 0) {
                    throw new BadRequestException("Quantity cannot be negative");
                }
            }
            case RESTOCK -> {
                validatePositive(request.deltaQuantity(), "deltaQuantity");
                delta = request.deltaQuantity();
                after = before + delta;
                item.setLastRestockedAt(LocalDateTime.now());
            }
            case ADJUST -> {
                if (request.actualQuantity() == null || request.actualQuantity() < 0) {
                    throw new BadRequestException("actualQuantity must be >= 0 for ADJUST");
                }
                after = request.actualQuantity();
                delta = after - before;
            }
            default -> throw new BadRequestException("Unsupported transaction type: " + type);
        }

        item.setQuantity(after);
        applyDefaultsAndValidate(item);
        Item savedItem = itemRepository.save(item);

        InventoryTransaction transaction = InventoryTransaction.builder()
                .item(savedItem)
                .type(type)
                .deltaQuantity(delta)
                .beforeQuantity(before)
                .afterQuantity(after)
                .reason(request.reason())
                .source(request.source())
                .operatorName(request.operatorName())
                .occurredAt(LocalDateTime.now())
                .build();
        InventoryTransaction savedTransaction = inventoryTransactionRepository.save(transaction);

        return new ItemTransactionResultResponse(
                itemMapper.toResponse(savedItem),
                toTransactionResponse(savedTransaction)
        );
    }

    @Override
    public List<InventoryTransactionResponse> getTransactionsByItemId(Long id, Integer limit) {
        if (!itemRepository.existsById(id)) {
            throw new ResourceNotFoundException("Item not found with id: " + id);
        }
        int effectiveLimit = (limit == null || limit <= 0) ? 50 : limit;
        return inventoryTransactionRepository.findByItemIdOrderByOccurredAtDesc(id).stream()
                .limit(effectiveLimit)
                .map(this::toTransactionResponse)
                .toList();
    }

    @Override
    @Transactional
    public void deleteItem(Long id) {
        if (!itemRepository.existsById(id)) {
            throw new ResourceNotFoundException("Item not found with id: " + id);
        }

        // Avoid FK violation by removing dependent rows first.
        inventoryTransactionRepository.deleteByItemId(id);
        shoppingListItemRepository.deleteByItemId(id);
        int deletedRows = itemRepository.hardDeleteById(id);
        itemRepository.flush();

        if (deletedRows <= 0 || itemRepository.existsById(id)) {
            throw new IllegalStateException("Failed to delete item with id: " + id);
        }
    }

    private void validatePositive(Integer value, String fieldName) {
        if (value == null || value <= 0) {
            throw new BadRequestException(fieldName + " must be > 0");
        }
    }

    private void applyDefaultsAndValidate(Item item) {
        if (item.getQuantity() == null || item.getQuantity() < 0) {
            throw new BadRequestException("quantity must be >= 0");
        }
        if (item.getMinQuantity() != null && item.getMinQuantity() < 0) {
            throw new BadRequestException("minQuantity must be >= 0");
        }
        if (item.getTargetQuantity() != null && item.getTargetQuantity() < 0) {
            throw new BadRequestException("targetQuantity must be >= 0");
        }
        if (item.getIsConsumable() == null) {
            item.setIsConsumable(true);
        }
        if (item.getStatus() == null || item.getStatus().isBlank()) {
            item.setStatus("ACTIVE");
        }
    }

    private InventoryTransactionResponse toTransactionResponse(InventoryTransaction transaction) {
        return new InventoryTransactionResponse(
                transaction.getId(),
                transaction.getItem().getId(),
                transaction.getType(),
                transaction.getDeltaQuantity(),
                transaction.getBeforeQuantity(),
                transaction.getAfterQuantity(),
                transaction.getReason(),
                transaction.getSource(),
                transaction.getOperatorName(),
                transaction.getOccurredAt(),
                transaction.getCreatedAt()
        );
    }
}
