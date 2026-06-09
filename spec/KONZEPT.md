# Konzept & Implementierungsplan: Heimautomatisierung mit Alexa (`pantau-alexa`)

> Stand: 2026-06-09 · Stack: Python 3.14 · FastAPI · AWS (Terraform) · Alexa Smart-Home-Skill

## 1. Context / Motivation

Es soll ein Alexa-gesteuertes Heimautomatisierungssystem entstehen, das **Fernseher**
(Logitech Harmony Hub), **Rollos** (HomeKit) und **Heizungsthermostate** (AVM FRITZ!Box)
über natürliche Sprachbefehle steuert. Die Geräteanbindung erfolgt über einen
selbst betriebenen **FastAPI-Server im LAN**, der die drei vorhandenen, asynchronen
Python-Bibliotheken (`homekit`, `fritzctl`, `harmonyhub`) nutzt.

Zu unterstützende Befehle (Beispiele):

- „Alexa, schalte ZDF ein" → Fernseher auf Kanal *ZDF*
- „Alexa, schalte den Fernseher stumm" / „Alexa, schalte den Ton ein"
- „Alexa, stell die Heizung im Wohnzimmer auf 22 Grad"
- „Alexa, mach die Rollos in der Küche halb runter"

Zwei harte Randbedingungen prägen die Architektur:

1. **Der Heimserver hat keine stabile öffentliche Adresse** (rein dynamisch / rotierende
   Tunnel-URL). Seine aktuelle Erreichbarkeit wird in einer **Datei auf S3** hinterlegt
   und vor jeder Befehlsweiterleitung gelesen.
2. **Account Linking**: Der Nutzer muss sich erst am Heimserver anmelden, bevor der Skill
   nutzbar ist. Der **Heimserver ist selbst der OAuth2-Identity-Provider**.

Da Alexa Smart-Home-Skills zwingend eine **AWS-Lambda** als Endpunkt verlangen und die
Geräte-Bibliotheken LAN-Zugriff brauchen (also **nicht** in Lambda laufen können), ergibt
sich zwingend das Muster: **Alexa → AWS (Lambda/API Gateway, stabil) → S3-Lookup →
FastAPI-Heimserver (dynamisch)**. AWS ist dabei ein **dummer Reverse-Proxy**; die gesamte
Intelligenz (Geräteerkennung, Orchestrierung) liegt im FastAPI-Server.

---

## 2. Architekturentscheidungen (mit Begründung)

