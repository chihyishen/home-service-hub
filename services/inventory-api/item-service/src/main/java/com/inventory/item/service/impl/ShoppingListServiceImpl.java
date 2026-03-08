package com.inventory.item.service.impl;

import com.inventory.item.dto.ShoppingListItemRequest;
import com.inventory.item.dto.ShoppingListItemResponse;
import com.inventory.item.exception.BadRequestException;
import com.inventory.item.exception.ResourceNotFoundException;
import com.inventory.item.model.Item;
import com.inventory.item.model.ShoppingListItem;
import com.inventory.item.model.ShoppingListItemSource;
import com.inventory.item.model.ShoppingListItemStatus;
import com.inventory.item.repository.ItemRepository;
import com.inventory.item.repository.ShoppingListItemRepository;
import com.inventory.item.service.ShoppingListService;
import io.micrometer.observation.annotation.Observed;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
@Observed(name = "shopping-list.service", contextualName = "Layer: Service")
public class ShoppingListServiceImpl implements ShoppingListService {

    private final ShoppingListItemRepository shoppingListItemRepository;
    private final ItemRepository itemRepository;

    @Override
    public List<ShoppingListItemResponse> getShoppingList(ShoppingListItemStatus status) {
        List<ShoppingListItem> items = status == null
                ? shoppingListItemRepository.findAll()
                : shoppingListItemRepository.findByStatusOrderByCreatedAtDesc(status);
        return items.stream().map(this::toResponse).toList();
    }

    @Override
    @Transactional
    public List<ShoppingListItemResponse> generateFromLowStock() {
        List<Item> lowStockItems = itemRepository.findByFilters(null, true, null, null);
        for (Item item : lowStockItems) {
            if (shoppingListItemRepository.existsByItemIdAndStatus(item.getId(), ShoppingListItemStatus.PENDING)) {
                continue;
            }

            int suggestedQuantity = 1;
            if (item.getTargetQuantity() != null) {
                suggestedQuantity = Math.max(item.getTargetQuantity() - item.getQuantity(), 1);
            }

            ShoppingListItem entry = ShoppingListItem.builder()
                    .item(item)
                    .itemNameSnapshot(item.getName())
                    .suggestedQuantity(suggestedQuantity)
                    .status(ShoppingListItemStatus.PENDING)
                    .source(ShoppingListItemSource.LOW_STOCK_RULE)
                    .build();
            shoppingListItemRepository.save(entry);
        }

        return shoppingListItemRepository.findByStatusOrderByCreatedAtDesc(ShoppingListItemStatus.PENDING)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    @Override
    @Transactional
    public ShoppingListItemResponse createItem(ShoppingListItemRequest request) {
        if ((request.itemNameSnapshot() == null || request.itemNameSnapshot().isBlank()) && request.itemId() == null) {
            throw new BadRequestException("itemNameSnapshot is required when itemId is not provided");
        }
        if (request.suggestedQuantity() == null || request.suggestedQuantity() <= 0) {
            throw new BadRequestException("suggestedQuantity must be > 0");
        }

        Item linkedItem = null;
        if (request.itemId() != null) {
            linkedItem = itemRepository.findById(request.itemId())
                    .orElseThrow(() -> new ResourceNotFoundException("Item not found with id: " + request.itemId()));
        }

        ShoppingListItem entity = ShoppingListItem.builder()
                .item(linkedItem)
                .itemNameSnapshot(request.itemNameSnapshot() != null && !request.itemNameSnapshot().isBlank()
                        ? request.itemNameSnapshot()
                        : linkedItem.getName())
                .suggestedQuantity(request.suggestedQuantity())
                .status(request.status() == null ? ShoppingListItemStatus.PENDING : request.status())
                .source(request.source() == null ? ShoppingListItemSource.MANUAL : request.source())
                .note(request.note())
                .build();
        return toResponse(shoppingListItemRepository.save(entity));
    }

    @Override
    @Transactional
    public ShoppingListItemResponse updateItem(Long id, ShoppingListItemRequest request) {
        ShoppingListItem entity = shoppingListItemRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Shopping list item not found with id: " + id));

        if (request.itemNameSnapshot() != null && !request.itemNameSnapshot().isBlank()) {
            entity.setItemNameSnapshot(request.itemNameSnapshot());
        }
        if (request.suggestedQuantity() != null) {
            if (request.suggestedQuantity() <= 0) {
                throw new BadRequestException("suggestedQuantity must be > 0");
            }
            entity.setSuggestedQuantity(request.suggestedQuantity());
        }
        if (request.status() != null) {
            entity.setStatus(request.status());
        }
        if (request.source() != null) {
            entity.setSource(request.source());
        }
        if (request.note() != null) {
            entity.setNote(request.note());
        }
        return toResponse(shoppingListItemRepository.save(entity));
    }

    @Override
    @Transactional
    public void deleteItem(Long id) {
        shoppingListItemRepository.deleteById(id);
    }

    private ShoppingListItemResponse toResponse(ShoppingListItem entity) {
        return new ShoppingListItemResponse(
                entity.getId(),
                entity.getItem() == null ? null : entity.getItem().getId(),
                entity.getItemNameSnapshot(),
                entity.getSuggestedQuantity(),
                entity.getStatus(),
                entity.getSource(),
                entity.getNote(),
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }
}
