import { Injectable } from '@angular/core';
import Keycloak from 'keycloak-js';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly keycloak = new Keycloak({ url: environment.oidcUrl, realm: environment.oidcRealm, clientId: environment.oidcClientId });
  private initialized = false;

  async init(): Promise<void> {
    if (this.initialized) return;
    await this.keycloak.init({ onLoad: 'login-required', pkceMethod: 'S256', checkLoginIframe: false });
    this.initialized = true;
  }
  get authenticated(): boolean { return this.keycloak.authenticated === true; }
  async accessToken(): Promise<string | undefined> {
    if (!this.authenticated) return undefined;
    try { await this.keycloak.updateToken(30); return this.keycloak.token; }
    catch { await this.login(); return undefined; }
  }
  login(): Promise<void> { return this.keycloak.login({ redirectUri: window.location.origin + window.location.pathname }); }
  async logout(): Promise<void> { this.keycloak.clearToken(); await this.keycloak.logout({ redirectUri: window.location.origin + '/' }); }
}
