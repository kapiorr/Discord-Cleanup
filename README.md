# Discord Cleaner Bot

Bot do Discorda, który automatycznie czyści wiadomości na wybranych kanałach:
- usuwa wiadomości starsze niż ustawiony czas,
- albo, gdy liczba wiadomości na kanale przekroczy ustalony limit, kasuje od najstarszej.

Konfiguracja jest per-kanał i zapisywana w pliku `data/config.json`, więc przetrwa restart kontenera.

---

## 1. Utworzenie aplikacji bota w Discord Developer Portal

1. Wejdź na https://discord.com/developers/applications i zaloguj się.
2. Kliknij **New Application**, nadaj nazwę (np. `Cleaner Bot`) i zatwierdź.
3. W lewym menu wejdź w zakładkę **Bot**.
   - Kliknij **Reset Token** / **Copy** aby skopiować token bota — będzie potrzebny w kroku 3. Token pokazuje się tylko raz, zapisz go bezpiecznie.
   - W sekcji **Privileged Gateway Intents** włącz **MESSAGE CONTENT INTENT** (bez tego bot nie odczyta treści komend). Zapisz zmiany.

---

## 2. Zaproszenie bota na serwer

1. W lewym menu wejdź w **OAuth2 → URL Generator**.
2. W sekcji **Scopes** zaznacz: `bot`.
3. W sekcji **Bot Permissions** zaznacz:
   - **View Channel**
   - **Send Messages**
   - **Read Message History**
   - **Manage Messages**
4. Na dole strony skopiuj wygenerowany URL, otwórz go w przeglądarce, wybierz swój serwer i zatwierdź.
5. Bot pojawi się na serwerze (offline, dopóki nie uruchomisz kontenera).

### Ograniczenie bota tylko do wybranych kanałów (zalecane)

Domyślnie zaproszony bot może widzieć wszystkie kanały. Żeby to ograniczyć:

1. Serwer → **Ustawienia serwera → Role** → znajdź rolę bota (tworzy się automatycznie przy zaproszeniu, zwykle o nazwie aplikacji).
2. Na poziomie tej roli **odbierz** uprawnienie **View Channel** (Przeglądaj kanał) — bot przestanie widzieć wszystkie kanały domyślnie.
3. Wejdź na kanał, na którym bot ma czyścić wiadomości → **Ustawienia kanału → Uprawnienia → Dodaj rolę/uczestnika** → wybierz rolę bota i włącz dla niej: **View Channel**, **Send Messages**, **Read Message History**, **Manage Messages**.
4. Powtórz krok 3 dla każdego kanału, na którym bot ma działać.

---

## 3. Konfiguracja tokena

1. Skopiuj plik `.env.example` i zmień nazwę na `.env`:
   ```bash
   cp .env.example .env
   ```
2. Otwórz `.env` i wklej token bota skopiowany w kroku 1:
   ```
   DISCORD_TOKEN=twoj_prawdziwy_token
   ```

Plik `.env` nie powinien trafiać do repozytorium git (dodaj go do `.gitignore`).

---

## 4. Uruchomienie (Docker)

Wymaga zainstalowanego Dockera i Docker Compose.

```bash
docker compose up -d --build
```

Sprawdzenie logów:
```bash
docker compose logs -f
```

Po poprawnym starcie w logach pojawi się linia `Zalogowano jako <nazwa_bota> (ID: ...)`.

Zatrzymanie:
```bash
docker compose down
```

Konfiguracja kanałów zapisuje się w `./data/config.json` na hoście (wolumen), więc przetrwa `docker compose down/up` i przebudowę obrazu.

---

