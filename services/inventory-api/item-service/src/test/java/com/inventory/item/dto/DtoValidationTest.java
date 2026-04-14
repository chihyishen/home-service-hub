package com.inventory.item.dto;

import com.inventory.item.model.InventoryTransactionType;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class DtoValidationTest {

    private static Validator validator;

    @BeforeAll
    static void setUpValidator() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @Test
    void testItemRequestInvalid() {
        ItemRequest req = new ItemRequest("", "工具", "A層", -1, -2, -3, true, "ACTIVE", "note", "url");
        Set<ConstraintViolation<ItemRequest>> violations = validator.validate(req);
        assertFalse(violations.isEmpty());
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("name")));
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("quantity")));
    }

    @Test
    void testInventoryTransactionRequestInvalid() {
        InventoryTransactionRequest req = new InventoryTransactionRequest(null, null, null, null, null, null);
        Set<ConstraintViolation<InventoryTransactionRequest>> violations = validator.validate(req);
        assertFalse(violations.isEmpty());
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("type")));
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("deltaQuantity")));
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("source")));
    }

    @Test
    void testShoppingListItemRequestInvalid() {
        ShoppingListItemRequest req = new ShoppingListItemRequest(null, "", 0, null, null, null);
        Set<ConstraintViolation<ShoppingListItemRequest>> violations = validator.validate(req);
        assertFalse(violations.isEmpty());
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("itemNameSnapshot")));
        assertTrue(violations.stream().anyMatch(v -> v.getPropertyPath().toString().equals("suggestedQuantity")));
    }
}
