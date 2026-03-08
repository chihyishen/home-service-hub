export interface ItemRequest {
  name: string;
  category?: string;
  location?: string;
  quantity: number;
  minQuantity?: number | null;
  targetQuantity?: number | null;
  isConsumable?: boolean;
  status?: string;
  note?: string;
  imageUrl?: string;
}

export interface ItemResponse {
  id: number;
  name: string;
  category?: string;
  location?: string;
  quantity: number;
  minQuantity?: number | null;
  targetQuantity?: number | null;
  isConsumable?: boolean;
  status?: string;
  lastRestockedAt?: string | null;
  isLowStock?: boolean;
  stockStatus?: 'OUT' | 'LOW' | 'NORMAL' | 'UNKNOWN' | string;
  note?: string;
  imageUrl?: string;
  createdAt: string;
  updatedAt: string;
}

export type InventoryTransactionType = 'CONSUME' | 'RESTOCK' | 'ADJUST';

export interface InventoryTransactionRequest {
  type: InventoryTransactionType;
  deltaQuantity?: number;
  actualQuantity?: number;
  reason?: string;
  operatorName?: string;
}

export interface InventoryTransactionResponse {
  id: number;
  itemId: number;
  type: InventoryTransactionType;
  deltaQuantity: number;
  beforeQuantity: number;
  afterQuantity: number;
  reason?: string;
  source: 'MANUAL' | 'SYSTEM' | string;
  operatorName?: string;
  occurredAt: string;
  createdAt: string;
}

export interface ItemTransactionResultResponse {
  item: ItemResponse;
  transaction: InventoryTransactionResponse;
}

export interface ShoppingListItemRequest {
  itemId?: number | null;
  itemNameSnapshot?: string;
  suggestedQuantity?: number;
  status?: 'PENDING' | 'PURCHASED' | 'SKIPPED';
  source?: 'LOW_STOCK_RULE' | 'MANUAL';
  note?: string;
}

export interface ShoppingListItemResponse {
  id: number;
  itemId?: number | null;
  itemNameSnapshot: string;
  suggestedQuantity: number;
  status: 'PENDING' | 'PURCHASED' | 'SKIPPED';
  source: 'LOW_STOCK_RULE' | 'MANUAL' | string;
  note?: string;
  createdAt: string;
  updatedAt: string;
}
