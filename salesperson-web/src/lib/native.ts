/** Capacitor wiring: splash, status bar, hardware back button, connectivity. */

import { App } from '@capacitor/app';
import { Capacitor } from '@capacitor/core';
import { Geolocation } from '@capacitor/geolocation';
import { Network } from '@capacitor/network';
import { SplashScreen } from '@capacitor/splash-screen';
import { StatusBar, Style } from '@capacitor/status-bar';

export const isNative = Capacitor.isNativePlatform();

export async function initNative(): Promise<void> {
  if (!isNative) return;
  try {
    await StatusBar.setStyle({ style: Style.Dark });
    await StatusBar.setBackgroundColor({ color: '#1f2a44' });
  } catch {
    /* status bar is unavailable on some devices */
  }
  try {
    await SplashScreen.hide();
  } catch {
    /* ignore */
  }
}

/**
 * Android back button: go back inside the app, and only exit from the home
 * screen - so a half-written report is never lost by a stray back tap.
 */
export function registerBackButton(
  canGoBack: () => boolean,
  goBack: () => void,
  confirmExit: () => void,
): void {
  if (!isNative) return;
  App.addListener('backButton', () => {
    if (canGoBack()) {
      goBack();
    } else {
      confirmExit();
    }
  });
}

export function onResume(handler: () => void): void {
  if (!isNative) {
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') handler();
    });
    return;
  }
  App.addListener('appStateChange', ({ isActive }) => {
    if (isActive) handler();
  });
}

export function onNetworkRestored(handler: () => void): void {
  if (!isNative) {
    window.addEventListener('online', handler);
    return;
  }
  Network.addListener('networkStatusChange', (status) => {
    if (status.connected) handler();
  });
}

export async function isOnline(): Promise<boolean> {
  if (!isNative) return navigator.onLine;
  try {
    const status = await Network.getStatus();
    return status.connected;
  } catch {
    return true;
  }
}

/**
 * Where the phone is right now, so the person standing at the customer's gate
 * can pin a place the office only had as text.
 */
export async function currentPosition(): Promise<{ latitude: number; longitude: number }> {
  if (isNative) {
    const permission = await Geolocation.checkPermissions();
    if (permission.location !== 'granted') {
      const requested = await Geolocation.requestPermissions();
      if (requested.location !== 'granted') {
        throw new Error('Location permission is needed to pin this place.');
      }
    }
    const position = await Geolocation.getCurrentPosition({
      enableHighAccuracy: true,
      timeout: 15000,
    });
    return {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
    };
  }

  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('This browser cannot share a location.'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        }),
      () => reject(new Error('Could not read your location. Check location permission.')),
      { enableHighAccuracy: true, timeout: 15000 },
    );
  });
}

/**
 * Open an external link (Google Maps, tel:) outside the WebView so the native
 * app handles it. Capacitor routes these through an Android intent.
 */
export function openExternal(url: string): void {
  window.open(url, '_blank', 'noreferrer');
}
