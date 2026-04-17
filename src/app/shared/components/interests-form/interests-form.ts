import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CategoryApiOption } from '../../../core/models/auth.model';

@Component({
  selector: 'app-interests-form',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './interests-form.html',
  styleUrls: ['./interests-form.css']
})
export class InterestsForm {
  @Input({ required: true }) categories: CategoryApiOption[] = [];
  @Output() back = new EventEmitter<void>();
  @Output() complete = new EventEmitter<string[]>();

  selected: string[] = [];
  errorMessage = '';

  toggleInterest(category: string): void {
    if (this.selected.includes(category)) {
      this.selected = this.selected.filter((item) => item !== category);
      this.errorMessage = '';
      return;
    }

    if (this.selected.length >= 3) {
      this.errorMessage = 'You can choose a maximum of 3 favorite categories.';
      return;
    }

    this.selected = [...this.selected, category];
    this.errorMessage = '';
  }

  submit(): void {
    this.complete.emit(this.selected);
  }
}