| # | Entscheidung | Wahl | Begründung |
|---|---|---|---|
| 1 | Skill-Typ | **Smart-Home-Skill** | Befehle ohne Invocation-Name („Alexa, schalte … ein") nur hier möglich. |
| 2 | Skill-Endpunkt | **AWS Lambda als Proxy** | Smart-Home-Skills erfordern Lambda; Bibliotheken brauchen LAN → FastAPI im Heim. |
| 3 | Server-Erreichbarkeit | **Dynamisch + S3-Beacon** | Heimserver veröffentlicht aktuelle Tunnel-URL nach S3; Lambda liest sie vor jedem Befehl. |
| 4 | OAuth/Account Linking | **Heimserver als IdP, via AWS gefrontet** | Stabile OAuth-Endpunkte (API Gateway) als Pflicht von Alexa; eigentliche IdP-Logik im FastAPI-Server. |
| 5 | Kanalwahl („ZDF") | **Sender als eigene PowerController-Geräte** | Umgeht die fragile `ChannelController`-Namensauflösung; „schalte ZDF ein" = robustes `TurnOn`. Server orchestriert Aktivität + Kanal. |
| 6 | Mute/Unmute | **`Alexa.Speaker.SetMute` + Assumed-State** | Harmony bietet nur einen **Mute-Toggle** (keine diskrete An/Aus). Server hält angenommenen Zustand. |
| 7 | Rollos | **`Alexa.RangeController` (Position 0–100) + Semantik** | `SetRangeValue(50)` für „halb"; Semantik-Mapping für „runter"/„hoch". |
| 8 | Thermostate | **`Alexa.ThermostatController.SetTargetTemperature`** | Direkte 1:1-Abbildung; `fritzctl` rundet auf 0,5 °C und erzwingt Grenzen. |
| 9 | AWS-IaC | **Terraform** | Vom Nutzer gewählt. |
| 10 | Stack | **Python 3.14, uv, FastAPI, Pydantic 2.13, ruff(88), pytest ≥80%** | Konsistent mit den Schwesterprojekten im Workspace. |

---

## 3. Gesamtarchitektur

```
   ┌──────────┐   Sprachbefehl    ┌──────────────────┐
   │  Nutzer  │ ────────────────► │  Alexa (Cloud)   │
   └──────────┘                   └───────┬──────────┘
                                          │ (1) Smart-Home-Directive  (2) OAuth (Account Linking)
                          ┌───────────────┴───────────────────────────┐
                          ▼                                            ▼
              ┌───────────────────────┐                  ┌────────────────────────┐
              │  Lambda: Directive-   │                  │ API Gateway + Lambda:  │
              │  Proxy (Skill-ARN)    │                  │ OAuth-Proxy            │
              └───────────┬───────────┘                  └───────────┬────────────┘
                          │  S3 GET (ETag, conditional)               │
                          ▼                                           │
              ┌───────────────────────┐                              │
              │  S3: endpoint.json    │ ◄──── PUT (Beacon-Updater) ───┼──┐
              │  { base_url, ... }    │                              │  │
              └───────────────────────┘                              │  │
                          │  forward (HTTPS-Tunnel + Shared-Secret)   │  │
                          └──────────────────┬────────────────────────┘  │
                                             ▼                            │
                          ┌────────────────────────────────────────┐     │
                          │      FastAPI-Heimserver (LAN)           │─────┘
                          │  • /alexa/directive  (Smart-Home)       │
                          │  • /oauth/authorize, /oauth/token (IdP) │
                          │  • Orchestrierung + Device-Registry     │
                          │  • Beacon-Updater (PUT nach S3)         │
                          └───────┬─────────────┬─────────────┬─────┘
                                  ▼             ▼             ▼
                          ┌──────────┐   ┌────────────┐  ┌──────────┐
                          │ harmony  │   │  fritzctl  │  │ homekit  │
                          │  (TV)    │   │(Thermostat)│  │ (Rollos) │
                          └──────────┘   └────────────┘  └──────────┘
```

### Datenfluss A — Account Linking (einmalig beim Aktivieren)

1. Nutzer aktiviert Skill in der Alexa-App → Alexa öffnet die **Authorization-URI**
   (stabile API-Gateway-URL).
2. OAuth-Proxy liest `endpoint.json` aus S3, leitet Browser-Flow (Login-Seite, Formular,
   302-Redirect) transparent an den **FastAPI-IdP** weiter.
3. Nutzer meldet sich am Heimserver an → Authorization-Code → Alexa tauscht ihn an der
   **Token-URI** (API Gateway → Proxy → FastAPI) gegen Access-/Refresh-Token (PKCE).
4. Erst jetzt ist der Skill nutzbar; Alexa führt `Alexa.Discovery` aus.

### Datenfluss B — Sprachbefehl (pro Kommando)

1. Alexa → Directive-Lambda (mit Bearer-Token des Nutzers).
2. Lambda liest `endpoint.json` aus S3 (**conditional GET via ETag** → erfüllt
   „vor jedem Befehl prüfen" ohne unnötige Latenz/Kosten).
3. Lambda leitet die Directive als JSON an `https://<base_url>/alexa/directive` weiter
   (Shared-Secret-Header + Bearer-Token-Passthrough).
4. FastAPI validiert Token & Secret, mappt Directive → Use-Case → Geräte-Adapter,
   orchestriert ggf. mehrere Schritte und antwortet im Alexa-Response-Format.

---

## 4. Geräte-Modell & Konfiguration (konfigurierbare Geräte mit Aliasen)

Die Geräte werden **deklarativ konfiguriert** (YAML), inkl. Aliasen. Das Hinzufügen eines
Senders oder Geräts ist reine Konfiguration (Open/Closed-Prinzip — keine Codeänderung).

```yaml
# config/devices.yaml
tv:
  harmony_host: "192.168.178.50"     # LAN-IP des Hubs
  watch_activity: "Fernseher"         # Harmony-Aktivität (start_activity)
  audio:
    id: "tv-audio"
    friendly_name: "Fernseher"        # "schalte den Fernseher stumm" / "Ton ein"
  channels:                           # Sender = eigene An/Aus-Geräte (PowerController)
    - id: "zdf"
      friendly_name: "ZDF"
      aliases: ["ZDF", "Zweites"]
      channel_number: "2"
    - id: "ard"
      friendly_name: "ARD"
      channel_number: "1"

blinds:                               # homekit (set_position)
  - id: "kueche-rollo"
    friendly_name: "Rollo Küche"
    aliases: ["Küche", "Rollos Küche"]
    homekit_entity_id: "cover.kueche"
    invert: false                     # 0=zu/runter, 100=auf/hoch (konfigurierbar)

thermostats:                          # fritzctl (set_temperature)
  - id: "wohnzimmer-heizung"
    friendly_name: "Heizung Wohnzimmer"
    aliases: ["Wohnzimmer", "Heizung im Wohnzimmer"]
    fritz_name: "Wohnzimmer"          # Name auf der FRITZ!Box → wird zu AIN aufgelöst
    min_celsius: 16
    max_celsius: 24
```

---

## 5. Alexa-Capability-Mapping (Befehl → Capability → Orchestrierung)

| Sprachbefehl | Alexa Capability / Directive | Endpoint | Server-Orchestrierung |
|---|---|---|---|
| „schalte ZDF ein" | `Alexa.PowerController` · `TurnOn` | `zdf` (Kanal) | `get_current_activity()`; falls nicht „Fernseher" aktiv → `start_activity("Fernseher")`; dann `hub.set_channel("2")` |
| „schalte ZDF aus" | `PowerController` · `TurnOff` | `zdf` | dokumentiert: `hub.power_off()` (TV aus) **oder** No-Op (konfigurierbar) |
| „schalte den Fernseher stumm" | `Alexa.Speaker` · `SetMute(true)` | `tv-audio` | falls Assumed-State ≠ stumm → `hub.send_key("mute")`; State aktualisieren |
| „schalte den Ton ein" | `Alexa.Speaker` · `SetMute(false)` | `tv-audio` | falls Assumed-State = stumm → `hub.send_key("mute")` (Toggle); State aktualisieren |
| „stell die Heizung im Wohnzimmer auf 22 Grad" | `Alexa.ThermostatController` · `SetTargetTemperature(22, CELSIUS)` | `wohnzimmer-heizung` | Name→AIN (`list_devices`); `client.set_temperature(ain, 22.0)` |
| „mach die Rollos in der Küche halb runter" | `Alexa.RangeController` · `SetRangeValue(50)` (instance `Blind.Position`) | `kueche-rollo` | `client.set_position("cover.kueche", 50)` |

**Semantik Rollos** (`RangeController` Semantics): `Close → 0`, `Open → 100`, sodass
„runter/zu" und „hoch/auf" funktionieren; „halb" ⇒ Alexa liefert `rangeValue: 50`.

---

## 6. FastAPI-Server — Clean Architecture (CCD)

Hexagonale Schichtung (Ports & Adapters), strikte Abhängigkeitsrichtung nach innen (DIP):

```
pantau/
├── domain/                # reine Domäne, keine I/O (Orange/Yellow)
│   ├── models.py          # Device, Channel, Thermostat, Blind, TvAudio
│   └── values.py          # Temperature, Percentage, MuteState (Value Objects, invariantengeschützt)
├── application/           # Use-Cases (SRP, ein Anwendungsfall pro Klasse)
│   ├── set_thermostat_temperature.py
│   ├── set_blind_position.py
│   ├── activate_channel.py        # mehrstufige Orchestrierung (Tell-Don't-Ask)
│   ├── set_tv_mute.py
│   └── discover_devices.py
├── ports/                 # Schnittstellen (ISP: schmale Ports je Fähigkeit)
│   ├── thermostat_port.py
│   ├── blind_port.py
│   ├── tv_port.py
│   ├── device_registry.py
│   ├── token_validator.py
│   └── beacon_publisher.py
├── adapters/              # Infrastruktur (implementiert Ports)
│   ├── fritz_thermostat_adapter.py    # nutzt fritzctl
│   ├── homekit_blind_adapter.py       # nutzt homekit
│   ├── harmony_tv_adapter.py          # nutzt harmonyhub
│   ├── s3_beacon_publisher.py
│   └── yaml_device_registry.py
├── interfaces/            # Delivery-Layer
│   ├── alexa/             # Directive-Parsing, Response-Builder, Capability-Handler
│   │   ├── router.py      # (namespace,name) → Handler  (OCP für neue Capabilities)
│   │   └── handlers/      # power, speaker, thermostat, range, discovery
│   └── oauth/             # OAuth2-Authorization-Server (IdP)
│       ├── authorize.py   # Login-Seite, Code-Erzeugung, PKCE
│       └── token.py       # Token/Refresh
├── api/                   # FastAPI-App + Router-Verdrahtung
│   └── app.py
├── config/                # pydantic-settings, devices.yaml-Loader
└── composition.py         # Composition Root (DI-Verdrahtung Ports↔Adapter)
```

**CCD-Prinzipien konkret:**

- **SRP/SoC**: je Adapter genau eine Bibliothek; je Use-Case genau ein Anwendungsfall.
- **DIP**: Use-Cases hängen nur von `ports/`-Interfaces ab; Adapter werden im
  Composition Root injiziert → Use-Cases sind ohne Hardware testbar (Fakes).
- **OCP**: neue Sender/Geräte = Config; neue Capability = neuer Handler im `router`,
  bestehende Use-Cases bleiben unberührt.
- **ISP**: `ThermostatPort`, `BlindPort`, `TvPort` getrennt statt eines „GodPort".
- **Tell-Don't-Ask / Law of Demeter**: Orchestrierung (`activate_channel`) spricht den
  `TvPort` an, nicht direkt `harmonyhub`-Interna.
- **Konventionen**: `logging` statt `print`, **keine f-Strings in Logger-Calls**
  (`log.info("Kanal %s", ch)`), Type-Hints überall, Zeilenlänge 88, Coverage ≥ 80 %.

---

## 7. Geräte-Adapter — verifizierte Bibliotheks-APIs

Die Signaturen stammen aus dem **lokalen Quellcode** der Schwesterprojekte
(`../homekit-py`, `../fritzhome-py`, `../harmonyhub-py`), nicht aus Vermutungen.

### TV — `harmonyhub` (Paket `harmonyhub-py`, import `harmonyhub`)

```python
from harmonyhub import HarmonyHubClient
async with HarmonyHubClient(host, connection_mode="persistent") as hub:
    status = await hub.get_current_activity()          # aktive Aktivität prüfen
    await hub.start_activity("Fernseher")              # TV-Aktivität starten
    await hub.set_channel("2")                          # ChannelResult (digits_then_enter)
    await hub.send_key("mute")                          # ⚠ TOGGLE (kein diskretes on/off)
```

> **Caveat**: `mute` ist nur ein Toggle → Server hält Assumed-State; Drift möglich, wenn
> per Originalfernbedienung gemutet wird (dokumentiertes Restrisiko).

### Thermostate — `fritzctl` (Paket `fritzctl-py`, import `fritzctl`)

```python
from fritzctl.avm.clients import fritz_client_context
async with fritz_client_context() as client:
    devices = await client.list_devices()              # list[Thermostat] (id=AIN, name, …)
    ain = next(d.id for d in devices if d.name == "Wohnzimmer")
    await client.set_temperature(ain, 22.0)            # 8–28 °C, rundet 0,5 °C, Safety-Engine
```

> Name→AIN-Auflösung macht der Adapter (Client matcht per AIN). `fritzctl` bringt eine
> **Safety-Engine** (Grenzen, ±5 °C-Delta, Cooldown, Audit-Log) mit → kostenlos genutzt.

### Rollos — `homekit` (Paket `homekit-py`, import `homekit`)

```python
from homekit import HomeKitClient, load_config
async with HomeKitClient(load_config()) as client:
    await client.set_position("cover.kueche", 50)      # 0–100 %  (CharacteristicWriteResult)
    state = await client.get_state("cover.kueche")     # aktuelle Position
```

> Entities/Aliase in `entities.toml` der homekit-Bibliothek; im Device-Registry referenziert.

**Connection-Management**: Adapter halten je Bibliothek einen (optional persistenten)
Client; Verbindungsfehler werden auf Domänenfehler gemappt (`DeviceUnavailableError` →
Alexa `ENDPOINT_UNREACHABLE`).

---

## 8. OAuth2 / Account Linking (Heimserver als IdP, via AWS gefrontet)

- FastAPI implementiert einen **OAuth2 Authorization Server**: `Authorization Code Grant
  + PKCE` (von Alexa unterstützt), eigene **Benutzerverwaltung** (Single-Household,
  wenige Nutzer; Passwort-Hash via `argon2`/`bcrypt`, Speicherung in SQLite/`aiosqlite`).
- Endpunkte: `/oauth/authorize` (Login-Seite + Consent + Code), `/oauth/token`
  (Access/Refresh), `/oauth/jwks` optional. Access-Token als signiertes JWT (kurzlebig),
  Refresh-Token rotierend.
- In der Alexa-Konsole werden als **stabile** Authorization-/Token-URIs die
  **API-Gateway-URLs** eingetragen; der OAuth-Proxy leitet zur S3-ermittelten
  Heimserver-Adresse weiter.
- Jede Smart-Home-Directive trägt das Bearer-Token; der Heimserver validiert es
  (Signatur, Ablauf, Scope) in einer Middleware (`TokenValidator`-Port).
- **4,5-s-Grenze** des Token-Endpoints: Proxy + conditional S3-GET + persistenter Tunnel
  + (optional) Provisioned Concurrency halten die Latenz niedrig.

---

## 9. AWS-Edge — Lambda-Proxy, S3-Beacon, Terraform

### Komponenten

- **Directive-Lambda** (`lambda/directive_proxy/`): Python; empfängt Smart-Home-Event,
  liest `endpoint.json` (conditional GET, ETag im Warm-Container-Cache), leitet JSON an
  `/alexa/directive` weiter, gibt Alexa-Response zurück. Diese Lambda-ARN wird im Skill
  als Default-Endpoint hinterlegt.
- **OAuth-Proxy** (`API Gateway HTTP API` + Lambda): Catch-all-Route für `/oauth/*`,
  transparente Weiterleitung (inkl. Cookies/302) an den Heimserver.
- **S3-Bucket** (`pantau-alexa-beacon`): Objekt `endpoint.json`
  `{ "base_url": "...", "updated_at": "...", "health": "ok" }`; **versioniert**,
  **SSE-verschlüsselt**, Bucket-Policy least-privilege.
- **IAM**: Lambda-Rolle `s3:GetObject` (nur dieses Objekt); Heimserver-IAM-User
  `s3:PutObject`.
- **Beacon-Updater** (auf dem Heimserver, `adapters/s3_beacon_publisher.py`): schreibt
  `endpoint.json` bei Start, periodisch und bei Tunnel-URL-Wechsel.

### Sicherheit (Schichten)

1. **Alexa→AWS**: Smart-Home-Lambda nur durch den Skill aufrufbar (Trust-Policy).
2. **AWS→Heim**: HTTPS-Tunnel **+ Shared-Secret-Header** (HMAC über Body+Timestamp,
   Replay-Schutz) → Heimserver weist Nicht-AWS-Traffic ab. Secret in **SSM Parameter
   Store/Secrets Manager**, nicht in `endpoint.json`.
3. **Pro Nutzer**: OAuth2-Bearer-Token bei jeder Directive validiert.
4. **S3**: verschlüsselt, versioniert, IAM-eingeschränkt, kein langlebiges Secret im Objekt.
5. **Geräte**: `fritzctl`-Safety-Engine, Rollos-Caution-Policy, Rate-Limiting.

### Terraform

Module: `s3_beacon`, `iam`, `lambda_directive`, `apigw_oauth`; Outputs u. a. die
**Directive-Lambda-ARN** und die **OAuth-URLs** für die Alexa-Skill-Konfiguration.

---

## 10. Bekannte Risiken & Annahmen

- **Smart-Home-NLU bestimmt die Phrasierung** (nicht autorseitig steuerbar). Die
  *Intention* aller Befehle ist umsetzbar; *exakte Sätze* müssen früh am echten
  deutschen Modell verifiziert werden:
  - „schalte ZDF ein" via PowerController-Gerät → **robust**.
  - „mach die Rollos halb runter" → „halb" über RangeController-Semantik; Fallback
    **„auf 50 Prozent"** empfehlen/testen.
  - „schalte den Ton ein" → Routing zu `Speaker.SetMute(false)` unsicher; Mitigation:
    zusätzlich optionales `Ton`-PowerController-Gerät als Synonym.
- **Mute-Drift** (Toggle-only) — dokumentiertes Restrisiko.
- **Harmony-Kanalwahl** hängt von konfiguriertem STB/TV, Ziffern-Timing und exaktem
  Aktivitätsnamen ab.
- **Latenz**: Cold-Start + Tunnel + S3-GET müssen < 8 s (Directive) bzw. < 4,5 s (Token)
  bleiben → persistenter Tunnel, conditional GET, ggf. Provisioned Concurrency.
- **Single-Household**-Scope (keine öffentliche Multi-Tenant-Zertifizierung); erweiterbar.
- **LAN-Annahme**: Heimserver erreicht FRITZ!Box, Harmony Hub und HomeKit-Accessoires.

---

## 11. Entwicklungsplan in Phasen

> Jede Phase ist eigenständig lauffähig/testbar und liefert einen demonstrierbaren Stand.

**Phase 0 — Projekt-Setup & Skeleton**
- `uv`-Projekt, `Taskfile.dist.yml`, `ruff`/`mypy`, `pydantic-settings`, CI.
- FastAPI-App mit `/health`; leeres Device-Registry-Schema; Mock-/Echo-Adapter.

**Phase 1 — Domäne, Device-Registry & Use-Cases (ohne Hardware)**
- Domänenmodell + Value Objects; Ports; `yaml_device_registry`.
- Use-Cases (`set_thermostat_temperature`, `set_blind_position`, `activate_channel`,
  `set_tv_mute`, `discover_devices`) gegen **Fake-Adapter**; Unit-Tests ≥ 80 %.

**Phase 2 — Reale Geräte-Adapter**
- `harmony_tv_adapter`, `fritz_thermostat_adapter`, `homekit_blind_adapter`.
- Integrationstests (gemockte Hubs: `pytest-httpserver` für FRITZ, Fakes für Harmony/
  HomeKit); Fehler-Mapping; Connection-Management.

**Phase 3 — Alexa Smart-Home-Integration (Directive-Layer)**
- `/alexa/directive`: Parsing, `router`, Capability-Handler
  (Power, Speaker, Thermostat, Range, **Discovery**); Response-Builder.
- Contract-Tests mit Beispiel-Directive-JSON → Response-Shape.

**Phase 4 — OAuth2 / Account Linking (IdP)**
- Authorization Server (`authorize`/`token`, PKCE), Login-Seite, Nutzer-Store,
  Token-Validierungs-Middleware; Flow-Tests.

**Phase 5 — AWS-Edge: Lambda-Proxy + S3-Beacon + Terraform**
- Directive-Lambda (conditional S3-GET + Forwarding), OAuth-Proxy (API Gateway),
  S3-Beacon-Bucket, IAM, Shared-Secret; **Beacon-Updater** im Heimserver.
- Terraform-Module + Outputs; `sam local`/Test-Events.

**Phase 6 — Skill-Konfiguration & E2E-Härtung**
- Skill-Manifest, Account-Linking-Konfig, Discovery; strukturierte Logs/Observability;
  Security-Härtung; E2E mit echter Alexa und realer Hardware.

---

## 12. Teststrategie & Verifikation

- **Unit** (`task test`, ≥ 80 %): Domäne & Use-Cases mit Fake-Adaptern.
- **Adapter-Integration**: gemockte Hubs (FRITZ via `pytest-httpserver`; Harmony/HomeKit-Fakes).
- **Alexa-Contract**: Beispiel-Directives (aus den offiziellen Docs) → Response-JSON prüfen.
- **OAuth-Flow**: Authorization-Code-Grant + PKCE simulieren; Token/Refresh.
- **Lokal E2E**: FastAPI starten, Beispiel-Directives an `/alexa/directive` mit Test-Token
  POSTen; Orchestrierung über Fakes, dann gegen reale Geräte.
- **AWS**: `terraform plan/apply` in Sandbox; Lambda mit Sample-Event; S3-conditional-GET
  + Forwarding; Beacon-Updater schreibt Objekt.
- **Abschluss**: Skill in Alexa-App aktivieren, Account-Linking, „Alexa, Geräte suchen",
  dann die realen Befehle.

---

## 13. Offene Punkte (nicht blockierend)

- Genaue Liste der Sender + Harmony-Kanalnummern (Config-Detail, später befüllbar).
- Tunnel-Technologie (cloudflared named/quick vs. ngrok) → bestimmt Beacon-Update-Trigger.
- „schalte ZDF aus" / „Ton"-Synonymgerät: finale Semantik beim E2E-Test festzurren.
