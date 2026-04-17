import { Routes } from '@angular/router';
import { HomePageComponent } from './features/home/home-page/home-page';
import { NewsChatbotPageComponent } from './features/news/news-chatbot-page/news-chatbot-page';
import { NewsDetailsPageComponent } from './features/news/news-details-page/news-details-page';
import { AuthCard } from './shared/components/auth-card/auth-card';

export const appRoutes: Routes = [
  {
    path: '',
    component: HomePageComponent
  },
  {
    path: 'details/:id',
    component: NewsDetailsPageComponent
  },
  {
    path: 'details/:id/ask-ai',
    component: NewsChatbotPageComponent
  },
  {
    path: 'login',
    component: AuthCard
  },
  {
    path: 'register',
    component: AuthCard
  },
  {
    path: '**',
    redirectTo: ''
  }

];
