import { getRequestConfig } from 'next-intl/server';
import { cookies, headers } from 'next/headers';

export const locales = ['en', 'es', 'fr'] as const;
export type Locale = (typeof locales)[number];

export const localeNames: Record<Locale, string> = {
  en: 'English',
  es: 'Espanol',
  fr: 'Francais',
};

export const defaultLocale: Locale = 'en';

export function getLocaleFromCookie(): Locale {
  // This is only used client-side
  if (typeof document !== 'undefined') {
    const match = document.cookie.match(/(?:^|; )locale=([^;]*)/);
    if (match && locales.includes(match[1] as Locale)) {
      return match[1] as Locale;
    }
  }
  return defaultLocale;
}

export function setLocaleCookie(locale: Locale) {
  if (typeof document !== 'undefined') {
    document.cookie = `locale=${locale};path=/;max-age=31536000;SameSite=Lax`;
  }
}

export default getRequestConfig(async () => {
  // Get locale from cookie or Accept-Language header
  const cookieStore = await cookies();
  const headerStore = await headers();

  let locale: Locale = defaultLocale;

  // Check cookie first
  const localeCookie = cookieStore.get('locale');
  if (localeCookie && locales.includes(localeCookie.value as Locale)) {
    locale = localeCookie.value as Locale;
  } else {
    // Fall back to Accept-Language header
    const acceptLanguage = headerStore.get('accept-language');
    if (acceptLanguage) {
      const browserLocale = acceptLanguage.split(',')[0].split('-')[0];
      if (locales.includes(browserLocale as Locale)) {
        locale = browserLocale as Locale;
      }
    }
  }

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  };
});
