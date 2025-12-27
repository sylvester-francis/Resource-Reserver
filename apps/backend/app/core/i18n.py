"""Internationalization (i18n) module for API responses.

This module provides multilingual support for error messages and API responses
in the Resource Reserver application. It implements a simple yet flexible
translation system supporting multiple locales with fallback to English.

Features:
    - Support for multiple locales (English, Spanish, French)
    - Translation key-based message retrieval
    - Placeholder substitution in translated messages
    - Accept-Language header parsing for automatic locale detection
    - ASGI middleware for request-level locale extraction

Example usage:
    Basic translation::

        from app.core.i18n import t, get_translation

        # Using the shorthand function
        message = t("auth.invalid_credentials", locale="es")
        # Returns: "Usuario o contrasena invalidos"

        # With placeholder substitution
        message = t("user.greeting", locale="en", name="John")

    Middleware integration::

        from fastapi import FastAPI
        from app.core.i18n import TranslationMiddleware

        app = FastAPI()
        app.add_middleware(TranslationMiddleware)

    Accessing locale in routes::

        from fastapi import Request

        @app.get("/example")
        async def example(request: Request):
            locale = request.state.locale
            return {"message": t("success.operation", locale)}

Author:
    Resource Reserver Development Team
"""

from typing import Any

# Supported locales for the application.
SUPPORTED_LOCALES: list[str] = ["en", "es", "fr"]

# The default locale used when no valid locale is specified or detected.
DEFAULT_LOCALE: str = "en"

# Translation dictionaries organized by translation key.
# Structure:
# {
#     "category.key": {
#         "en": "English message",
#         "es": "Spanish message",
#         "fr": "French message",
#     },
#     ...
# }
TRANSLATIONS: dict[str, dict[str, str]] = {
    # Authentication messages
    "auth.invalid_credentials": {
        "en": "Invalid username or password",
        "es": "Usuario o contrasena invalidos",
        "fr": "Nom d'utilisateur ou mot de passe invalide",
    },
    "auth.token_expired": {
        "en": "Token has expired",
        "es": "El token ha expirado",
        "fr": "Le jeton a expire",
    },
    "auth.unauthorized": {
        "en": "Not authorized to access this resource",
        "es": "No autorizado para acceder a este recurso",
        "fr": "Non autorise a acceder a cette ressource",
    },
    "auth.forbidden": {
        "en": "Access forbidden",
        "es": "Acceso prohibido",
        "fr": "Acces interdit",
    },
    # Resource messages
    "resource.not_found": {
        "en": "Resource not found",
        "es": "Recurso no encontrado",
        "fr": "Ressource non trouvee",
    },
    "resource.created": {
        "en": "Resource created successfully",
        "es": "Recurso creado exitosamente",
        "fr": "Ressource creee avec succes",
    },
    "resource.updated": {
        "en": "Resource updated successfully",
        "es": "Recurso actualizado exitosamente",
        "fr": "Ressource mise a jour avec succes",
    },
    "resource.deleted": {
        "en": "Resource deleted successfully",
        "es": "Recurso eliminado exitosamente",
        "fr": "Ressource supprimee avec succes",
    },
    "resource.in_use": {
        "en": "Resource is currently in use",
        "es": "El recurso esta actualmente en uso",
        "fr": "La ressource est actuellement utilisee",
    },
    # Reservation messages
    "reservation.not_found": {
        "en": "Reservation not found",
        "es": "Reservacion no encontrada",
        "fr": "Reservation non trouvee",
    },
    "reservation.created": {
        "en": "Reservation created successfully",
        "es": "Reservacion creada exitosamente",
        "fr": "Reservation creee avec succes",
    },
    "reservation.updated": {
        "en": "Reservation updated successfully",
        "es": "Reservacion actualizada exitosamente",
        "fr": "Reservation mise a jour avec succes",
    },
    "reservation.cancelled": {
        "en": "Reservation cancelled successfully",
        "es": "Reservacion cancelada exitosamente",
        "fr": "Reservation annulee avec succes",
    },
    "reservation.conflict": {
        "en": "Time slot conflicts with existing reservation",
        "es": "El horario tiene conflicto con una reservacion existente",
        "fr": "Le creneau entre en conflit avec une reservation existante",
    },
    "reservation.past_time": {
        "en": "Cannot create reservation in the past",
        "es": "No se puede crear una reservacion en el pasado",
        "fr": "Impossible de creer une reservation dans le passe",
    },
    "reservation.outside_hours": {
        "en": "Reservation is outside business hours",
        "es": "La reservacion esta fuera del horario de atencion",
        "fr": "La reservation est en dehors des heures d'ouverture",
    },
    "reservation.too_long": {
        "en": "Reservation exceeds maximum duration",
        "es": "La reservacion excede la duracion maxima",
        "fr": "La reservation depasse la duree maximale",
    },
    "reservation.too_short": {
        "en": "Reservation is below minimum duration",
        "es": "La reservacion es menor a la duracion minima",
        "fr": "La reservation est inferieure a la duree minimale",
    },
    # User messages
    "user.not_found": {
        "en": "User not found",
        "es": "Usuario no encontrado",
        "fr": "Utilisateur non trouve",
    },
    "user.created": {
        "en": "User created successfully",
        "es": "Usuario creado exitosamente",
        "fr": "Utilisateur cree avec succes",
    },
    "user.updated": {
        "en": "User updated successfully",
        "es": "Usuario actualizado exitosamente",
        "fr": "Utilisateur mis a jour avec succes",
    },
    "user.deleted": {
        "en": "User deleted successfully",
        "es": "Usuario eliminado exitosamente",
        "fr": "Utilisateur supprime avec succes",
    },
    "user.already_exists": {
        "en": "Username already exists",
        "es": "El nombre de usuario ya existe",
        "fr": "Le nom d'utilisateur existe deja",
    },
    # Role messages
    "role.not_found": {
        "en": "Role not found",
        "es": "Rol no encontrado",
        "fr": "Role non trouve",
    },
    "role.assigned": {
        "en": "Role assigned successfully",
        "es": "Rol asignado exitosamente",
        "fr": "Role attribue avec succes",
    },
    "role.removed": {
        "en": "Role removed successfully",
        "es": "Rol removido exitosamente",
        "fr": "Role retire avec succes",
    },
    # Validation messages
    "validation.required": {
        "en": "This field is required",
        "es": "Este campo es obligatorio",
        "fr": "Ce champ est obligatoire",
    },
    "validation.invalid_format": {
        "en": "Invalid format",
        "es": "Formato invalido",
        "fr": "Format invalide",
    },
    "validation.invalid_date": {
        "en": "Invalid date format",
        "es": "Formato de fecha invalido",
        "fr": "Format de date invalide",
    },
    "validation.invalid_time": {
        "en": "Invalid time format",
        "es": "Formato de hora invalido",
        "fr": "Format d'heure invalide",
    },
    # Rate limiting messages
    "rate_limit.exceeded": {
        "en": "Rate limit exceeded. Please try again later.",
        "es": "Limite de solicitudes excedido. Intente de nuevo mas tarde.",
        "fr": "Limite de requetes depassee. Veuillez reessayer plus tard.",
    },
    "quota.exceeded": {
        "en": "Daily quota exceeded",
        "es": "Cuota diaria excedida",
        "fr": "Quota journalier depasse",
    },
    # General messages
    "error.internal": {
        "en": "Internal server error",
        "es": "Error interno del servidor",
        "fr": "Erreur interne du serveur",
    },
    "error.not_found": {
        "en": "Resource not found",
        "es": "Recurso no encontrado",
        "fr": "Ressource non trouvee",
    },
    "error.bad_request": {
        "en": "Bad request",
        "es": "Solicitud invalida",
        "fr": "Requete invalide",
    },
    "success.operation": {
        "en": "Operation completed successfully",
        "es": "Operacion completada exitosamente",
        "fr": "Operation terminee avec succes",
    },
}