## 5. Uruchomienie bez Dockera (opcjonalnie)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export DISCORD_TOKEN=twoj_prawdziwy_token
python bot.py
```

---

## 6. Komendy bota

Wszystkie komendy wywołuje się przez wspomnienie (mention) bota na kanale, np. `@Cleaner Bot set 5m 10`.

| Komenda | Dostęp | Opis |
|---|---|---|
| `@bot set <czas> <liczba> [new]` | Manage Messages / Administrator / lista `admin` | Ustawia czyszczenie kanału. Format czasu: `30s`, `5m`, `1h`. `0` w dowolnej wartości pomija to kryterium, `0 0` wyłącza (jak `unset`). Dopisz `new` na końcu, żeby dotyczyło tylko wiadomości wysłanych po tej komendzie. Przykład: `@bot set 5m 10` |
| `@bot unset` | Manage Messages / Administrator / lista `admin` | Wyłącza czyszczenie na tym kanale |
| `@bot status` | każdy | Pokazuje aktualną konfigurację kanału |
| `@bot admin @Rola` / `@Uzytkownik` | tylko Administrator serwera | Nadaje dostęp do komend `set`/`unset`/`help` |
| `@bot unadmin @Rola` / `@Uzytkownik` | tylko Administrator serwera | Odbiera dostęp |
| `@bot adminlist` | tylko Administrator serwera | Pokazuje role/userów z dostępem |
| `@bot vip @Rola` / `@Uzytkownik` | tylko Administrator serwera | Ich wiadomości nigdy nie są usuwane przy czyszczeniu |
| `@bot unvip @Rola` / `@Uzytkownik` | tylko Administrator serwera | Cofa to wykluczenie |
| `@bot viplist` | tylko Administrator serwera | Pokazuje role/userów wykluczonych z czyszczenia |
| `@bot lang EN` / `@bot lang PL` | tylko Administrator serwera | Ustawia język odpowiedzi bota na tym serwerze (domyślnie: angielski) |
| `@bot help` | Manage Messages / Administrator / lista `admin` | Pokazuje listę komend z przykładami |

Bot obsługuje wiele serwerów jednocześnie — wystarczy zaprosić go na kolejny serwer (link z kroku 2), bez zmian w kodzie.

---

## 7. Zmienne środowiskowe

| Zmienna | Domyślna wartość | Opis |
|---|---|---|
| `DISCORD_TOKEN` | — (wymagane) | Token bota z Developer Portal |
| `CONFIG_PATH` | `/data/config.json` | Ścieżka pliku z konfiguracją |
| `CHECK_INTERVAL_SECONDS` | `20` | Co ile sekund bot sprawdza kanały i czyści wiadomości |
| `WARNING_COOLDOWN_SECONDS` | `600` (10 minut) | Ile sekund bot czeka po `set`, zanim zacznie faktycznie kasować wiadomości (dając czas na `unset`) |

---

## 8. Rozwiązywanie problemów

- **Bot jest online, ale nie reaguje na komendy** → sprawdź, czy w Developer Portal jest włączony **MESSAGE CONTENT INTENT** (krok 1).
- **Bot nie usuwa wiadomości** → sprawdź, czy rola bota ma uprawnienie **Manage Messages** na danym kanale (krok 2).
- **`discord.Forbidden` w logach** → brak uprawnień na konkretnym kanale — dodaj rolę bota w ustawieniach uprawnień kanału.
- **Zmiana tokena** → zaktualizuj `.env` i zrestartuj kontener: `docker compose up -d --build`.

---
---

# Discord Cleaner Bot (English)

A Discord bot that automatically cleans messages in selected channels:
- deletes messages older than a configured time,
- or, once the number of messages in the channel exceeds a set limit, deletes starting from the oldest.

Configuration is per-channel and stored in `data/config.json`, so it survives container restarts.

---

## 1. Create a bot application in the Discord Developer Portal

1. Go to https://discord.com/developers/applications and log in.
2. Click **New Application**, give it a name (e.g. `Cleaner Bot`) and confirm.
3. In the left menu, open the **Bot** tab.
   - Click **Reset Token** / **Copy** to copy the bot token — you'll need it in step 3. The token is shown only once, so save it somewhere safe.
   - Under **Privileged Gateway Intents**, enable **MESSAGE CONTENT INTENT** (without this the bot cannot read command text). Save changes.

---

## 2. Invite the bot to your server

1. In the left menu, go to **OAuth2 → URL Generator**.
2. Under **Scopes**, check: `bot`.
3. Under **Bot Permissions**, check:
   - **View Channel**
   - **Send Messages**
   - **Read Message History**
   - **Manage Messages**
4. Copy the generated URL at the bottom of the page, open it in a browser, pick your server and confirm.
5. The bot will appear on the server (offline until you start the container).

### Restricting the bot to specific channels only (recommended)

By default, an invited bot can see every channel. To restrict that:

1. Server → **Server Settings → Roles** → find the bot's role (created automatically when it's invited, usually named after the application).
2. At the role level, **remove** the **View Channel** permission — the bot will no longer see any channel by default.
3. Go to the channel where the bot should clean messages → **Channel Settings → Permissions → Add role/member** → select the bot's role and enable: **View Channel**, **Send Messages**, **Read Message History**, **Manage Messages**.
4. Repeat step 3 for every channel the bot should operate on.

---

## 3. Configure the token

1. Copy `.env.example` and rename it to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and paste the bot token you copied in step 1:
   ```
   DISCORD_TOKEN=your_real_token
   ```

The `.env` file should not be committed to git (add it to `.gitignore`).

---

## 4. Running (Docker)

Requires Docker and Docker Compose installed.

```bash
docker compose up -d --build
```

Check logs:
```bash
docker compose logs -f
```

Once started successfully, the logs will show a line like `Zalogowano jako <bot_name> (ID: ...)`.

Stop:
```bash
docker compose down
```

Channel configuration is saved to `./data/config.json` on the host (volume mount), so it survives `docker compose down/up` and image rebuilds.

---

## 5. Running without Docker (optional)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export DISCORD_TOKEN=your_real_token
python bot.py
```

