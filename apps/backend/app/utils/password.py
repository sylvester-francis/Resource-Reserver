"""Password policy and validation utilities."""

import re
from dataclasses import dataclass


@dataclass
class PasswordStrength:
    """Result of password strength calculation."""

    score: int  # 0-4 (weak to very strong)
    label: str  # "weak", "fair", "good", "strong", "very_strong"
    suggestions: list[str]


class PasswordPolicy:
    """Password policy configuration and validation."""

    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\\;'/`~]"

    # Account lockout settings
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15

    @classmethod
    def validate(cls, password: str, username: str = "") -> tuple[bool, list[str]]:
        """Validate password against policy.

        Args:
            password: The password to validate
            username: Optional username to check password doesn't contain it

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters")

        if cls.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("Password must contain an uppercase letter")

        if cls.REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append("Password must contain a lowercase letter")

        if cls.REQUIRE_DIGIT and not re.search(r"\d", password):
            errors.append("Password must contain a number")

        if cls.REQUIRE_SPECIAL and not re.search(cls.SPECIAL_CHARS, password):
            errors.append("Password must contain a special character")

        if username and len(username) >= 3 and username.lower() in password.lower():
            errors.append("Password cannot contain your username")

        return len(errors) == 0, errors

    @classmethod
    def calculate_strength(cls, password: str) -> PasswordStrength:
        """Calculate password strength score.

        Args:
            password: The password to evaluate

        Returns:
            PasswordStrength with score, label, and suggestions
        """
        score = 0
        suggestions = []

        # Length scoring
        if len(password) >= 8:
            score += 1
        else:
            suggestions.append("Use at least 8 characters")

        if len(password) >= 12:
            score += 1
        elif len(password) >= 8:
            suggestions.append("Consider using 12+ characters for extra security")

        # Character variety scoring
        has_upper = bool(re.search(r"[A-Z]", password))
        has_lower = bool(re.search(r"[a-z]", password))
        has_digit = bool(re.search(r"\d", password))
        has_special = bool(re.search(cls.SPECIAL_CHARS, password))

        variety_count = sum([has_upper, has_lower, has_digit, has_special])

        if variety_count >= 3:
            score += 1
        if variety_count >= 4:
            score += 1

        if not has_upper:
            suggestions.append("Add uppercase letters")
        if not has_lower:
            suggestions.append("Add lowercase letters")
        if not has_digit:
            suggestions.append("Add numbers")
        if not has_special:
            suggestions.append("Add special characters")

        # Common patterns penalty
        common_patterns = [
            r"^[a-zA-Z]+$",  # Only letters
            r"^[0-9]+$",  # Only numbers
            r"(.)\1{2,}",  # Same character 3+ times
            r"123|abc|qwe|password|admin",  # Common sequences
        ]

        for pattern in common_patterns:
            if re.search(pattern, password.lower()):
                score = max(0, score - 1)
                break

        # Map score to label
        labels = ["weak", "fair", "good", "strong", "very_strong"]
        label = labels[min(score, 4)]

        return PasswordStrength(score=score, label=label, suggestions=suggestions[:3])

    @classmethod
    def get_policy_requirements(cls) -> list[str]:
        """Get list of password policy requirements for display."""
        requirements = [f"At least {cls.MIN_LENGTH} characters"]

        if cls.REQUIRE_UPPERCASE:
            requirements.append("At least one uppercase letter")
        if cls.REQUIRE_LOWERCASE:
            requirements.append("At least one lowercase letter")
        if cls.REQUIRE_DIGIT:
            requirements.append("At least one number")
        if cls.REQUIRE_SPECIAL:
            requirements.append("At least one special character")

        return requirements