def get_translation(key: str, locale: str | None = None, **kwargs: str) -> str:
    """Retrieve a translated message by its translation key.

    Looks up the translation for the given key in the specified locale.
    If the locale is not supported or not provided, falls back to the
    default locale (English). If the key is not found, returns the key
    itself as a fallback.

    Args:
        key: The translation key in dot notation (e.g., 'auth.invalid_credentials').
            Keys follow the pattern 'category.message_name'.
        locale: The locale code to use for translation (e.g., 'en', 'es', 'fr').
            If None or not in SUPPORTED_LOCALES, defaults to DEFAULT_LOCALE.
        **kwargs: Placeholder values for string formatting. These are substituted
            into the translated message using Python's str.format() method.

    Returns:
        The translated message string. If the key is not found in TRANSLATIONS,
        returns the key unchanged. If placeholder substitution fails due to
        missing keys, returns the unformatted translated message.

    Example:
        >>> get_translation("auth.invalid_credentials", "es")
        'Usuario o contrasena invalidos'
        >>> get_translation("user.greeting", "en", name="Alice")
        'Hello, Alice!'
        >>> get_translation("nonexistent.key")
        'nonexistent.key'
    """
    if locale is None or locale not in SUPPORTED_LOCALES:
        locale = DEFAULT_LOCALE

    translations = TRANSLATIONS.get(key)
    if not translations:
        return key

    message = translations.get(locale, translations.get(DEFAULT_LOCALE, key))

    # Apply any placeholder substitutions if keyword arguments are provided
    if kwargs:
        try:
            message = message.format(**kwargs)
        except KeyError:
            # If placeholder substitution fails, return the unformatted message
            pass

    return message


