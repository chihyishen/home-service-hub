package com.inventory.item.dto;

public record ItemRequest(
        String name,
        String category,
        String location,
        Integer quantity,
        String note,
        String imageUrl) {

}
