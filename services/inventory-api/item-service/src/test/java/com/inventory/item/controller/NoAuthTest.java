package com.inventory.item.controller;

import com.inventory.item.IntegrationTestBase;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@AutoConfigureMockMvc
@TestPropertySource(properties = "AUTH_ENFORCEMENT_ENABLED=true")
class NoAuthTest extends IntegrationTestBase {

    @Autowired
    MockMvc mockMvc;

    @Test
    void postWithoutTokenSucceedsEvenWithEnforcementFlag() throws Exception {
        mockMvc.perform(get("/api/items")).andExpect(status().isOk());
    }
}
