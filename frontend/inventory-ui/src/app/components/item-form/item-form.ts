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
      <div class="col-12 col-md-10 col-lg-8">
        <div class="card shadow-sm">
          <div class="card-header bg-white py-3 border-bottom-0">
            <h4 class="mb-0 fw-bold text-center text-md-start">
              <i class="bi me-2" [ngClass]="isEditMode() ? 'bi-pencil-square' : 'bi-plus-circle-fill'"></i>
              {{ isEditMode() ? '編輯物品' : '新增物品' }}
            </h4>
          </div>
          <div class="card-body p-3 p-md-4">
            <form [formGroup]="itemForm" (ngSubmit)="onSubmit()">
              <div class="mb-3">
                <label for="name" class="form-label fw-bold small text-uppercase">名稱</label>
                <input id="name" type="text" class="form-control form-control-lg" formControlName="name" placeholder="請輸入物品名稱">
                <div *ngIf="itemForm.get('name')?.touched && itemForm.get('name')?.invalid" class="text-danger small mt-1">
                  請輸入名稱。
                </div>
              </div>

              <div class="row mb-3 g-3">
                <div class="col-12 col-md-6">
                  <label for="category" class="form-label fw-bold small text-uppercase">類別</label>
                  <input id="category" type="text" class="form-control" formControlName="category" placeholder="例如：電子產品">
                </div>
                <div class="col-12 col-md-6">
                  <label for="location" class="form-label fw-bold small text-uppercase">位置</label>
                  <input id="location" type="text" class="form-control" formControlName="location" placeholder="例如：廚房櫥櫃">
                </div>
              </div>

              <div class="row mb-3 g-3">
                <div class="col-12 col-md-6">
                  <label for="quantity" class="form-label fw-bold small text-uppercase">數量</label>
                  <input id="quantity" type="number" class="form-control" formControlName="quantity">
                  <div *ngIf="itemForm.get('quantity')?.touched && itemForm.get('quantity')?.invalid" class="text-danger small mt-1">
                    數量必須為 0 或以上。
                  </div>
                </div>
              </div>

              <div class="mb-4">
                <label for="note" class="form-label fw-bold small text-uppercase">備註</label>
                <textarea id="note" class="form-control" formControlName="note" rows="3" placeholder="其他詳細資訊..."></textarea>
              </div>

              <div class="row g-2">
                <div class="col-12 col-md-auto">
                  <button type="submit" class="btn btn-primary px-5 w-100" [disabled]="itemForm.invalid">
                    <i class="bi me-2" [ngClass]="isEditMode() ? 'bi-save' : 'bi-check-circle'"></i>
                    {{ isEditMode() ? '更新' : '建立' }}
                  </button>
                </div>
                <div class="col-12 col-md-auto">
                  <button type="button" routerLink="/" class="btn btn-light px-4 w-100 border text-muted">取消</button>
                </div>
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
      note: ['']
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
