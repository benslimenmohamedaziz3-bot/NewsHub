import { ComponentFixture, TestBed } from '@angular/core/testing';

import { InterestsForm } from './interests-form';

describe('InterestsForm', () => {
  let component: InterestsForm;
  let fixture: ComponentFixture<InterestsForm>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InterestsForm],
    }).compileComponents();

    fixture = TestBed.createComponent(InterestsForm);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
