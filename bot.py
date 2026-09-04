import asyncio
import json
import os
import re
import logging
import typing
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cleaner-bot")

TOKEN = os.environ.get("DISCORD_TOKEN")
CONFIG_PATH = os.environ.get("CONFIG_PATH", "/data/config.json")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL_SECONDS", "20"))
WARNING_COOLDOWN_SECONDS = int(os.environ.get("WARNING_COOLDOWN_SECONDS", "600"))  # 10 minut

DURATION_RE = re.compile(r"^(\d+)([smh])$", re.IGNORECASE)
UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600}

DEFAULT_LANG = "en"

# --- Tłumaczenia / Translations ---

TRANSLATIONS = {
    "en": {
        "bad_duration": "Invalid time format. Use e.g. 30s, 5m, 1h.",
        "bad_count_format": "Message count must be a whole number.",
        "bad_count": "Message count must be 0 or greater.",
        "confirm_time_only": "Messages in this channel will be deleted after {duration}.",
        "confirm_count_only": "Messages in this channel will be deleted once there are more than "
                               "{count} messages.",
        "confirm_both": "Messages in this channel will be deleted after {duration}, or once there "
                         "are more than {count} messages.",
        "confirm_only_new": " Only messages sent after this was set up are affected — earlier "
                             "messages are left alone.",
        "warning_generic": "⚠️ Cleanup starts in {minutes} minutes — including old messages. "
                            "Use `{mention} unset` before then to cancel.",
        "warning_new_hint": "Tip: add `new` at the end of the `set` command (e.g. `{mention} set ... new`) "
                             "if you'd rather only affect messages sent from now on, leaving existing "
                             "messages untouched.",
        "set_confirmation_disabled": "Both time and count are set to 0, so cleanup has been "
                                      "disabled for this channel.",
        "unset_confirmation": "Cleanup has been disabled for this channel.",
        "status_none": "Cleanup is not configured for this channel.",
        "status_info": "Time: {time}, max messages: {count}.",
        "status_cooldown": " Still in warm-up — cleanup starts <t:{timestamp}:R>.",
        "status_only_new": "Only messages sent after cleanup was set up are affected.",
        "admin_role_added": "Role **{name}** can now use bot commands.",
        "admin_user_added": "User **{name}** can now use bot commands.",
        "admin_role_removed": "Role **{name}** lost access to bot commands.",
        "admin_user_removed": "User **{name}** lost access to bot commands.",
        "adminlist_title": "**Access to commands (besides Manage Messages / Administrator):**",
        "adminlist_roles": "Roles: {value}",
        "adminlist_users": "Users: {value}",
        "adminlist_none": "none",
        "vip_role_added": "Messages from role **{name}** will no longer be deleted by cleanup.",
        "vip_user_added": "Messages from **{name}** will no longer be deleted by cleanup.",
        "vip_role_removed": "Role **{name}** no longer skips cleanup.",
        "vip_user_removed": "**{name}** no longer skips cleanup.",
        "viplist_title": "**Roles/users whose messages are never deleted by cleanup:**",
        "lang_admin_only": "Only a server Administrator can change the bot's language.",
        "lang_invalid": "Invalid language. Use `EN` or `PL`.",
        "lang_set": "Bot language for this server set to **{lang_name}**.",
        "lang_name_en": "English",
        "lang_name_pl": "Polish",
        "help_title": "**Bot commands for cleaning channels:**",
        "help_set": "`{mention} set <time> <count>` — sets up cleanup for this channel.",
        "help_set_example": "  e.g. `{mention} set 5m 10` — deletes messages older than 5 minutes, "
                             "and once there are more than 10, deletes starting from the oldest.",
        "help_set_units": "  allowed time units: `s` (seconds), `m` (minutes), `h` (hours), "
                           "e.g. `30s`, `1m`, `1h`.",
        "help_set_zero": "  use `0` for either value to ignore that rule (e.g. `{mention} set 0 10` "
                          "only limits by count); `{mention} set 0 0` disables cleanup, same as `{mention} unset`.",
        "help_set_new": "  add `new` at the end (e.g. `{mention} set 24h 0 new`) to only apply cleanup "
                         "to messages sent after this command — older messages are left alone entirely.",
        "help_set_warning": "  cleanup doesn't start right away — the bot posts a warning and waits "
                             "{minutes} minutes first, so there's time to `{mention} unset` if you "
                             "change your mind. This also removes old messages (older than 14 days), "
                             "not just recent ones.",
        "help_unset": "`{mention} unset` — disables cleanup for this channel.",
        "help_status": "`{mention} status` — shows the current configuration for this channel.",
        "help_admin": "`{mention} admin @Role` or `{mention} admin @User` — grants access to commands "
                      "(server Administrator only).",
        "help_admin_example": "  e.g. `{mention} admin @Moderators`",
        "help_unadmin": "`{mention} unadmin @Role` or `{mention} unadmin @User` — revokes access "
                        "(server Administrator only).",
        "help_adminlist": "`{mention} adminlist` — shows roles/users with access to commands "
                          "(server Administrator only).",
        "help_vip": "`{mention} vip @Role` or `{mention} vip @User` — their messages are never "
                    "deleted by cleanup (server Administrator only).",
        "help_vip_example": "  e.g. `{mention} vip @Moderators`",
        "help_unvip": "`{mention} unvip @Role` or `{mention} unvip @User` — removes that exemption "
                      "(server Administrator only).",
        "help_viplist": "`{mention} viplist` — shows roles/users exempt from cleanup "
                        "(server Administrator only).",
        "help_lang": "`{mention} lang EN` or `{mention} lang PL` — sets the bot's language "
                    "for this server (server Administrator only).",
        "help_help": "`{mention} help` — shows this message.",
    },
    "pl": {
        "bad_duration": "Zły format czasu. Użyj np. 30s, 5m, 1h.",
        "bad_count_format": "Liczba wiadomości musi być liczbą całkowitą.",
        "bad_count": "Liczba wiadomości musi być większa lub równa 0.",
        "confirm_time_only": "Wiadomości na tym kanale będą usuwane po {duration}.",
        "confirm_count_only": "Wiadomości na tym kanale będą usuwane, gdy będzie ich więcej niż {count}.",
        "confirm_both": "Wiadomości na tym kanale będą usuwane po {duration}, lub gdy będzie ich "
                         "więcej niż {count}.",
        "confirm_only_new": " Dotyczy tylko wiadomości wysłanych po tym ustawieniu — wcześniejsze "
                             "zostają nietknięte.",
        "warning_generic": "⚠️ Czyszczenie zacznie działać za {minutes} minut — łącznie ze starymi "
                            "wiadomościami. Użyj `{mention} unset` wcześniej, żeby to anulować.",
        "warning_new_hint": "Wskazówka: dopisz `new` na końcu komendy `set` (np. `{mention} set ... new`), "
                             "jeśli wolisz, żeby dotyczyło to tylko wiadomości wysłanych od teraz, "
                             "zostawiając istniejące bez zmian.",
        "set_confirmation_disabled": "Czas i liczba wiadomości ustawione na 0, więc czyszczenie "
                                      "na tym kanale zostało wyłączone.",
        "unset_confirmation": "Czyszczenie na tym kanale zostało wyłączone.",
        "status_none": "Na tym kanale czyszczenie nie jest skonfigurowane.",
        "status_info": "Czas: {time}, maks. liczba wiadomości: {count}.",
        "status_cooldown": " Wciąż trwa rozgrzewka — czyszczenie zacznie się <t:{timestamp}:R>.",
        "status_only_new": "Dotyczy tylko wiadomości wysłanych po skonfigurowaniu czyszczenia.",
        "admin_role_added": "Rola **{name}** może teraz wydawać komendy botowi.",
        "admin_user_added": "Użytkownik **{name}** może teraz wydawać komendy botowi.",
        "admin_role_removed": "Rola **{name}** straciła dostęp do komend bota.",
        "admin_user_removed": "Użytkownik **{name}** stracił dostęp do komend bota.",
        "adminlist_title": "**Dostęp do komend (oprócz Manage Messages / Administrator):**",
        "adminlist_roles": "Role: {value}",
        "adminlist_users": "Userzy: {value}",
        "adminlist_none": "brak",
        "vip_role_added": "Wiadomości od roli **{name}** nie będą już usuwane przy czyszczeniu.",
        "vip_user_added": "Wiadomości od **{name}** nie będą już usuwane przy czyszczeniu.",
        "vip_role_removed": "Rola **{name}** nie jest już pomijana przy czyszczeniu.",
        "vip_user_removed": "**{name}** nie jest już pomijany/a przy czyszczeniu.",
        "viplist_title": "**Role/userzy, których wiadomości nigdy nie są usuwane przy czyszczeniu:**",
        "lang_admin_only": "Tylko Administrator serwera może zmienić język bota.",
        "lang_invalid": "Zły język. Użyj `EN` lub `PL`.",
        "lang_set": "Język bota na tym serwerze ustawiono na **{lang_name}**.",
        "lang_name_en": "angielski",
        "lang_name_pl": "polski",
        "help_title": "**Komendy bota do czyszczenia kanałów:**",
        "help_set": "`{mention} set <czas> <liczba>` — ustawia czyszczenie kanału.",
        "help_set_example": "  np. `{mention} set 5m 10` — usuwa wiadomości starsze niż 5 minut, "
                             "a gdy jest ich więcej niż 10, kasuje od najstarszej.",
        "help_set_units": "  dozwolone jednostki czasu: `s` (sekundy), `m` (minuty), `h` (godziny), "
                           "np. `30s`, `1m`, `1h`.",
        "help_set_zero": "  wpisz `0` w dowolnej wartości, żeby pominąć to kryterium (np. `{mention} set 0 10` "
                          "limituje tylko liczbą); `{mention} set 0 0` wyłącza czyszczenie, tak jak `{mention} unset`.",
        "help_set_new": "  dopisz `new` na końcu (np. `{mention} set 24h 0 new`), żeby czyszczenie dotyczyło "
                         "tylko wiadomości wysłanych po tej komendzie — starsze zostają nietknięte.",
        "help_set_warning": "  czyszczenie nie zaczyna się od razu — bot wysyła ostrzeżenie i czeka "
                             "{minutes} minut, żeby można było zrobić `{mention} unset`, jeśli ktoś "
                             "się rozmyśli. Kasowane są też stare wiadomości (starsze niż 14 dni), "
                             "nie tylko te niedawne.",
        "help_unset": "`{mention} unset` — wyłącza czyszczenie na tym kanale.",
        "help_status": "`{mention} status` — pokazuje aktualną konfigurację tego kanału.",
        "help_admin": "`{mention} admin @Rola` lub `{mention} admin @Uzytkownik` — nadaje dostęp do komend "
                      "(tylko Administrator serwera).",
        "help_admin_example": "  np. `{mention} admin @Moderatorzy`",
        "help_unadmin": "`{mention} unadmin @Rola` lub `{mention} unadmin @Uzytkownik` — odbiera dostęp "
                        "(tylko Administrator serwera).",
        "help_adminlist": "`{mention} adminlist` — pokazuje role/userów z dostępem do komend "
                          "(tylko Administrator serwera).",
        "help_vip": "`{mention} vip @Rola` lub `{mention} vip @Uzytkownik` — ich wiadomości nigdy "
                    "nie są usuwane przy czyszczeniu (tylko Administrator serwera).",
        "help_vip_example": "  np. `{mention} vip @Moderatorzy`",
        "help_unvip": "`{mention} unvip @Rola` lub `{mention} unvip @Uzytkownik` — cofa to wykluczenie "
                      "(tylko Administrator serwera).",
        "help_viplist": "`{mention} viplist` — pokazuje role/userów wykluczonych z czyszczenia "
                        "(tylko Administrator serwera).",
        "help_lang": "`{mention} lang EN` lub `{mention} lang PL` — ustawia język bota "
                    "na tym serwerze (tylko Administrator serwera).",
        "help_help": "`{mention} help` — pokazuje tę wiadomość.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Zwraca przetłumaczony tekst dla danego języka (domyślnie EN, jeśli brak klucza)."""
    table = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG])
    template = table.get(key, TRANSLATIONS[DEFAULT_LANG].get(key, key))
    return template.format(**kwargs)


