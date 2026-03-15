import { Component, input, output, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-list-item',
  imports: [CommonModule],
  templateUrl: './list-item.html',
  styleUrl: './list-item.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ListItemComponent {
  clickable = input<boolean>(true);
  itemClick = output<MouseEvent>();

  onClick(event: MouseEvent) {
    if (this.clickable()) {
      this.itemClick.emit(event);
    }
  }
}