def t(key: str, locale: str | None = None, **kwargs: str) -> str:
    """Shorthand alias for get_translation function.

    Provides a convenient, concise way to retrieve translated messages.
    This is the recommended function for use throughout the application
    due to its brevity.

    Args:
        key: The translation key in dot notation (e.g., 'auth.invalid_credentials').
        locale: The locale code to use for translation. Defaults to None,
            which falls back to DEFAULT_LOCALE.
        **kwargs: Placeholder values for string formatting in the translated message.

    Returns:
        The translated message string, or the key if not found.

    Example:
        >>> t("resource.created", "fr")
        'Ressource creee avec succes'
        >>> t("validation.required")
        'This field is required'
    """
    return get_translation(key, locale, **kwargs)


def get_locale_from_header(accept_language: str | None) -> str:
    """Parse the Accept-Language HTTP header and determine the best matching locale.

    Parses the Accept-Language header according to RFC 7231, extracting
    language tags and their quality values, then returns the highest-priority
    supported locale.

    The function handles:
        - Multiple language preferences separated by commas
        - Quality values (q=) for preference weighting
        - Language tags with region codes (e.g., 'en-US' extracts 'en')
        - Case-insensitive language codes

    Args:
        accept_language: The value of the Accept-Language HTTP header.
            Example formats:
                - "en-US,en;q=0.9,es;q=0.8"
                - "fr-FR,fr;q=0.9,en;q=0.5"
                - "es"
            If None or empty, returns DEFAULT_LOCALE.

    Returns:
        The best matching locale code from SUPPORTED_LOCALES, or DEFAULT_LOCALE
        if no supported locale is found in the header.

    Example:
        >>> get_locale_from_header("en-US,en;q=0.9,es;q=0.8")
        'en'
        >>> get_locale_from_header("fr-FR,es;q=0.9")
        'fr'
        >>> get_locale_from_header("de,ja;q=0.9")
        'en'
        >>> get_locale_from_header(None)
        'en'
    """
    if not accept_language:
        return DEFAULT_LOCALE

    # Parse Accept-Language header (e.g., "en-US,en;q=0.9,es;q=0.8")
    languages: list[tuple[str, float]] = []
    for part in accept_language.split(","):
        lang_parts = part.strip().split(";")
        # Extract base language code, ignoring region (e.g., 'en-US' -> 'en')
        lang = lang_parts[0].split("-")[0].lower()
        quality = 1.0
        # Parse quality value if present
        if len(lang_parts) > 1 and lang_parts[1].startswith("q="):
            try:
                quality = float(lang_parts[1][2:])
            except ValueError:
                quality = 0.0
        languages.append((lang, quality))

    # Sort by quality value in descending order (highest preference first)
    languages.sort(key=lambda x: x[1], reverse=True)

    # Return the first language that is in the supported locales list
    for lang, _ in languages:
        if lang in SUPPORTED_LOCALES:
            return lang

    return DEFAULT_LOCALE


class TranslationMiddleware:
    """ASGI middleware for extracting locale from HTTP request headers.

    This middleware parses the Accept-Language header from incoming HTTP
    requests and stores the detected locale in the request scope state.
    This allows route handlers to access the user's preferred language
    without manually parsing headers.

    The middleware is compatible with FastAPI, Starlette, and other
    ASGI-compliant frameworks.

    Attributes:
        app: The ASGI application to wrap. This is the next middleware
            or the actual application in the middleware chain.

    Example:
        Adding middleware to a FastAPI application::

            from fastapi import FastAPI, Request
            from app.core.i18n import TranslationMiddleware, t

            app = FastAPI()
            app.add_middleware(TranslationMiddleware)

            @app.get("/greeting")
            async def greeting(request: Request):
                locale = getattr(request.state, 'locale', 'en')
                return {"message": t("success.operation", locale)}

        Accessing locale via dependency injection::

            from fastapi import Request, Depends

            def get_locale(request: Request) -> str:
                return getattr(request.state, 'locale', 'en')

            @app.get("/example")
            async def example(locale: str = Depends(get_locale)):
                return {"message": t("success.operation", locale)}
    """

    def __init__(self, app: Any) -> None:
        """Initialize the TranslationMiddleware with an ASGI application.

        Args:
            app: The ASGI application to wrap. This should be the next
                middleware in the chain or the final application.
        """
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Any,
        send: Any,
    ) -> None:
        """Process an incoming ASGI request and extract the locale.

        For HTTP requests, this method extracts the Accept-Language header,
        parses it to determine the preferred locale, and stores the result
        in scope["state"]["locale"]. Non-HTTP requests (e.g., WebSocket,
        lifespan) are passed through without modification.

        Args:
            scope: The ASGI connection scope dictionary containing request
                metadata including headers, path, and connection type.
            receive: An awaitable callable to receive ASGI event messages
                from the client.
            send: An awaitable callable to send ASGI event messages to
                the client.

        Returns:
            None. This method delegates to the wrapped application after
            optionally modifying the scope.
        """
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            accept_language = headers.get(b"accept-language", b"").decode("utf-8")
            locale = get_locale_from_header(accept_language)
            # Ensure state dict exists in scope and add locale
            scope["state"] = scope.get("state", {})
            scope["state"]["locale"] = locale

        await self.app(scope, receive, send)
