import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { provideRouter } from '@angular/router';
import { ItemListComponent } from './item-list';
import { ItemService } from '../../services/item.service';
import { ShoppingListService } from '../../services/shopping-list.service';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ItemResponse } from '../../models/item.model';

describe('ItemListComponent', () => {
  let component: ItemListComponent;
  let fixture: ComponentFixture<ItemListComponent>;
  let itemService: ItemService;
  let shoppingListService: ShoppingListService;
  let confirmationService: ConfirmationService;
  let messageService: MessageService;

  const itemServiceMock = {
    getAll: () => of([]),
    getAllFiltered: () => of([]),
    getCategories: () => of([]),
    getLocations: () => of([]),
    create: () => of({}),
    update: () => of({}),
    delete: () => of(undefined),
    uploadImage: () => of({}),
    createTransaction: () => of({}),
    getTransactions: () => of([])
  };

  const shoppingListServiceMock = {
    generateFromLowStock: () => of([])
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ItemListComponent],
      providers: [
        provideRouter([]),
        { provide: ItemService, useValue: itemServiceMock },
        { provide: ShoppingListService, useValue: shoppingListServiceMock }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ItemListComponent);
    component = fixture.componentInstance;
    itemService = TestBed.inject(ItemService);
    shoppingListService = TestBed.inject(ShoppingListService);
    confirmationService = fixture.debugElement.injector.get(ConfirmationService);
    messageService = fixture.debugElement.injector.get(MessageService);
    await fixture.whenStable();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should group items by location', () => {
    const mockItems: ItemResponse[] = [
      { id: 1, name: 'Item A', quantity: 5, location: 'Kitchen', category: 'Food', stockStatus: 'OK' } as any,
      { id: 2, name: 'Item B', quantity: 2, location: 'Bathroom', category: 'Hygiene', stockStatus: 'LOW' } as any,
      { id: 3, name: 'Item C', quantity: 10, location: '', category: 'Tools', stockStatus: 'OK' } as any,
      { id: 4, name: 'Item D', quantity: 1, location: 'Kitchen', category: 'Food', stockStatus: 'OK' } as any
    ];

    component.items.set(mockItems);
    const groups = component.groupedItems();

    expect(groups.length).toBe(3);
    // groups are sorted: Bathroom, Kitchen, 未知位置
    expect(groups[0].location).toBe('Bathroom');
    expect(groups[0].items.length).toBe(1);

    expect(groups[1].location).toBe('Kitchen');
    expect(groups[1].items.length).toBe(2);

    expect(groups[2].location).toBe('未知位置');
    expect(groups[2].items.length).toBe(1);
  });

  it('should debounce search inputs', () => {
    vi.useFakeTimers();
    const getAllFilteredSpy = vi.spyOn(itemService, 'getAllFiltered').mockReturnValue(of([]));
    
    component.searchKeyword = 'test';
    component.onSearchChange();
    component.searchKeyword = 'test search';
    component.onSearchChange();

    expect(getAllFilteredSpy).not.toHaveBeenCalled();

    vi.advanceTimersByTime(299);
    expect(getAllFilteredSpy).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(getAllFilteredSpy).toHaveBeenCalledTimes(1);
    expect(getAllFilteredSpy).toHaveBeenCalledWith('test search', false);
    vi.useRealTimers();
  });

  it('should confirm and delete item', () => {
    const confirmSpy = vi.spyOn(confirmationService, 'confirm').mockImplementation((options: any) => {
      options.accept?.();
      return confirmationService;
    });
    const deleteSpy = vi.spyOn(itemService, 'delete').mockReturnValue(of(undefined));
    const messageSpy = vi.spyOn(messageService, 'add');

    component.deleteItem(123);

    expect(confirmSpy).toHaveBeenCalled();
    expect(deleteSpy).toHaveBeenCalledWith(123);
    expect(messageSpy).toHaveBeenCalledWith(expect.objectContaining({
      severity: 'success',
      detail: '物品已刪除'
    }));
  });

  it('should request generating shopping list from low stock items', () => {
    const generateSpy = vi.spyOn(shoppingListService, 'generateFromLowStock').mockReturnValue(of([{ id: 1 } as any]));
    const messageSpy = vi.spyOn(messageService, 'add');

    component.addLowStockToShoppingList();

    expect(generateSpy).toHaveBeenCalled();
    expect(messageSpy).toHaveBeenCalledWith(expect.objectContaining({
      severity: 'success',
      detail: '已將 1 項低庫存物品加入購物清單'
    }));
  });
});