def parse_duration(value: str, lang: str = DEFAULT_LANG) -> int:
    match = DURATION_RE.match(value.strip())
    if not match:
        raise ValueError(t(lang, "bad_duration"))
    amount, unit = match.groups()
    return int(amount) * UNIT_SECONDS[unit.lower()]


def format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}h{minutes}m{secs}s"


class ConfigStore:
    """Magazyn konfiguracji (kanały do czyszczenia + role/userzy z dostępem + język) w pliku JSON."""

    def __init__(self, path: str):
        self.path = path
        self._data: dict = {"channels": {}, "guild_admins": {}, "guild_lang": {}, "guild_vips": {}}
        self._lock = asyncio.Lock()
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Kompatybilność ze starszym, płaskim formatem (sam słownik kanałów).
            if "channels" not in raw and "guild_admins" not in raw:
                raw = {"channels": raw, "guild_admins": {}}
            raw.setdefault("channels", {})
            raw.setdefault("guild_admins", {})
            raw.setdefault("guild_lang", {})
            raw.setdefault("guild_vips", {})
            self._data = raw

    async def save(self):
        async with self._lock:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp_path = f"{self.path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp_path, self.path)

    # --- kanały ---

    def set_channel(self, channel_id: int, seconds: int, count: int, only_new_after: datetime | None = None):
        self._data["channels"][str(channel_id)] = {
            "seconds": seconds,
            "count": count,
            "pinned_message_id": None,
            "warning_message_id": None,
            "activate_at": None,
            "only_new_after": only_new_after.isoformat() if only_new_after else None,
        }

    def set_pinned_message(self, channel_id: int, message_id: int):
        cfg = self._data["channels"].get(str(channel_id))
        if cfg is not None:
            cfg["pinned_message_id"] = message_id

    def set_warning(self, channel_id: int, message_id: int, activate_at: datetime):
        cfg = self._data["channels"].get(str(channel_id))
        if cfg is not None:
            cfg["warning_message_id"] = message_id
            cfg["activate_at"] = activate_at.isoformat()

    def clear_warning(self, channel_id: int):
        cfg = self._data["channels"].get(str(channel_id))
        if cfg is not None:
            cfg["warning_message_id"] = None

    def remove_channel(self, channel_id: int):
        self._data["channels"].pop(str(channel_id), None)

    def get_channel(self, channel_id: int):
        return self._data["channels"].get(str(channel_id))

    def all_channels(self):
        return dict(self._data["channels"])

    # --- role/userzy z dostępem do komend na danym serwerze ---

    def _guild_admins(self, guild_id: int) -> dict:
        return self._data["guild_admins"].setdefault(
            str(guild_id), {"roles": [], "users": []}
        )

    def get_guild_admins(self, guild_id: int) -> dict:
        return self._data["guild_admins"].get(str(guild_id), {"roles": [], "users": []})

    def add_admin_role(self, guild_id: int, role_id: int):
        admins = self._guild_admins(guild_id)
        if role_id not in admins["roles"]:
            admins["roles"].append(role_id)

    def remove_admin_role(self, guild_id: int, role_id: int):
        admins = self._guild_admins(guild_id)
        if role_id in admins["roles"]:
            admins["roles"].remove(role_id)

    def add_admin_user(self, guild_id: int, user_id: int):
        admins = self._guild_admins(guild_id)
        if user_id not in admins["users"]:
            admins["users"].append(user_id)

    def remove_admin_user(self, guild_id: int, user_id: int):
        admins = self._guild_admins(guild_id)
        if user_id in admins["users"]:
            admins["users"].remove(user_id)

    # --- role/userzy, których wiadomości nigdy nie są kasowane (VIP) ---

    def _guild_vips(self, guild_id: int) -> dict:
        return self._data["guild_vips"].setdefault(
            str(guild_id), {"roles": [], "users": []}
        )

    def get_guild_vips(self, guild_id: int) -> dict:
        return self._data["guild_vips"].get(str(guild_id), {"roles": [], "users": []})

    def add_vip_role(self, guild_id: int, role_id: int):
        vips = self._guild_vips(guild_id)
        if role_id not in vips["roles"]:
            vips["roles"].append(role_id)

    def remove_vip_role(self, guild_id: int, role_id: int):
        vips = self._guild_vips(guild_id)
        if role_id in vips["roles"]:
            vips["roles"].remove(role_id)

    def add_vip_user(self, guild_id: int, user_id: int):
        vips = self._guild_vips(guild_id)
        if user_id not in vips["users"]:
            vips["users"].append(user_id)

    def remove_vip_user(self, guild_id: int, user_id: int):
        vips = self._guild_vips(guild_id)
        if user_id in vips["users"]:
            vips["users"].remove(user_id)

    # --- język bota per serwer ---

    def get_guild_lang(self, guild_id: int) -> str:
        return self._data["guild_lang"].get(str(guild_id), DEFAULT_LANG)

    def set_guild_lang(self, guild_id: int, lang: str):
        self._data["guild_lang"][str(guild_id)] = lang


