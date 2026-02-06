import { Routes } from '@angular/router';
import { ItemListComponent } from './components/item-list/item-list';
import { ItemFormComponent } from './components/item-form/item-form';

export const routes: Routes = [
  { path: '', component: ItemListComponent },
  { path: 'add', component: ItemFormComponent },
  { path: 'edit/:id', component: ItemFormComponent },
  { path: '**', redirectTo: '' }
];