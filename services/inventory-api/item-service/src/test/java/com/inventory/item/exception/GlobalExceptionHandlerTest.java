package com.inventory.item.exception;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.core.MethodParameter;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class GlobalExceptionHandlerTest {

    private GlobalExceptionHandler handler;
    private WebRequest request;

    @BeforeEach
    void setUp() {
        handler = new GlobalExceptionHandler();
        request = mock(WebRequest.class);
        when(request.getDescription(false)).thenReturn("uri=/test");
    }

    @Test
    void testHandleDataIntegrityViolationException() {
        DataIntegrityViolationException ex = new DataIntegrityViolationException("Duplicate entry");
        ResponseEntity<GlobalExceptionHandler.ErrorResponse> response = handler.handleDataIntegrityViolationException(ex, request);

        assertEquals(HttpStatus.CONFLICT, response.getStatusCode());
        assertEquals(HttpStatus.CONFLICT.value(), response.getBody().status());
        assertEquals("Conflict", response.getBody().error());
    }

    @Test
    void testHandleNoResourceFoundException() {
        when(request.getDescription(false)).thenReturn("uri=/api-docs");
        NoResourceFoundException ex = new NoResourceFoundException(
                HttpMethod.GET,
                "/private/internal-resource.yaml",
                "/static"
        );

        ResponseEntity<GlobalExceptionHandler.ErrorResponse> response =
                handler.handleNoResourceFoundException(ex, request);

        assertEquals(HttpStatus.NOT_FOUND, response.getStatusCode());
        assertEquals(HttpStatus.NOT_FOUND.value(), response.getBody().status());
        assertEquals("Not Found", response.getBody().error());
        assertEquals("Resource not found.", response.getBody().message());
        assertEquals("uri=/api-docs", response.getBody().path());
    }

    @Test
    void testHandleMethodArgumentNotValidException() {
        MethodParameter parameter = mock(MethodParameter.class);
        BindingResult bindingResult = mock(BindingResult.class);
        FieldError fieldError = new FieldError("objectName", "fieldName", "must not be blank");
        when(bindingResult.getAllErrors()).thenReturn(List.of(fieldError));

        MethodArgumentNotValidException ex = new MethodArgumentNotValidException(parameter, bindingResult);

        ResponseEntity<Object> response = handler.handleValidationExceptions(ex, request);

        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertTrue(response.getBody() instanceof Map);
        Map<String, String> errors = (Map<String, String>) response.getBody();
        assertEquals("must not be blank", errors.get("fieldName"));
    }
}
