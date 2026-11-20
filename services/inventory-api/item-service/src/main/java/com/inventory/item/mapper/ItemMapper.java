package com.inventory.item.mapper;

import com.inventory.item.dto.ItemRequest;
import com.inventory.item.dto.ItemResponse;
import com.inventory.item.model.Item;
import org.mapstruct.*;

@Mapper(componentModel = "spring")
public interface ItemMapper {

    @Mapping(target = "isLowStock", expression = "java(isLowStock(item))")
    @Mapping(target = "stockStatus", expression = "java(getStockStatus(item))")
    ItemResponse toResponse(Item item);

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    @Mapping(target = "version", ignore = true)
    Item toEntity(ItemRequest request);

    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    @Mapping(target = "version", ignore = true)
    // 清空門檻 = 改成「等用完」，空值也要寫回去
    @Mapping(target = "minQuantity", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.SET_TO_NULL)
    void updateEntityFromRequest(ItemRequest request, @MappingTarget Item item);

    default Boolean isLowStock(Item item) {
        if (item.getMinQuantity() == null) {
            return false;
        }
        return item.getQuantity() != null && item.getQuantity() <= item.getMinQuantity();
    }

    default String getStockStatus(Item item) {
        Integer quantity = item.getQuantity();
        if (quantity == null) {
            return "UNKNOWN";
        }
        if (quantity == 0) {
            return "OUT";
        }
        if (isLowStock(item)) {
            return "LOW";
        }
        return "NORMAL";
    }
}
