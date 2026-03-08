package com.inventory.item.repository;

import com.inventory.item.model.Item;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ItemRepository extends JpaRepository<Item, Long> {

    List<Item> findByCategory(String category);

    List<Item> findByLocation(String location);

    @Query("SELECT DISTINCT i.category FROM Item i WHERE i.category IS NOT NULL AND i.category <> '' ORDER BY i.category")
    List<String> findDistinctCategories();

    @Query("SELECT DISTINCT i.location FROM Item i WHERE i.location IS NOT NULL AND i.location <> '' ORDER BY i.location")
    List<String> findDistinctLocations();

    List<Item> findByNameContainingIgnoreCaseOrNoteContainingIgnoreCase(String name, String note);

    @Query("""
            SELECT i FROM Item i
            WHERE (:keyword IS NULL OR :keyword = '' OR
                   LOWER(i.name) LIKE LOWER(CONCAT('%', :keyword, '%')) OR
                   LOWER(COALESCE(i.note, '')) LIKE LOWER(CONCAT('%', :keyword, '%')))
              AND (:category IS NULL OR :category = '' OR i.category = :category)
              AND (:location IS NULL OR :location = '' OR i.location = :location)
              AND (:lowStockOnly = false OR (i.minQuantity IS NOT NULL AND i.quantity <= i.minQuantity))
            """)
    List<Item> findByFilters(String keyword, Boolean lowStockOnly, String category, String location);

    @Modifying
    @Query("DELETE FROM Item i WHERE i.id = :id")
    int hardDeleteById(@Param("id") Long id);
}