config_store = ConfigStore(CONFIG_PATH)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents, help_command=None)


@bot.event
async def on_ready():
    log.info("Zalogowano jako %s (ID: %s)", bot.user, bot.user.id)
    if not cleanup_loop.is_running():
        cleanup_loop.start()


def _can_use_cleanup_commands():
    """Manage Messages / Administrator, LUB rola/user dodany komendą 'admin'."""
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False
        author = ctx.author
        perms = author.guild_permissions
        if perms.manage_messages or perms.administrator:
            return True
        guild_admins = config_store.get_guild_admins(ctx.guild.id)
        if author.id in guild_admins["users"]:
            return True
        author_role_ids = {r.id for r in author.roles}
        if author_role_ids & set(guild_admins["roles"]):
            return True
        return False
    return commands.check(predicate)


def _can_manage_admin_list():
    """Tylko Administrator serwera może dodawać/usuwać role i userów z dostępem do komend."""
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)


async def _delete_message_if_exists(channel: discord.abc.Messageable, message_id: int):
    """Usuwa wskazaną wiadomość, jeśli istnieje (np. stare ostrzeżenie/potwierdzenie)."""
    try:
        old_message = await channel.fetch_message(message_id)
        await old_message.delete()
    except discord.NotFound:
        pass
    except discord.HTTPException as exc:
        log.warning("Nie udało się usunąć starej wiadomości %s na kanale %s: %s", message_id, channel.id, exc)


