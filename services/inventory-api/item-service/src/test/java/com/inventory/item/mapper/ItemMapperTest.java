package com.inventory.item.mapper;

import static org.assertj.core.api.Assertions.assertThat;

import com.inventory.item.dto.ItemRequest;
import com.inventory.item.model.Item;
import org.junit.jupiter.api.Test;
import org.mapstruct.factory.Mappers;

class ItemMapperTest {

    private final ItemMapper mapper = Mappers.getMapper(ItemMapper.class);

    @Test
    void updateClearsMinQuantityButKeepsOtherFieldsOnNull() {
        Item item = new Item();
        item.setMinQuantity(2);
        item.setNote("keep");

        mapper.updateEntityFromRequest(new ItemRequest("x", null, null, 1, null, null, null), item);

        assertThat(item.getMinQuantity()).isNull();
        assertThat(item.getNote()).isEqualTo("keep");
    }
}
