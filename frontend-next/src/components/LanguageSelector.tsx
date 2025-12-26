'use client';

import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useTransition } from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Globe, Check } from 'lucide-react';
import { locales, localeNames, type Locale, setLocaleCookie } from '@/i18n';

export function LanguageSelector() {
  const locale = useLocale() as Locale;
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const handleLocaleChange = (newLocale: Locale) => {
    if (newLocale !== locale) {
      setLocaleCookie(newLocale);
      startTransition(() => {
        router.refresh();
      });
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          disabled={isPending}
        >
          <Globe className="h-5 w-5" />
          <span className="sr-only">Change language</span>
          {isPending && (
            <span className="absolute inset-0 flex items-center justify-center">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {locales.map((loc) => (
          <DropdownMenuItem
            key={loc}
            onClick={() => handleLocaleChange(loc)}
            className="flex items-center justify-between gap-2"
          >
            <span>{localeNames[loc]}</span>
            {loc === locale && <Check className="h-4 w-4" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function SimpleLanguageSelector() {
  const locale = useLocale() as Locale;
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const handleLocaleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLocale = e.target.value as Locale;
    if (newLocale !== locale) {
      setLocaleCookie(newLocale);
      startTransition(() => {
        router.refresh();
      });
    }
  };

  return (
    <select
      value={locale}
      onChange={handleLocaleChange}
      disabled={isPending}
      className="bg-transparent border border-border rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
    >
      {locales.map((loc) => (
        <option key={loc} value={loc}>
          {localeNames[loc]}
        </option>
      ))}
    </select>
  );
}
