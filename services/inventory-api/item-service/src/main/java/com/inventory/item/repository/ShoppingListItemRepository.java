package com.inventory.item.repository;

import com.inventory.item.model.ShoppingListItem;
import com.inventory.item.model.ShoppingListItemStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface ShoppingListItemRepository extends JpaRepository<ShoppingListItem, Long> {
    List<ShoppingListItem> findByStatusOrderByCreatedAtDesc(ShoppingListItemStatus status);

    boolean existsByItemIdAndStatus(Long itemId, ShoppingListItemStatus status);

    @Modifying
    @Query("delete from ShoppingListItem s where s.item.id = :itemId")
    int deleteByItemId(@Param("itemId") Long itemId);
}
