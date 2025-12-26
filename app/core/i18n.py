"""
Internationalization (i18n) module for API responses.

Provides multilingual support for error messages and API responses.
"""

# Supported locales
SUPPORTED_LOCALES = ["en", "es", "fr"]
DEFAULT_LOCALE = "en"

# Translation dictionaries
TRANSLATIONS: dict[str, dict[str, str]] = {
    # Authentication
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
    # Resources
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
    # Reservations
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
    # Users
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
    # Roles
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
    # Validation
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
    # Rate Limiting
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
    # General
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
    """
    Get a translated message by key.

    Args:
        key: The translation key (e.g., 'auth.invalid_credentials')
        locale: The locale to use (defaults to 'en')
        **kwargs: Placeholder values for string formatting

    Returns:
        The translated message or the key if not found
    """
    if locale is None or locale not in SUPPORTED_LOCALES:
        locale = DEFAULT_LOCALE

    translations = TRANSLATIONS.get(key)
    if not translations:
        return key

    message = translations.get(locale, translations.get(DEFAULT_LOCALE, key))

    # Apply any placeholder substitutions
    if kwargs:
        try:
            message = message.format(**kwargs)
        except KeyError:
            pass

    return message


def t(key: str, locale: str | None = None, **kwargs: str) -> str:
    """Shorthand alias for get_translation."""
    return get_translation(key, locale, **kwargs)


def get_locale_from_header(accept_language: str | None) -> str:
    """
    Parse Accept-Language header and return the best matching locale.

    Args:
        accept_language: The Accept-Language header value

    Returns:
        The best matching locale code
    """
    if not accept_language:
        return DEFAULT_LOCALE

    # Parse Accept-Language header (e.g., "en-US,en;q=0.9,es;q=0.8")
    languages = []
    for part in accept_language.split(","):
        lang_parts = part.strip().split(";")
        lang = lang_parts[0].split("-")[0].lower()
        quality = 1.0
        if len(lang_parts) > 1 and lang_parts[1].startswith("q="):
            try:
                quality = float(lang_parts[1][2:])
            except ValueError:
                quality = 0.0
        languages.append((lang, quality))

    # Sort by quality (descending)
    languages.sort(key=lambda x: x[1], reverse=True)

    # Return the first supported locale
    for lang, _ in languages:
        if lang in SUPPORTED_LOCALES:
            return lang

    return DEFAULT_LOCALE


class TranslationMiddleware:
    """
    Middleware to extract locale from request headers.

    Usage:
        from fastapi import Request, Depends

        def get_locale(request: Request) -> str:
            return request.state.locale if hasattr(request.state, 'locale') else 'en'

        @app.get("/example")
        async def example(locale: str = Depends(get_locale)):
            return {"message": t("success.operation", locale)}
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            accept_language = headers.get(b"accept-language", b"").decode("utf-8")
            locale = get_locale_from_header(accept_language)
            scope["state"] = scope.get("state", {})
            scope["state"]["locale"] = locale

        await self.app(scope, receive, send)
