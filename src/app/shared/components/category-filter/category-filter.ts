import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CategoryOption, NewsCategory } from '../../../core/models/category.model';
import { NewsDataType, NewsFilters, SelectOption } from '../../../core/models/filter.model';

@Component({
  selector: 'app-category-filter',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './category-filter.html',
  styleUrl: './category-filter.css'
})
export class CategoryFilterComponent {
  @Input({ required: true }) categories: CategoryOption[] = [];
  @Input({ required: true }) selectedCategory: NewsCategory = 'all';
  @Input({ required: true }) countryOptions: SelectOption[] = [];
  @Input({ required: true }) sourceOptions: SelectOption[] = [];
  @Input({ required: true }) dataTypeOptions: SelectOption[] = [];
  @Input({ required: true }) filters: NewsFilters = {
    category: 'all',
    country: '',
    source: '',
    date: '',
    dataType: ''
  };

  @Output() filtersChange = new EventEmitter<NewsFilters>();

  onSelect(category: NewsCategory): void {
    this.filtersChange.emit({
      category,
      country: '',
      source: '',
      date: '',
      dataType: ''
    });
  }

  onCountryChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.filtersChange.emit({
      category: 'all',
      country: value,
      source: '',
      date: '',
      dataType: ''
    });
  }

  onSourceChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.filtersChange.emit({
      category: 'all',
      country: '',
      source: value,
      date: '',
      dataType: ''
    });
  }

  onDateChange(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.filtersChange.emit({
      category: 'all',
      country: '',
      source: '',
      date: value,
      dataType: ''
    });
  }

  onDataTypeChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value as NewsDataType | '';
    this.filtersChange.emit({
      category: 'all',
      country: '',
      source: '',
      date: '',
      dataType: value
    });
  }
}