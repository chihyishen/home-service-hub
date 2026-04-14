package com.inventory.item;

import com.inventory.item.dto.*;
import com.inventory.item.exception.BadRequestException;
import com.inventory.item.model.InventoryTransactionSource;
import com.inventory.item.model.InventoryTransactionType;
import com.inventory.item.repository.InventoryTransactionRepository;
import com.inventory.item.repository.ItemRepository;
import com.inventory.item.service.ItemService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ItemInventoryWorkflowIntegrationTest extends IntegrationTestBase {

    @Autowired
    private ItemService itemService;

    @Autowired
    private ItemRepository itemRepository;

    @Autowired
    private InventoryTransactionRepository inventoryTransactionRepository;

    @BeforeEach
    void setUp() {
        inventoryTransactionRepository.deleteAll();
        itemRepository.deleteAll();
    }

    @Test
    void shouldHandleConsumeRestockAdjustFlowAndRecordTransactions() {
        ItemResponse item = itemService.createItem(new ItemRequest(
                "衛生紙", "浴室", "A櫃", 5,
                2, 8, true, "ACTIVE", "測試", null
        ));

        ItemTransactionResultResponse consumeResult = itemService.createTransaction(
                item.id(),
                new InventoryTransactionRequest(InventoryTransactionType.CONSUME, 3, null, "日常使用", InventoryTransactionSource.MANUAL, "chihyi")
        );

        assertThat(consumeResult.item().quantity()).isEqualTo(2);
        assertThat(consumeResult.item().isLowStock()).isTrue();
        assertThat(consumeResult.item().stockStatus()).isEqualTo("LOW");
        assertThat(consumeResult.transaction().beforeQuantity()).isEqualTo(5);
        assertThat(consumeResult.transaction().afterQuantity()).isEqualTo(2);

        ItemTransactionResultResponse restockResult = itemService.createTransaction(
                item.id(),
                new InventoryTransactionRequest(InventoryTransactionType.RESTOCK, 4, null, "補貨", InventoryTransactionSource.MANUAL, "chihyi")
        );

        assertThat(restockResult.item().quantity()).isEqualTo(6);
        assertThat(restockResult.item().lastRestockedAt()).isNotNull();
        assertThat(restockResult.transaction().beforeQuantity()).isEqualTo(2);
        assertThat(restockResult.transaction().afterQuantity()).isEqualTo(6);

        ItemTransactionResultResponse adjustResult = itemService.createTransaction(
                item.id(),
                new InventoryTransactionRequest(InventoryTransactionType.ADJUST, null, 1, "盤點修正", InventoryTransactionSource.MANUAL, "chihyi")
        );

        assertThat(adjustResult.item().quantity()).isEqualTo(1);
        assertThat(adjustResult.transaction().deltaQuantity()).isEqualTo(-5);
        assertThat(itemService.getTransactionsByItemId(item.id(), 10)).hasSize(3);
    }

    @Test
    void shouldRejectConsumeThatMakesQuantityNegative() {
        ItemResponse item = itemService.createItem(new ItemRequest(
                "洗髮精", "浴室", "A櫃", 1,
                1, 4, true, "ACTIVE", null, null
        ));

        assertThatThrownBy(() -> itemService.createTransaction(
                item.id(),
                new InventoryTransactionRequest(InventoryTransactionType.CONSUME, 2, null, "超扣", InventoryTransactionSource.MANUAL, "tester")
        )).isInstanceOf(BadRequestException.class)
                .hasMessageContaining("cannot be negative");
    }

    @Test
    void shouldFilterLowStockByCategoryAndLocation() {
        itemService.createItem(new ItemRequest(
                "牙膏", "浴室", "A櫃", 1,
                2, 5, true, "ACTIVE", null, null
        ));
        itemService.createItem(new ItemRequest(
                "洗碗精", "廚房", "B櫃", 5,
                1, 5, true, "ACTIVE", null, null
        ));

        List<ItemResponse> filtered = itemService.getAllItems(null, true, "浴室", "A櫃");
        assertThat(filtered).hasSize(1);
        assertThat(filtered.getFirst().name()).isEqualTo("牙膏");
        assertThat(filtered.getFirst().isLowStock()).isTrue();
    }
}
