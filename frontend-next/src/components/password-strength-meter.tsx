'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';

interface PasswordStrengthMeterProps {
  password: string;
  className?: string;
}

interface PasswordStrength {
  score: number; // 0-4
  label: string;
  color: string;
  suggestions: string[];
}

const SPECIAL_CHARS = /[!@#$%^&*(),.?":{}|<>\-_=+\[\]\\;'/`~]/;

function calculateStrength(password: string): PasswordStrength {
  let score = 0;
  const suggestions: string[] = [];

  // Length scoring
  if (password.length >= 8) {
    score += 1;
  } else {
    suggestions.push('Use at least 8 characters');
  }

  if (password.length >= 12) {
    score += 1;
  } else if (password.length >= 8) {
    suggestions.push('Consider using 12+ characters');
  }

  // Character variety
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasDigit = /\d/.test(password);
  const hasSpecial = SPECIAL_CHARS.test(password);

  const varietyCount = [hasUpper, hasLower, hasDigit, hasSpecial].filter(Boolean).length;

  if (varietyCount >= 3) score += 1;
  if (varietyCount >= 4) score += 1;

  if (!hasUpper) suggestions.push('Add uppercase letters');
  if (!hasLower) suggestions.push('Add lowercase letters');
  if (!hasDigit) suggestions.push('Add numbers');
  if (!hasSpecial) suggestions.push('Add special characters');

  // Common patterns penalty
  const commonPatterns = [
    /^[a-zA-Z]+$/,
    /^[0-9]+$/,
    /(.)\1{2,}/,
    /123|abc|qwe|password|admin/i,
  ];

  for (const pattern of commonPatterns) {
    if (pattern.test(password)) {
      score = Math.max(0, score - 1);
      break;
    }
  }

  // Map score to label and color
  const labels = ['Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
  const colors = [
    'bg-red-500',
    'bg-orange-500',
    'bg-yellow-500',
    'bg-green-500',
    'bg-emerald-500',
  ];

  const clampedScore = Math.min(score, 4);

  return {
    score: clampedScore,
    label: labels[clampedScore],
    color: colors[clampedScore],
    suggestions: suggestions.slice(0, 3),
  };
}

export function PasswordStrengthMeter({ password, className }: PasswordStrengthMeterProps) {
  const strength = useMemo(() => calculateStrength(password), [password]);

  if (!password) {
    return null;
  }

  return (
    <div className={cn('space-y-2', className)}>
      {/* Strength bar */}
      <div className="flex gap-1">
        {[0, 1, 2, 3, 4].map((level) => (
          <div
            key={level}
            className={cn(
              'h-1.5 flex-1 rounded-full transition-colors duration-200',
              level <= strength.score ? strength.color : 'bg-muted'
            )}
          />
        ))}
      </div>

      {/* Label and suggestions */}
      <div className="flex items-center justify-between text-xs">
        <span
          className={cn(
            'font-medium',
            strength.score <= 1 && 'text-red-500',
            strength.score === 2 && 'text-yellow-500',
            strength.score >= 3 && 'text-green-500'
          )}
        >
          {strength.label}
        </span>
        {strength.suggestions.length > 0 && (
          <span className="text-muted-foreground">
            {strength.suggestions[0]}
          </span>
        )}
      </div>
    </div>
  );
}

// Password requirements component
interface PasswordRequirementsProps {
  className?: string;
}

export function PasswordRequirements({ className }: PasswordRequirementsProps) {
  const requirements = [
    'At least 8 characters',
    'At least one uppercase letter',
    'At least one lowercase letter',
    'At least one number',
    'At least one special character',
  ];

  return (
    <div className={cn('text-xs text-muted-foreground', className)}>
      <p className="font-medium mb-1">Password requirements:</p>
      <ul className="list-disc list-inside space-y-0.5">
        {requirements.map((req) => (
          <li key={req}>{req}</li>
        ))}
      </ul>
    </div>
  );
}
