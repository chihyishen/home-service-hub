import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ItemService } from '../../services/item.service';
import { ItemRequest } from '../../models/item.model';

@Component({
  selector: 'app-item-form',
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  template: `
    <div class="row justify-content-center">
      <div class="col-md-8 col-lg-6">
        <div class="card">
          <div class="card-header bg-white py-3">
            <h4 class="mb-0">{{ isEditMode() ? 'Edit Item' : 'Add New Item' }}</h4>
          </div>
          <div class="card-body p-4">
            <form [formGroup]="itemForm" (ngSubmit)="onSubmit()">
              <div class="mb-3">
                <label for="name" class="form-label fw-bold">Name</label>
                <input id="name" type="text" class="form-control" formControlName="name" placeholder="Enter item name">
                <div *ngIf="itemForm.get('name')?.touched && itemForm.get('name')?.invalid" class="text-danger small mt-1">
                  Name is required.
                </div>
              </div>

              <div class="row mb-3">
                <div class="col-md-6">
                  <label for="category" class="form-label fw-bold">Category</label>
                  <input id="category" type="text" class="form-control" formControlName="category" placeholder="e.g. Electronics">
                </div>
                <div class="col-md-6">
                  <label for="location" class="form-label fw-bold">Location</label>
                  <input id="location" type="text" class="form-control" formControlName="location" placeholder="e.g. Kitchen Cabinet">
                </div>
              </div>

              <div class="row mb-3">
                <div class="col-md-6">
                  <label for="quantity" class="form-label fw-bold">Quantity</label>
                  <input id="quantity" type="number" class="form-control" formControlName="quantity">
                  <div *ngIf="itemForm.get('quantity')?.touched && itemForm.get('quantity')?.invalid" class="text-danger small mt-1">
                    Quantity must be 0 or more.
                  </div>
                </div>
                <div class="col-md-6">
                  <label for="imageUrl" class="form-label fw-bold">Image URL</label>
                  <input id="imageUrl" type="text" class="form-control" formControlName="imageUrl" placeholder="https://...">
                </div>
              </div>

              <div class="mb-4">
                <label for="note" class="form-label fw-bold">Note</label>
                <textarea id="note" class="form-control" formControlName="note" rows="3" placeholder="Additional details..."></textarea>
              </div>

              <div class="d-flex gap-2">
                <button type="submit" class="btn btn-primary px-4" [disabled]="itemForm.invalid">
                  <i class="bi" [ngClass]="isEditMode() ? 'bi-save' : 'bi-plus-circle'"></i>
                  {{ isEditMode() ? 'Update Item' : 'Create Item' }}
                </button>
                <button type="button" routerLink="/" class="btn btn-light px-4 border">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .form-control:focus {
      box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.15);
    }
  `]
})
export class ItemFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private itemService = inject(ItemService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  itemForm: FormGroup;
  isEditMode = signal(false);
  itemId = signal<number | null>(null);

  constructor() {
    this.itemForm = this.fb.group({
      name: ['', Validators.required],
      category: [''],
      location: [''],
      quantity: [0, [Validators.required, Validators.min(0)]],
      note: [''],
      imageUrl: ['']
    });
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode.set(true);
      this.itemId.set(+id);
      this.loadItem(+id);
    }
  }

  loadItem(id: number): void {
    this.itemService.getById(id).subscribe(item => {
      this.itemForm.patchValue(item);
    });
  }

  onSubmit(): void {
    if (this.itemForm.invalid) return;

    const itemData: ItemRequest = this.itemForm.value;
    
    if (this.isEditMode()) {
      this.itemService.update(this.itemId()!, itemData).subscribe(() => {
        this.router.navigate(['/']);
      });
    } else {
      this.itemService.create(itemData).subscribe(() => {
        this.router.navigate(['/']);
      });
    }
  }
}