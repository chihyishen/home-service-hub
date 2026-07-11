import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { from, switchMap } from 'rxjs';
import { AuthService } from '../auth/auth.service';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const url = new URL(request.url, window.location.origin);
  const protectedRequest = url.origin === window.location.origin && (url.pathname.startsWith('/api/') || url.pathname.startsWith('/minio/'));
  if (!protectedRequest) return next(request);
  return from(inject(AuthService).accessToken()).pipe(switchMap(token => next(token ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : request)));
};
