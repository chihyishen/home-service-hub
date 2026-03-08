package com.inventory.item.repository;

import com.inventory.item.model.InventoryTransaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface InventoryTransactionRepository extends JpaRepository<InventoryTransaction, Long> {
    List<InventoryTransaction> findByItemIdOrderByOccurredAtDesc(Long itemId);

    @Modifying
    @Query("delete from InventoryTransaction t where t.item.id = :itemId")
    int deleteByItemId(@Param("itemId") Long itemId);
}
