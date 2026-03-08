package com.inventory.item.model;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDateTime;

@Entity
@Table(name = "items")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@EntityListeners(AuditingEntityListener.class)
public class Item {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;        // 物品名稱

    private String category;    // 分類 (例如：浴室、廚房)

    private String location;    // 存放位置 (例如：櫃子 A)

    @Column(nullable = false)
    private Integer quantity;   // 數量

    private Integer minQuantity;    // 低庫存門檻

    private Integer targetQuantity; // 理想庫存量

    @Column(nullable = false)
    @Builder.Default
    private Boolean isConsumable = true;

    @Column(nullable = false)
    @Builder.Default
    private String status = "ACTIVE";

    private LocalDateTime lastRestockedAt;

    @Version
    private Long version;

    private String note;        // 備註

    private String imageUrl;    // 圖片網址 (指向 MinIO)

    @CreatedDate
    @Column(updatable = false)
    private LocalDateTime createdAt; // 建立時間

    @LastModifiedDate
    private LocalDateTime updatedAt; // 最後修改時間
}