---

## 6. Bot commands

All commands are invoked by mentioning the bot in a channel, e.g. `@Cleaner Bot set 5m 10`.

| Command | Access | Description |
|---|---|---|
| `@bot set <duration> <count> [new]` | Manage Messages / Administrator / `admin` list | Sets up cleanup for the channel. Duration format: `30s`, `5m`, `1h`. `0` on either value skips that rule, `0 0` disables (same as `unset`). Add `new` at the end to only affect messages sent after this command. Example: `@bot set 5m 10` |
| `@bot unset` | Manage Messages / Administrator / `admin` list | Disables cleanup for the channel |
| `@bot status` | anyone | Shows the channel's current configuration |
| `@bot admin @Role` / `@User` | Server Administrator only | Grants access to `set`/`unset`/`help` |
| `@bot unadmin @Role` / `@User` | Server Administrator only | Revokes access |
| `@bot adminlist` | Server Administrator only | Shows roles/users with access |
| `@bot vip @Role` / `@User` | Server Administrator only | Their messages are never deleted by cleanup |
| `@bot unvip @Role` / `@User` | Server Administrator only | Removes that exemption |
| `@bot viplist` | Server Administrator only | Shows roles/users exempt from cleanup |
| `@bot lang EN` / `@bot lang PL` | Server Administrator only | Sets the bot's reply language for this server (default: English) |
| `@bot help` | Manage Messages / Administrator / `admin` list | Shows the command list with examples |

The bot works across multiple servers at once — just invite it to another server (link from step 2), no code changes needed.

---

## 7. Environment variables

| Variable | Default | Description |
|---|---|---|
| `DISCORD_TOKEN` | — (required) | Bot token from the Developer Portal |
| `CONFIG_PATH` | `/data/config.json` | Path to the configuration file |
| `CHECK_INTERVAL_SECONDS` | `20` | How often (in seconds) the bot checks channels and cleans messages |
| `WARNING_COOLDOWN_SECONDS` | `600` (10 minutes) | How many seconds the bot waits after `set` before actually deleting messages (giving time to `unset`) |

---

## 8. Troubleshooting

- **Bot is online but doesn't respond to commands** → check that **MESSAGE CONTENT INTENT** is enabled in the Developer Portal (step 1).
- **Bot isn't deleting messages** → check that the bot's role has the **Manage Messages** permission on that channel (step 2).
- **`discord.Forbidden` in the logs** → missing permissions on a specific channel — add the bot's role in that channel's permission settings.
- **Changing the token** → update `.env` and restart the container: `docker compose up -d --build`.