@bot.command(name="set")
@_can_use_cleanup_commands()
async def set_cmd(ctx: commands.Context, duration: str, count: int, mode: str = ""):
    """Ustawia czyszczenie kanału: @bot set 5m 10 [new]
    (0 = pomiń to kryterium, 0 0 = wyłącz, dopisz 'new' by pominąć wiadomości sprzed tej komendy)"""
    lang = config_store.get_guild_lang(ctx.guild.id)
    bot_name = ctx.guild.me.display_name if ctx.guild else bot.user.name
    mention = f"@{bot_name}"

    try:
        seconds = parse_duration(duration, lang)
    except ValueError as exc:
        await ctx.send(str(exc))
        return

    if count < 0:
        await ctx.send(t(lang, "bad_count"))
        return

    only_new = mode.strip().lower() == "new"

    old_cfg = config_store.get_channel(ctx.channel.id)
    old_pinned_id = old_cfg.get("pinned_message_id") if old_cfg else None
    old_warning_id = old_cfg.get("warning_message_id") if old_cfg else None

    # Czas i liczba ustawione na 0 -> działa jak @bot unset.
    if seconds == 0 and count == 0:
        if old_pinned_id:
            await _delete_message_if_exists(ctx.channel, old_pinned_id)
        if old_warning_id:
            await _delete_message_if_exists(ctx.channel, old_warning_id)
        config_store.remove_channel(ctx.channel.id)
        await config_store.save()
        await ctx.send(t(lang, "set_confirmation_disabled"))
        return

    only_new_after = datetime.now(timezone.utc) if only_new else None
    config_store.set_channel(ctx.channel.id, seconds, count, only_new_after)

    # 1. Wiadomość z regułą — zostaje na stałe jako przypomnienie ustawień.
    if count == 0:
        confirm_text = t(lang, "confirm_time_only", duration=format_duration(seconds))
    elif seconds == 0:
        confirm_text = t(lang, "confirm_count_only", count=count)
    else:
        confirm_text = t(lang, "confirm_both", duration=format_duration(seconds), count=count)

    if only_new:
        confirm_text += t(lang, "confirm_only_new")

    confirmation = await ctx.send(confirm_text)
    config_store.set_pinned_message(ctx.channel.id, confirmation.id)
    await config_store.save()

    # 2. Wiadomość ostrzegawcza — znika po wygaśnięciu cooldownu.
    minutes = max(1, WARNING_COOLDOWN_SECONDS // 60)
    activate_at = datetime.now(timezone.utc) + timedelta(seconds=WARNING_COOLDOWN_SECONDS)

    warning_text = t(lang, "warning_generic", minutes=minutes, mention=mention)
    if not only_new:
        warning_text += " " + t(lang, "warning_new_hint", mention=mention)

    warning = await ctx.send(warning_text)
    config_store.set_warning(ctx.channel.id, warning.id, activate_at)
    await config_store.save()

    if old_pinned_id and old_pinned_id not in (confirmation.id, warning.id):
        await _delete_message_if_exists(ctx.channel, old_pinned_id)
    if old_warning_id and old_warning_id not in (confirmation.id, warning.id):
        await _delete_message_if_exists(ctx.channel, old_warning_id)


@bot.command(name="lang")
@_can_manage_admin_list()
async def set_lang(ctx: commands.Context, lang_code: str):
    """Ustawia język bota na tym serwerze: @bot lang EN / @bot lang PL"""
    current_lang = config_store.get_guild_lang(ctx.guild.id)
    lang_input = lang_code.strip().lower()
    if lang_input not in ("en", "pl"):
        await ctx.reply(t(current_lang, "lang_invalid"), mention_author=False)
        return

    config_store.set_guild_lang(ctx.guild.id, lang_input)
    await config_store.save()
    lang_name = t(lang_input, "lang_name_en" if lang_input == "en" else "lang_name_pl")
    await ctx.reply(t(lang_input, "lang_set", lang_name=lang_name), mention_author=False)


@bot.command(name="unset")
@_can_use_cleanup_commands()
async def unset_cleanup(ctx: commands.Context):
    """Wyłącza czyszczenie na tym kanale: @bot unset"""
    lang = config_store.get_guild_lang(ctx.guild.id)

    cfg = config_store.get_channel(ctx.channel.id)
    pinned_message_id = cfg.get("pinned_message_id") if cfg else None
    warning_message_id = cfg.get("warning_message_id") if cfg else None
    if pinned_message_id:
        await _delete_message_if_exists(ctx.channel, pinned_message_id)
    if warning_message_id:
        await _delete_message_if_exists(ctx.channel, warning_message_id)

    config_store.remove_channel(ctx.channel.id)
    await config_store.save()
    await ctx.reply(t(lang, "unset_confirmation"), mention_author=False)


@bot.command(name="status")
async def status_cleanup(ctx: commands.Context):
    """Pokazuje aktualną konfigurację kanału: @bot status"""
    lang = config_store.get_guild_lang(ctx.guild.id) if ctx.guild else DEFAULT_LANG
    cfg = config_store.get_channel(ctx.channel.id)
    if not cfg:
        await ctx.reply(t(lang, "status_none"), mention_author=False)
        return

    message = t(lang, "status_info", time=format_duration(cfg["seconds"]), count=cfg["count"])

    if cfg.get("only_new_after"):
        message += " " + t(lang, "status_only_new")

    activate_at_raw = cfg.get("activate_at")
    if activate_at_raw:
        activate_at = datetime.fromisoformat(activate_at_raw)
        if datetime.now(timezone.utc) < activate_at:
            message += t(lang, "status_cooldown", timestamp=int(activate_at.timestamp()))

    await ctx.reply(message, mention_author=False)


@bot.command(name="admin")
@_can_manage_admin_list()
async def add_admin(ctx: commands.Context, target: typing.Union[discord.Role, discord.Member]):
    """Nadaje roli lub userowi dostęp do komend bota: @bot admin @Rola / @Uzytkownik"""
    lang = config_store.get_guild_lang(ctx.guild.id)
    if isinstance(target, discord.Role):
        config_store.add_admin_role(ctx.guild.id, target.id)
        await config_store.save()
        await ctx.reply(t(lang, "admin_role_added", name=target.name), mention_author=False)
    else:
        config_store.add_admin_user(ctx.guild.id, target.id)
        await config_store.save()
        await ctx.reply(t(lang, "admin_user_added", name=target.display_name), mention_author=False)


@bot.command(name="unadmin")
@_can_manage_admin_list()
async def remove_admin(ctx: commands.Context, target: typing.Union[discord.Role, discord.Member]):
    """Odbiera roli lub userowi dostęp do komend bota: @bot unadmin @Rola / @Uzytkownik"""
    lang = config_store.get_guild_lang(ctx.guild.id)
    if isinstance(target, discord.Role):
        config_store.remove_admin_role(ctx.guild.id, target.id)
        await config_store.save()
        await ctx.reply(t(lang, "admin_role_removed", name=target.name), mention_author=False)
    else:
        config_store.remove_admin_user(ctx.guild.id, target.id)
        await config_store.save()
        await ctx.reply(t(lang, "admin_user_removed", name=target.display_name), mention_author=False)


@bot.command(name="adminlist")
@_can_manage_admin_list()
async def list_admins(ctx: commands.Context):
    """Pokazuje role/userów z dostępem do komend na tym serwerze: @bot adminlist"""
    lang = config_store.get_guild_lang(ctx.guild.id)
    admins = config_store.get_guild_admins(ctx.guild.id)
    role_names = []
    for role_id in admins["roles"]:
        role = ctx.guild.get_role(role_id)
        role_names.append(role.name if role else f"(deleted role {role_id})")
    user_names = []
    for user_id in admins["users"]:
        member = ctx.guild.get_member(user_id)
        user_names.append(member.display_name if member else f"(unknown user {user_id})")

    none_label = t(lang, "adminlist_none")
    lines = [
        t(lang, "adminlist_title"),
        t(lang, "adminlist_roles", value=", ".join(role_names) if role_names else none_label),
        t(lang, "adminlist_users", value=", ".join(user_names) if user_names else none_label),
    ]
    await ctx.reply("\n".join(lines), mention_author=False)


@bot.command(name="vip")
@_can_manage_admin_list()
async def add_vip(ctx: commands.Context, target: typing.Union[discord.Role, discord.Member]):
    """Wyklucza rolę lub usera z czyszczenia — ich wiadomości nigdy nie są kasowane: @bot vip @Rola / @Uzytkownik"""
    lang = config_store.get_guild_lang(ctx.guild.id)
    if isinstance(target, discord.Role):
        config_store.add_vip_role(ctx.guild.id, target.id)
        await config_store.save()
        await ctx.reply(t(lang, "vip_role_added", name=target.name), mention_author=False)
    else:
        config_store.add_vip_user(ctx.guild.id, target.id)
        await config_store.save()
        await ctx.reply(t(lang, "vip_user_added", name=target.display_name), mention_author=False)


@bot.command(name="unvip")
@_can_manage_admin_list()
async def remove_vip(ctx: commands.Context, target: typing.Union[discord.Role, discord.Member]):
    """Cofa wykluczenie z czyszczenia: @bot unvip @Rola / @Uzytkownik"""
    lang = config_store.get_guild_lang(ctx.guild.id)
    if isinstance(target, discord.Role):
        config_store.remove_vip_role(ctx.guild.id, target.id)
        await config_store.save()
        await ctx.reply(t(lang, "vip_role_removed", name=target.name), mention_author=False)
    else:
        config_store.remove_vip_user(ctx.guild.id, target.id)
        await config_store.save()
        await ctx.reply(t(lang, "vip_user_removed", name=target.display_name), mention_author=False)


@bot.command(name="viplist")
@_can_manage_admin_list()
async def list_vips(ctx: commands.Context):
    """Pokazuje role/userów wykluczonych z czyszczenia na tym serwerze: @bot viplist"""
    lang = config_store.get_guild_lang(ctx.guild.id)
    vips = config_store.get_guild_vips(ctx.guild.id)
    role_names = []
    for role_id in vips["roles"]:
        role = ctx.guild.get_role(role_id)
        role_names.append(role.name if role else f"(deleted role {role_id})")
    user_names = []
    for user_id in vips["users"]:
        member = ctx.guild.get_member(user_id)
        user_names.append(member.display_name if member else f"(unknown user {user_id})")

    none_label = t(lang, "adminlist_none")
    lines = [
        t(lang, "viplist_title"),
        t(lang, "adminlist_roles", value=", ".join(role_names) if role_names else none_label),
        t(lang, "adminlist_users", value=", ".join(user_names) if user_names else none_label),
    ]
    await ctx.reply("\n".join(lines), mention_author=False)


@bot.command(name="help")
@_can_use_cleanup_commands()
async def show_help(ctx: commands.Context):
    """Pokazuje listę komend bota: @bot help"""
    lang = config_store.get_guild_lang(ctx.guild.id)
    bot_name = ctx.guild.me.display_name if ctx.guild else bot.user.name
    mention = f"@{bot_name}"
    minutes = max(1, WARNING_COOLDOWN_SECONDS // 60)

    lines = [
        t(lang, "help_title"),
        "",
        t(lang, "help_set", mention=mention),
        t(lang, "help_set_example", mention=mention),
        t(lang, "help_set_units"),
        t(lang, "help_set_zero", mention=mention),
        t(lang, "help_set_new", mention=mention),
        t(lang, "help_set_warning", mention=mention, minutes=minutes),
        "",
        t(lang, "help_unset", mention=mention),
        "",
        t(lang, "help_status", mention=mention),
        "",
        t(lang, "help_admin", mention=mention),
        t(lang, "help_admin_example", mention=mention),
        "",
        t(lang, "help_unadmin", mention=mention),
        "",
        t(lang, "help_adminlist", mention=mention),
        "",
        t(lang, "help_vip", mention=mention),
        t(lang, "help_vip_example", mention=mention),
        "",
        t(lang, "help_unvip", mention=mention),
        "",
        t(lang, "help_viplist", mention=mention),
        "",
        t(lang, "help_lang", mention=mention),
        "",
        t(lang, "help_help", mention=mention),
    ]
    await ctx.reply("\n".join(lines), mention_author=False)


async def _cleanup_channel(channel: discord.TextChannel, seconds: int, count: int,
                            only_new_after: datetime | None, protected_message_id: int | None = None):
    now = datetime.now(timezone.utc)
    fourteen_days_ago = now - timedelta(days=14)

    vips = config_store.get_guild_vips(channel.guild.id)
    vip_role_ids = set(vips["roles"])
    vip_user_ids = set(vips["users"])

    def _is_protected(message: discord.Message) -> bool:
        if message.id == protected_message_id:
            return True
        if message.author.id in vip_user_ids:
            return True
        author_roles = getattr(message.author, "roles", None)
        if author_roles:
            if {r.id for r in author_roles} & vip_role_ids:
                return True
        return False

    # Jeśli włączono tryb "tylko nowe", nic sprzed tego momentu nigdy nie jest ruszane.
    lower_bound = only_new_after if only_new_after and only_new_after > fourteen_days_ago else fourteen_days_ago

    # seconds == 0 -> kryterium czasu wyłączone, kasujemy tylko po liczbie wiadomości.
    if seconds > 0:
        cutoff = now - timedelta(seconds=seconds)
        # Granica, od której trzeba kasować pojedynczo (bulk delete działa tylko do 14 dni wstecz,
        # a przy trybie "tylko nowe" nigdy nie schodzimy poniżej only_new_after).
        individual_boundary = min(cutoff, fourteen_days_ago)
        if only_new_after:
            individual_boundary = max(individual_boundary, only_new_after)

        try:
            # 1a. Bulk delete dla wiadomości starszych niż próg, ale młodszych niż 14 dni
            #     (i, jeśli włączone, młodszych niż only_new_after). Wiadomość ostrzegawcza
            #     i wiadomości VIP-ów są pomijane.
            bulk_after = max(fourteen_days_ago, only_new_after) if only_new_after else fourteen_days_ago
            if cutoff > bulk_after:
                await channel.purge(before=cutoff, after=bulk_after, limit=500,
                                     check=lambda m: not _is_protected(m))
        except discord.Forbidden:
            log.warning("Brak uprawnień do czyszczenia kanału %s", channel.id)
            return
        except discord.HTTPException as exc:
            log.warning("Błąd podczas czyszczenia (czas, bulk) kanału %s: %s", channel.id, exc)

        try:
            # 1b. Wiadomości starsze niż 14 dni (lub bardzo długi próg) — pojedynczo,
            #     ale nigdy starsze niż only_new_after, jeśli tryb "tylko nowe" jest włączony.
            #     Wiadomość ostrzegawcza i wiadomości VIP-ów są pomijane.
            if individual_boundary > lower_bound:
                async for msg in channel.history(before=individual_boundary, after=lower_bound, limit=200):
                    if _is_protected(msg):
                        continue
                    try:
                        await msg.delete()
                    except discord.HTTPException:
                        pass
        except discord.Forbidden:
            log.warning("Brak uprawnień do czyszczenia kanału %s", channel.id)
            return
        except discord.HTTPException as exc:
            log.warning("Błąd podczas czyszczenia (czas, stare) kanału %s: %s", channel.id, exc)

    # count == 0 -> kryterium liczby wiadomości wyłączone.
    if count <= 0:
        return

    try:
        # 2. Jeśli wciąż jest za dużo wiadomości, usuń nadmiar od najstarszych.
        #    W trybie "tylko nowe" liczymy tylko wiadomości nowsze niż only_new_after.
        #    Wiadomość ostrzegawcza i wiadomości VIP-ów nie liczą się do limitu i nigdy nie są kasowane.
        if only_new_after:
            history = [msg async for msg in channel.history(limit=count + 100, after=only_new_after)
                       if not _is_protected(msg)]
        else:
            history = [msg async for msg in channel.history(limit=count + 100) if not _is_protected(msg)]
        if len(history) > count:
            excess = history[count:]  # najstarsze wiadomości ponad limit
            fresh_enough = [m for m in excess if m.created_at > fourteen_days_ago]
            old_ones = [m for m in excess if m.created_at <= fourteen_days_ago]

            if len(fresh_enough) == 1:
                await fresh_enough[0].delete()
            elif len(fresh_enough) > 1:
                await channel.delete_messages(fresh_enough)

            for msg in old_ones:
                try:
                    await msg.delete()
                except discord.HTTPException:
                    pass
    except discord.Forbidden:
        log.warning("Brak uprawnień do czyszczenia kanału %s", channel.id)
    except discord.HTTPException as exc:
        log.warning("Błąd podczas czyszczenia (liczba) kanału %s: %s", channel.id, exc)


@tasks.loop(seconds=CHECK_INTERVAL)
async def cleanup_loop():
    now = datetime.now(timezone.utc)
    for channel_id, cfg in config_store.all_channels().items():
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            continue

        activate_at_raw = cfg.get("activate_at")
        if activate_at_raw:
            activate_at = datetime.fromisoformat(activate_at_raw)
            if now < activate_at:
                continue  # jeszcze trwa 10-minutowy cooldown ostrzeżenia — nic nie ruszamy

        # Cooldown minął (albo go nie było, stara konfiguracja) — kasujemy wiadomość
        # ostrzegawczą (spełniła swoją rolę) i czyścimy kanał.
        warning_message_id = cfg.get("warning_message_id")
        if warning_message_id:
            await _delete_message_if_exists(channel, warning_message_id)
            config_store.clear_warning(int(channel_id))
            await config_store.save()

        only_new_after_raw = cfg.get("only_new_after")
        only_new_after = datetime.fromisoformat(only_new_after_raw) if only_new_after_raw else None

        # Wiadomość z regułą (pinned_message_id) zostaje chroniona na stałe.
        await _cleanup_channel(channel, cfg["seconds"], cfg["count"], only_new_after,
                                cfg.get("pinned_message_id"))


@cleanup_loop.before_loop
async def before_cleanup_loop():
    await bot.wait_until_ready()


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Brak zmiennej środowiskowej DISCORD_TOKEN")
    bot.run(TOKEN)
