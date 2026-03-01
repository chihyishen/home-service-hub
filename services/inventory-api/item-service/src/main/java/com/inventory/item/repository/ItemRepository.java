package com.inventory.item.repository;

import com.inventory.item.model.Item;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
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
}
