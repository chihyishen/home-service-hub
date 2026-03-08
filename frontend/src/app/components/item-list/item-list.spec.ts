import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { provideRouter } from '@angular/router';
import { ItemListComponent } from './item-list';
import { ItemService } from '../../services/item.service';

describe('ItemListComponent', () => {
  let component: ItemListComponent;
  let fixture: ComponentFixture<ItemListComponent>;

  const itemServiceMock = {
    getAll: () => of([]),
    getCategories: () => of([]),
    getLocations: () => of([]),
    create: () => of({}),
    update: () => of({}),
    delete: () => of(undefined),
    uploadImage: () => of({}),
    createTransaction: () => of({}),
    getTransactions: () => of([])
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ItemListComponent],
      providers: [
        provideRouter([]),
        { provide: ItemService, useValue: itemServiceMock }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ItemListComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
