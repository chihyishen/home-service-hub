export interface ItemRequest {
  name: string;
  category: string;
  location: string;
  quantity: number;
  note: string;
  imageUrl: string;
}

export interface ItemResponse {
  id: number;
  name: string;
  category: string;
  location: string;
  quantity: number;
  note: string;
  imageUrl: string;
  createdAt: string;
  updatedAt: string;
}
