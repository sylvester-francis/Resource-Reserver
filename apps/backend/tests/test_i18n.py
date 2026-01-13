"""Tests for the i18n module."""

import pytest

from app.core.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    TRANSLATIONS,
    get_locale_from_header,
    get_translation,
    t,
)


class TestSupportedLocales:
    """Test supported locales configuration."""

    def test_default_locale_is_english(self):
        """Default locale should be English."""
        assert DEFAULT_LOCALE == "en"

    def test_supported_locales_includes_en_es_fr(self):
        """Should support English, Spanish, and French."""
        assert "en" in SUPPORTED_LOCALES
        assert "es" in SUPPORTED_LOCALES
        assert "fr" in SUPPORTED_LOCALES

    def test_all_translations_have_all_locales(self):
        """Each translation key should have all supported locales."""
        for key, translations in TRANSLATIONS.items():
            for locale in SUPPORTED_LOCALES:
                assert locale in translations, (
                    f"Translation key '{key}' missing locale '{locale}'"
                )


class TestGetTranslation:
    """Test get_translation function."""

    def test_get_english_translation(self):
        """Should return English translation."""
        result = get_translation("auth.invalid_credentials", "en")
        assert result == "Invalid username or password"

    def test_get_spanish_translation(self):
        """Should return Spanish translation."""
        result = get_translation("auth.invalid_credentials", "es")
        assert result == "Usuario o contrasena invalidos"

    def test_get_french_translation(self):
        """Should return French translation."""
        result = get_translation("auth.invalid_credentials", "fr")
        assert result == "Nom d'utilisateur ou mot de passe invalide"

    def test_default_to_english_for_unknown_locale(self):
        """Should default to English for unknown locale."""
        result = get_translation("auth.invalid_credentials", "de")
        assert result == "Invalid username or password"

    def test_default_to_english_for_none_locale(self):
        """Should default to English when locale is None."""
        result = get_translation("auth.invalid_credentials", None)
        assert result == "Invalid username or password"

    def test_returns_key_for_unknown_translation(self):
        """Should return the key if translation not found."""
        result = get_translation("unknown.key", "en")
        assert result == "unknown.key"

    def test_resource_translations(self):
        """Test resource-related translations."""
        assert "not found" in get_translation("resource.not_found", "en").lower()
        assert "no encontrado" in get_translation("resource.not_found", "es").lower()
        assert "non trouvee" in get_translation("resource.not_found", "fr").lower()

    def test_reservation_translations(self):
        """Test reservation-related translations."""
        assert "conflict" in get_translation("reservation.conflict", "en").lower()
        assert "conflicto" in get_translation("reservation.conflict", "es").lower()
        assert "conflit" in get_translation("reservation.conflict", "fr").lower()

    def test_rate_limit_translations(self):
        """Test rate limit translations."""
        result_en = get_translation("rate_limit.exceeded", "en")
        result_es = get_translation("rate_limit.exceeded", "es")
        result_fr = get_translation("rate_limit.exceeded", "fr")

        assert "rate limit" in result_en.lower()
        assert "limite" in result_es.lower()
        assert "limite" in result_fr.lower()


class TestShorthandT:
    """Test t() shorthand function."""

    def test_t_is_alias_for_get_translation(self):
        """t() should be an alias for get_translation()."""
        assert t("auth.invalid_credentials", "en") == get_translation(
            "auth.invalid_credentials", "en"
        )

    def test_t_with_spanish(self):
        """t() should work with Spanish."""
        result = t("user.created", "es")
        assert "exitosamente" in result


class TestGetLocaleFromHeader:
    """Test Accept-Language header parsing."""

    def test_parse_simple_locale(self):
        """Should parse simple locale."""
        result = get_locale_from_header("en")
        assert result == "en"

    def test_parse_locale_with_region(self):
        """Should parse locale with region and return base language."""
        result = get_locale_from_header("en-US")
        assert result == "en"

    def test_parse_locale_with_quality(self):
        """Should parse locale with quality factor."""
        result = get_locale_from_header("en;q=0.9")
        assert result == "en"

    def test_parse_multiple_locales(self):
        """Should return first supported locale from list."""
        result = get_locale_from_header("de,fr;q=0.9,en;q=0.8")
        assert result == "fr"

    def test_return_default_for_unsupported(self):
        """Should return default locale for unsupported languages."""
        result = get_locale_from_header("de,it,ja")
        assert result == DEFAULT_LOCALE

    def test_return_default_for_empty_header(self):
        """Should return default locale for empty header."""
        result = get_locale_from_header("")
        assert result == DEFAULT_LOCALE

    def test_return_default_for_none(self):
        """Should return default locale for None."""
        result = get_locale_from_header(None)
        assert result == DEFAULT_LOCALE

    def test_parse_complex_header(self):
        """Should parse complex Accept-Language header."""
        header = "es-MX,es;q=0.9,en-US;q=0.8,en;q=0.7,fr;q=0.6"
        result = get_locale_from_header(header)
        assert result == "es"

    def test_quality_ordering(self):
        """Should respect quality ordering."""
        header = "en;q=0.5,es;q=0.9,fr;q=0.7"
        result = get_locale_from_header(header)
        assert result == "es"


class TestTranslationCoverage:
    """Test translation coverage for important keys."""

    @pytest.mark.parametrize(
        "key",
        [
            "auth.invalid_credentials",
            "auth.token_expired",
            "auth.unauthorized",
            "resource.not_found",
            "resource.created",
            "reservation.not_found",
            "reservation.created",
            "reservation.conflict",
            "user.not_found",
            "user.created",
            "rate_limit.exceeded",
            "error.internal",
        ],
    )
    def test_critical_keys_exist(self, key):
        """Critical translation keys should exist."""
        assert key in TRANSLATIONS

    @pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
    def test_all_locales_have_auth_messages(self, locale):
        """All locales should have auth messages."""
        assert (
            get_translation("auth.invalid_credentials", locale)
            != "auth.invalid_credentials"
        )
        assert get_translation("auth.unauthorized", locale) != "auth.unauthorized"

    @pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
    def test_all_locales_have_error_messages(self, locale):
        """All locales should have error messages."""
        assert get_translation("error.internal", locale) != "error.internal"
        assert get_translation("error.not_found", locale) != "error.not_found"
