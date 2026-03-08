package com.inventory.item;

import com.inventory.item.dto.ItemRequest;
import com.inventory.item.dto.ItemResponse;
import com.inventory.item.dto.ShoppingListItemRequest;
import com.inventory.item.dto.ShoppingListItemResponse;
import com.inventory.item.model.ShoppingListItemSource;
import com.inventory.item.model.ShoppingListItemStatus;
import com.inventory.item.repository.InventoryTransactionRepository;
import com.inventory.item.repository.ItemRepository;
import com.inventory.item.repository.ShoppingListItemRepository;
import com.inventory.item.service.ItemService;
import com.inventory.item.service.ShoppingListService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class ShoppingListServiceIntegrationTest extends IntegrationTestBase {

    @Autowired
    private ShoppingListService shoppingListService;

    @Autowired
    private ItemService itemService;

    @Autowired
    private ShoppingListItemRepository shoppingListItemRepository;

    @Autowired
    private InventoryTransactionRepository inventoryTransactionRepository;

    @Autowired
    private ItemRepository itemRepository;

    @BeforeEach
    void setUp() {
        shoppingListItemRepository.deleteAll();
        inventoryTransactionRepository.deleteAll();
        itemRepository.deleteAll();
    }

    @Test
    void shouldGenerateShoppingListFromLowStockWithoutDuplicates() {
        ItemResponse lowStockItem = itemService.createItem(new ItemRequest(
                "廚房紙巾", "廚房", "抽屜", 1,
                2, 6, true, "ACTIVE", null, null
        ));

        itemService.createItem(new ItemRequest(
                "垃圾袋", "廚房", "抽屜", 5,
                1, 6, true, "ACTIVE", null, null
        ));

        List<ShoppingListItemResponse> first = shoppingListService.generateFromLowStock();
        assertThat(first).hasSize(1);
        assertThat(first.getFirst().itemId()).isEqualTo(lowStockItem.id());
        assertThat(first.getFirst().suggestedQuantity()).isEqualTo(5);
        assertThat(first.getFirst().source()).isEqualTo(ShoppingListItemSource.LOW_STOCK_RULE);

        List<ShoppingListItemResponse> second = shoppingListService.generateFromLowStock();
        assertThat(second).hasSize(1);
        assertThat(shoppingListItemRepository.count()).isEqualTo(1);
    }

    @Test
    void shouldCreateAndUpdateManualShoppingListItem() {
        ShoppingListItemResponse created = shoppingListService.createItem(new ShoppingListItemRequest(
                null, "咖啡豆", 2, ShoppingListItemStatus.PENDING, ShoppingListItemSource.MANUAL, "手動補貨"
        ));

        assertThat(created.status()).isEqualTo(ShoppingListItemStatus.PENDING);
        assertThat(created.source()).isEqualTo(ShoppingListItemSource.MANUAL);

        ShoppingListItemResponse updated = shoppingListService.updateItem(
                created.id(),
                new ShoppingListItemRequest(null, null, null, ShoppingListItemStatus.PURCHASED, null, "已購")
        );

        assertThat(updated.status()).isEqualTo(ShoppingListItemStatus.PURCHASED);
        assertThat(updated.note()).isEqualTo("已購");
    }
}
