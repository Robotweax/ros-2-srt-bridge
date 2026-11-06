# Handoff: ROS-2-Brücke für Robotweax CONTROL/SENSOR

Datum: 2026-11-04 · Einstieg für einen Entwickler

## Auftrag und aktueller Zustand

Implementiere die in [ARCHITECTURE.md](ARCHITECTURE.md) beschriebene selektive
ROS-2-Brücke. Beginne mit M0 und arbeite bis zum simulierten ROS-Demonstrator M2;
danach folgen Netzwerkvergleich M3 und der Intrinsic-Adapter M4.

**Bei der ursprünglichen Übergabe waren ausschließlich diese beiden Planungsdokumente vorhanden.** Es wurden
keine Bridge-Pakete, Container, ROS-Launchfiles oder Intrinsic-Adapter erstellt.
Es wurden keine Builds, Netzwerkversuche oder Robotertests für dieses Vorhaben
ausgeführt. Die Architektur ist kein gemessener Leistungs- oder Sicherheitsnachweis.

Die Grundentscheidung ist getroffen: SENSOR für kleine aktuelle Zustände,
CONTROL für einzelne bestätigte Aufträge, zwei getrennte SRT-Verbindungen,
begrenzte Queues und ein dauerhaftes Auftragsjournal. Der erste Handler ändert
die Messrate eines Simulators. Eine weitere reine Videobrücke ist nicht das Ziel.

## 1. Vor Arbeitsbeginn lesen

1. Anwendbare lokale `AGENTS.md` und die vollständige [Architektur](ARCHITECTURE.md).
2. CONTROL-, SENSOR- und SESSIONAUTH-Verträge am unten genannten SRT-Pin.
3. Installierter öffentlicher C-API-Consumer und Testanleitung am selben Pin.
4. Vor M4 Intrinsic-README und ICON-/ROS-2-Tutorial an dessen eigenem Pin.

Dieser Ordner liegt als neues Teilprojekt im vorhandenen SRT-Checkout. Die
`HANDOFF.md` im Repository-Wurzelverzeichnis gehört zu einer anderen Aufgabe.
Vorhandene Änderungen, andere Teilprojekte und deren Übergaben erhalten.
Für die Implementierung kann dieser Ordner in ein eigenständiges Repository
übernommen werden; SRT bleibt eine installierte Abhängigkeit. Vor neuen Dateien
den tatsächlichen Arbeitsbaum prüfen. Keine vorhandenen Änderungen zurücksetzen.

## 2. Pins und Umgebung

| Zweck | Referenz |
| --- | --- |
| Lokaler Ausgangscheckout, nur Quellenkontext | SRT `09ceab33e1fc190472558fdb4d873f38b76fa320`, Version 0.2.8 |
| Zu qualifizierender SRT-Kandidat | `52be7c86ee1f303cbb0c8718c364217e4dd97a36`, CMake-Version 0.3.1 |
| Zu qualifizierender Intrinsic-Pin für M4 | `723c3ee01f155f7a8bb04e449d917fe8ac5784e9` |
| MVP-Betriebssystem | Ubuntu 24.04, Linux amd64 |
| MVP-ROS | Jazzy; beide Enden identische Typ-Paketversionen |
| Sprache / Crypto | C++20 / OpenSSL 3.x, GCM und SESSIONAUTH v2 |

Die neuere Quelle wird in einem separaten Dependency-Checkout bereitgestellt.
Nicht den bestehenden, anderweitig genutzten SRT-Arbeitsbaum auf den Pin resetten.
Ein geeigneter vorhandener Checkout kann wiederverwendet werden. Gleiche
Versionsnummern allein genügen nicht: Headers, Bibliothek, Flags und SHA müssen
zusammenpassen. Für den MVP kein `latest`-Container und kein ungeprüftes `main`.

In M0 `baselines/dependencies.json` anlegen: SRT-/Intrinsic-SHA, Container-Digest,
ROS-Pakete, RMW, Protobuf, SQLite, Compiler, OpenSSL, Architektur und Buildflags.
Intrinsic verlangt laut gelesenem README Lyrical; dessen Integration separat
bauen. Die Jazzy-Baseline ist keine Behauptung einer Intrinsic-Kompatibilität.

## 3. Erster ausführbarer Schritt: SRT-Consumer qualifizieren

In einem vorbereiteten Linux-Entwicklungscontainer sind CMake, C++20-Compiler,
OpenSSL-Entwicklungsdateien und Python erforderlich. ROS ist für die erste
Consumer-Prüfung noch nicht erforderlich. Die folgenden Befehle gelten für den
separaten **gepinnten SRT-Quellbaum**, nicht für diesen Dokumentationsordner.
Sie sind ein Startrezept und wurden im Rahmen dieser Übergabe nicht ausgeführt.

```sh
set -eu
# Im Dependency-Checkout; bei einem anderen HEAD zuerst dessen Herkunft klären.
test "$(git rev-parse HEAD)" = 52be7c86ee1f303cbb0c8718c364217e4dd97a36
git status --short

cmake -S . -B build-ros2-profile \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PWD/stage-ros2-profile" \
  -DROBOTWEAX_SRT_INSTALL_LAYOUT=namespaced \
  -DROBOTWEAX_SRT_BUILD_TESTS=ON \
  -DROBOTWEAX_SRT_BUILD_EXAMPLES=ON \
  -DROBOTWEAX_SRT_BUILD_BENCHMARKS=OFF \
  -DROBOTWEAX_SRT_BUILD_TOOLS=OFF \
  -DROBOTWEAX_SRT_CRYPTO_BACKEND=openssl \
  -DENABLE_AEAD_API_PREVIEW=ON \
  -DROBOTWEAX_SRT_ENABLE_EXPERIMENTAL_ACP1=OFF
cmake --build build-ros2-profile --parallel 2
ctest --test-dir build-ros2-profile -N
ctest --test-dir build-ros2-profile -L profile --output-on-failure
cmake --install build-ros2-profile
```

Vor dem gefilterten Lauf die tatsächliche Testinventur prüfen. Null ausgewählte
Tests sind ein Fehler. Das `profile`-Label ist ein Einstieg, kein vollständiger
SESSIONAUTH-/Reconnect-Nachweis. Ergänze die am Pin dokumentierten relevanten
Tests und protokolliere Namen, Zahl, Ergebnisse und ausgelassene Umgebungsfälle.
Eine verschmutzte Dependency-Quelle muss im Manifest sichtbar sein und ist
keine unveränderte Pin-Qualifikation.

Ein eigener kleiner installierter Consumer muss danach über die öffentliche
C-API zwei echte Sockets betreiben und für CONTROL **und** SENSOR prüfen:

- Explizites Profil, AES-GCM und SESSIONAUTH v2; kein optionales Downgrade.
- Payload 1.024 Byte bei IPv4/MSS 1500 und IPv6/MSS 1280, identische Einstellungen
  auf beiden Seiten; CONTROL zusätzlich bis zur 4.096-Byte-Bridge-Grenze.
- Falsches Profil, falsches Secret, fehlendes GCM und fehlende SESSIONAUTH ablehnen.
- Gültige Samples empfangen, große SENSOR-Nachricht ablehnen, epoll/Timeout und
  begrenztes Close korrekt behandeln.

Die vorhandenen Message-Demos sind hilfreich, ersetzen aber nicht diesen
Consumer mit der vollständigen gewählten Optionskombination. Linker-Anbindung:

```cmake
find_package(RobotweaxSRT CONFIG REQUIRED)
target_compile_features(profile_probe PRIVATE cxx_std_20)
target_link_libraries(profile_probe PRIVATE RobotweaxSRT::srt)
```

`profile_probe` ist ein in M0 anzulegender Target. Das explizite Versions-/SHA-
Gate erfolgt über den Dependency-Lock und das Buildmanifest; keine pauschale
0.2-ABI-Anforderung für eine 0.3-Bibliothek setzen. Keine privaten C++-Headers.

## 4. Geplante Projektstruktur

Diese Struktur anlegen; sie existiert zum Übergabezeitpunkt noch nicht:

```text
SRT-ROS2/
  ARCHITECTURE.md
  HANDOFF.md
  baselines/dependencies.json
  config/robot.yaml
  config/operator.yaml
  src/robotweax_srt_bridge_core/
  src/robotweax_srt_bridge_msgs/
  src/robotweax_srt_bridge/
  src/robotweax_srt_bridge_demo/
  tests/protocol/
  tests/integration/
  tests/network/
  tools/
  evidence/                  # nur bereinigte, bewusst veröffentlichbare Resultate
```

Build-/Install-/Logverzeichnisse, Credentials und rohe Laufartefakte lokal
ignorieren. Der Core muss auch ohne ROS mit CMake testbar sein. Für ROS
`ament_cmake`/colcon verwenden. Ein README mit tatsächlich funktionierenden
Build-/Startbefehlen entsteht mit M2, nicht mit erfundenen heutigen Launchnamen.

## 5. Implementierung in kleinen überprüfbaren Schritten

### M0 — Umgebung und Profilkombination

- Dependency-Lock und Container-Basis festhalten.
- Obigen Consumer und Negative Cases ausführen; tatsächliche Grenzen erfassen.
- ROS-Typhash-/CDR-Verfügbarkeit und Worst-Case-Größen beider MVP-Nachrichten
  prüfen. 96-Byte-Envelope plus CDR muss in 1.024 Byte passen.
- Abweichungen zuerst im Architekturvertrag klären; keine stillen Fallbacks.

### M1 — Core ohne ROS

- 96-Byte-Envelope, Management-Protobufs und kanonischen Routenmanifest mit
  Golden-Vektoren implementieren. Unbekannte Versionen/Flags/Routen ablehnen.
- CONTROL-Handshake, SENSOR-Binding, ClockMapper und Lifecycle bauen.
- SENSOR latest-only Queue, Sequenz-/Epochprüfung und Altersprüfung umsetzen.
- SQLite-Journal mit Admission-, Dispatch-, Ergebnis- und UNKNOWN-Semantik bauen.
- Abbruch nach Journal-Commit und vor/nach Handler-Aufruf gezielt injizieren.
  Erneuter Send desselben Auftrags darf nicht blind erneut ausführen.
- Getrennte Queues und gemeinsame Bandbreiten-Admission implementieren.

### M2 — ROS-Demonstrator

- Zwei Nodes in isolierten ROS-Domänen verbinden. Bridge-Core separat zum
  ROS-Executor betreiben; keine blockierenden SRT-Aufrufe in ROS-Callbacks.
- Imu und JointState typisiert mit Größen-/Schema-/QoS-Gates übertragen.
- ExecuteCommand/GetCommandStatus und den simulierten SetMeasurementRate-Handler
  anschließen. ID, Generation und Ergebnis an einem realen Zustandswechsel prüfen.
- Eine saubere Demo zeigt: aktuelle Samples, Messratenwechsel, bestätigtes
  Ergebnis, 2-s-Unterbrechung, Wiederanlauf ohne alte Samples oder doppelte Wirkung.
- Tatsächliche ROS-Build-, Launch- und Testbefehle dokumentieren. Ein Transport-
  ACK oder ein einzelner erfolgreicher Send genügt nicht als Abnahme.

### M3 — Netzqualifikation und Vergleich

- N0–N5 aus der Architektur ausführen, Erstfehler und Seeds bewahren.
- Direkten DDS-Verkehr zwischen den Enden ausschließen; einen separaten,
  vergleichbar konfigurierten DDS-Baseline-Lauf ermöglichen.
- Ergebnisse auf Anwendungsebene messen, mit Raten, Altersabdeckung, CPU/RSS,
  Overhead, CONTROL-Ergebniszeiten und Reconnect. Kein pauschales „schneller“
  ohne die zugrunde liegenden Bedingungen und Daten.

### M4 — Intrinsic

- Tatsächliche Lyrical-/Runtime-Pins und erlaubte Zustands-/Auftrags-APIs erfassen.
- Core erneut gegen die passende Toolchain bauen, beide Gegenstellen kompatibel.
- Zuerst Zustandsbeobachtung, dann einen simulierten Diagnoseauftrag integrieren.
- Auftrags-ID/-Status-Abbildung und Unsicherheitsfälle dokumentieren. ICON/HAL-
  Shared Memory und Echtzeitthreads bleiben außerhalb des Netzwerkadapters.

## 6. Tests, die nicht fehlen dürfen

| Fall | Erwartung |
| --- | --- |
| Gleiche Request-ID, anderer Payload | `CONFLICT`, kein Handler-Aufruf. |
| Reconnect nach Ergebnis-Commit vor Zustellung | QUERY liefert ursprüngliches Ergebnis, keine neue Ausführung. |
| Absturz nach Dispatch vor Ergebnis-Commit | `UNKNOWN`, kein automatischer Retry. |
| Neustart mit angenommenem, noch nicht dispatchtem Auftrag | `REJECTED/CONTEXT_LOST`, keine späte Ausführung aus altem Kontext. |
| Frist läuft in Queue ab | `EXPIRED` vor Dispatch. |
| Unbekannte Clock-Abbildung / Sprung / Neustart | Kein frischer Sample oder Auftrag vor erfolgreicher Neuqualifikation. |
| Alter Sample nach neuerem Sample durch FEC | Gezählt und verworfen; publizierte Sequenz steigt streng. |
| SENSOR-Übergröße / Typhash-Mismatch | Expliziter Fehler; kein Abschneiden oder Profilwechsel. |
| Volle Queues / volles Journal / langsamer Peer | Begrenzter Speicher, beobachtbares BUSY bzw. SENSOR-Ersetzung. |
| Datenträger voll / Fehler beim Ergebnis-Commit | Kein unbelegtes SUCCEEDED; ursprüngliche ID bleibt rekonstruierbar bzw. UNKNOWN. |
| CONTROL gestört, SENSOR noch erreichbar | Alte Sitzung invalidieren; keine unkontrollierte Weiterpublikation. |
| Shutdown während Reconnect oder vollem Sendpuffer | Höchstens fünf Sekunden im Lifecycle-Test, kein 180-s-Linger, keine Callback-Nutzung freigegebenen Speichers. |

M0 qualifiziert zusätzlich die genaue Transport-/Crypto-Kombination; M1 testet
Wire und Zustandsautomaten deterministisch. M2 verwendet echte SRT-Sockets und
ROS-Nodes. M3 verwendet reale Kernel-Netzbeeinträchtigung in isolierter Umgebung.
Mocks oder Loopback erfüllen die jeweils nachfolgenden Stufen nicht.

## 7. Nächste Übergabe und Definition of Done

### Ursprünglicher Übernahmestand 2026-11-04

- Repository für M0–M3: https://github.com/Robotweax/ros-2-srt-bridge.
- Separates Repository für den späteren M4-Adapter:
  https://github.com/Robotweax/intrinsic-core-srt-integration.
- Beide GitHub-Repositories waren erreichbar und ohne Branches. Lokales
  Bootstrap in diesem Ordner; kein Commit oder Push bei der Übernahme.
- Architektur und Handoff vollständig gelesen. README, lokale Ignore-Regeln
  und `baselines/dependencies.json` als **unqualifiziertes Kandidatenmanifest**
  ergänzt. Unbekannte Digests/Versionen bleiben ausdrücklich `null`.
- Host: Darwin arm64. `docker version --format '{{json .Server}}'` scheiterte
  im Kontext `desktop-linux`: Docker-Socket fehlt, kein Server verfügbar.
  Docker Desktop ist installiert. Kein Linux-Build und keine Profilprobe gestartet.
- M0 ist offen. Nächster Ausführungsschritt: Linux-amd64-Umgebung bereitstellen,
  Image-Digest pinnen und separaten SRT-Kandidaten qualifizieren. Erst danach M1.
- Intrinsic bleibt M4 im eigenen Repository. Bestehender übergeordneter
  SRT-Arbeitsbaum und dessen Änderungen bleiben erhalten.

### Verifizierte Übernahme 2026-11-04

- Tatsächlich vorhanden waren nur Architektur, Handoff und README; die zuvor
  erwähnten lokalen Git-/Ignore-/Baseline-Dateien fehlten. Jetzt eigenständiges
  Repository mit Branch `main` und dem Bridge-Remote eingerichtet; kein Commit/Push.
- Kandidatenmanifest und Ignore-Regeln ergänzt. Beide Zielrepositories erneut
  erreichbar; Intrinsic bleibt M4.
- Docker-Daemon jetzt verfügbar. Ubuntu 24.04 Linux amd64 im isolierten Container
  erfolgreich unter Emulation gestartet. Image-Referenz und lokale Plattform-ID
  im Kandidatenmanifest erfasst; noch kein qualifiziertes Entwicklungsimage.
- Übergeordneter SRT-HEAD bei Prüfung: `49e615aa6996e2c5a366a426d09bfe3ca2d24c2c`.
  Keine Änderung am bestehenden SRT-Arbeitsbaum.
- M0 weiterhin offen: separaten Pin-Checkout und Entwicklungsimage bereitstellen,
  Verträge am Pin lesen, SRT bauen/installieren und kombinierte Profilprobe erstellen.
- Befehle und tatsächliche Ergebnisse: [Übernahme-Evidenz](evidence/2026-11-04-takeover.md).

### Entwicklung M0 und erster M1-Baustein — 2026-11-04

- M0 lokal bestanden: sauberer SRT-Pin separat unter `.deps/srt`, namespaced
  installiertes statisches Paket, OpenSSL/GCM/SESSIONAUTH v2, experimentelle
  ACP1-/Controller-/Filteroptionen aus. Reale Linux-amd64-Sockets unter Emulation.
- `python3 tools/run_m0.py --build-image --srt-source ..` erstellt die Umgebung,
  validiert den Pin und hält pro Versuch Logs, Inventur, Paketstände und JUnit fest.
  Voraussetzung: das im README gepinnte ROS-Image zuvor herunterladen.
- Eigene öffentliche C-API-Probe: 40/40 Fälle bestanden (IPv4/MSS 1500,
  IPv6/MSS 1280, beide Profile, GCM+SESSIONAUTH, negative Gegenstellen,
  Größen-/TTL-Grenzen, epoll und Close bei gefülltem Sendpuffer).
- Upstream: vier GCM-Profilpartitionen, eine SESSIONAUTH-Admission-Partition und
  15 fokussierte SESSIONAUTH-Fälle bestanden. Nicht die gesamte Upstream-Suite.
- Jazzy-Typhash und CDR-Roundtrip geprüft: Imu 380 Byte; JointState mit sechs
  Gelenken, 64-Byte-Namen und vollständigen numerischen Arrays 684 Byte.
  `frame_id` jeweils 64 Byte. Beide passen mit 96-Byte-Envelope in 1.024 Byte.
- Kandidatenmanifest zur lokal qualifizierten M0-Baseline ergänzt. Image-Digests,
  tatsächliche Pakete, Archive-Hash und Buffer-Readbacks sind festgehalten.
- M1 begonnen: unabhängiger C++20-Wire-Codec, initiales Management-Protobuf-Schema,
  Golden-Vektor und 20.000 deterministische Mutationen (22.576 Assertions).
  GNU/Linux Debug, ASan+UBSan sowie eigenständiger macOS-arm64-Build bestanden.
- M1 ist **nicht fertig**: Management-Runtime-Validierung, kanonischer Routenhash,
  ClockMapper, Sessions/Binding/Reconnect, begrenzte Queues/Scheduler und
  SQLite-Journal fehlen. Noch keine ROS-Nodes oder Simulatorbefehle.
- Nachweise und Reproduktion: [M0/M1-Evidenz](evidence/m0-2026-11-04/README.md).
  Quelldateien sind noch uncommitted; kein Push, kein Intrinsic-Code.

### M1-Fortsetzung: Management und ClockMapper — 2026-11-04

- Management-Codec mit generiertem Protobuf und begrenzter Vorprüfung implementiert:
  maximal 512 Byte, bekannte/undoppelte Felder, Wire-Typen, feste Hash-/Epochlängen,
  UTF-8 ohne Steuerzeichen, Peer-ID bis 64 Byte und feste MVP-Limits.
- HELLO/WELCOME/READY/BIND/TIME_PROBE/TIME_REPLY werden typisiert validiert.
  Das ist noch keine Gegenstellenautorisierung oder Sitzung. COMMAND/STATUS/QUERY
  und ERROR-Payloads bleiben dem Journal-/Session-Baustein vorbehalten.
- ClockMapper implementiert asymmetrieunabhängige Offset-/Altersintervalle mit
  expliziten Drift-/Timestampfehlergrenzen, konservativer Rundung und Overflow-Gates.
  Unbekannte/zu breite/abgelaufene Modelle liefern keinen gültigen Alterswert.
  Epoch-/Domänenfehler, Rücksprung und Widerspruch sperren bis Reset.
- Protokollpräzisierung: Beide SRT-Endpunkte initiieren eigene Zeitprobes; t1/t4
  sind lokal, t2/t3 remote. Protobuf-Feldnummern unverändert, Rollenbezeichnungen
  auf Initiator/Responder korrigiert. Korrelation offener Probes ist noch anzuschließen.
- Deterministische Tests: 5.000 Drift-Szenarien mit Folgeproben und alten Ereignissen,
  Integergrenzen, Resets, Frischebudgets sowie 20.000 Management-Mutationen.
  Linux Debug und ASan+UBSan bestehen; Wire/Clock auch auf macOS arm64 geprüft.
- Reproduktion: `python3 tools/run_m1.py` mit dem M0-Image. Native Builds ohne
  Protobuf verwenden `-DBUILD_MANAGEMENT_CODEC=OFF`; der volle Core benötigt
  Protobuf ab 3.21. README und Architektur entsprechend aktualisiert.
- Nachweise: [M1-Evidenz](evidence/m1-clock-management-2026-11-04/README.md).
  M1 ist weiter offen: Routenmanifest/SHA, Session-/Probe-Korrelation, SRT-I/O,
  Reconnect, begrenzte Queues/Scheduler und SQLite-Journal. Kein Commit/Push.

### M1-Fortsetzung: Routenmanifest und Sitzungen — 2026-11-04

- Kanonischer RWRM-v1-Manifest mit SHA-256, sortierten IDs, Typ-/Hash-/QoS-/
  Richtungs-/Größen-/Budgetgrenzen und Enabled-Freigabe implementiert. Unabhängiger
  Python/struct/hashlib-Goldenvektor liegt unter `tests/protocol/routes-v1.*`.
- Session-Core implementiert HELLO/WELCOME, konfigurierte Peer-/Manifest-/Limit-
  Gates, gegenseitiges READY, beidseitig korrelierte Zeitprobes, SENSOR-Binding,
  Sequenz-/Epoch-/Domain-/Altersgates und Close-/Flush-Aktionen bei CONTROL-Verlust.
  Er besitzt noch keine eigenen Sockets oder Worker und ist nicht kopier-/bewegbar.
- Erforderliche Protokollpräzisierung: frische 16-Byte-Binding-ID je SENSOR-Socket,
  auf CONTROL exakt bestätigt. Feld 3 in BIND und READY; alte Prototypen ohne ID
  werden abgelehnt. Lokale Socketgenerationen schützen gegen alte Close-/Daten-
  Ereignisse. Source-Sequenzen laufen über Rebind und CONTROL-Reconnect weiter.
- Echte installierte SRT-Sockets testen IPv4 und IPv6, GCM+SESSIONAUTH v2,
  beidseitige READY-/Clock-Probes, verspätete alte Binding-Acks, SENSOR-Rebind,
  tatsächlichen CONTROL-Verlust, neuen Sitzungsaufbau und Abweisung alter Frames.
  Nutzdaten sind vier synthetische Byte, keine ROS-IMU und kein M2-Demonstrator.
- Kernverträge: fünf Tests in Debug und ASan+UBSan. Root-Regression: 47/47 Tests.
  Native Wire/Clock-Minimalspur erneut auf macOS arm64 geprüft.
- Reproduktion: `python3 tools/run_m1.py --native` nach M0; der Runner prüft den
  installierten SRT-Archive-Hash und führt die vollständige Root-Matrix aus.
- [Neue Evidenz](evidence/m1-sessions-2026-11-04/README.md) enthält Ergebnisse,
  Quellfingerprints, offene Grenzen und erhaltene Fehlläufe. Kein Commit/Push.
- M1 ist weiterhin offen: bounded Queues/Bandbreiten-Admission, Reconnectkampagne
  mit Jitter, Produktions-I/O-Owner und SQLite-Auftragsjournal/Crash-Semantik.

### M1-Fortsetzung: Queues, Bandbreite und Reconnectplan — 2026-11-04

- Feste CONTROL-Queue (64/256 KiB, COMMAND maximal 56/224 KiB), acht latest-only
  SENSOR-Slots und ein BIND-Retry-Slot implementiert. Eigene Packetkopien,
  BUSY/Drop-Zähler, Deadline-/Raten-/Sequenzgates, round-robin und Generationsgates.
- Session-Close/-Flush-Aktionen leeren die passenden Queues; wartende COMMAND-IDs
  werden für spätere Journalauflösung zurückgegeben. Kein ACCEPTED/Erfolg aus Queue-OK.
- Globales/SENSOR-Tokenbudget mit CONTROL-Reserve und einmaliger Reserve-/Commit-/
  Refund-Semantik implementiert. Overheadschätzer ist keine harte Wire-Garantie.
- Reconnectplan implementiert 250 ms–5 s mit geklemmtem ±20-%-Jitter, 3-s-Versuche,
  exakte 60-s-Kampagnen, eindeutige Versuche, Cancel, Deadlinegates und explizite
  Reaktivierung nach permanenten Fehlern. Keine blockierenden Sleeps im Plan.
- Native IPv4/IPv6-Harness nutzt Queues und Budget jetzt für Management/SENSOR,
  wendet Session-Invalidierungsaktionen an und verwirft absichtlich gealterte
  Samples vor SRT. Tatsächlich publizierte synthetische Sequenzen sind 1, 3, 4;
  die wartende 2 läuft lokal ab. Keine ROS-Nodes oder Auftragsausführung.
- Acht Kernverträge in Debug und ASan+UBSan bestanden, vollständige Root-Matrix
  50/50. Enthalten: 50.000 Queue-Ereignisse, zehn Sekunden synthetische Überlast,
  1.000 deterministische Reconnectkampagnen. Minimale native Host-Spur: vier Tests.
- Reproduktion bleibt `python3 tools/run_m1.py --native` nach M0.
  [Neue Evidenz](evidence/m1-queues-reconnect-2026-11-04/README.md) bewahrt Logs,
  Quellhashes, Ergebnisse und Fehlläufe. Kein Commit/Push.
- Noch offen: produktiver Socket-/epoll-Owner, bounded thread-safe Callback-
  Ingress und Worker-Shutdown; SQLite-Journal mit durable Admission/Dispatch/
  Ergebnis und Crash-/Disk-Faults. M1 bleibt unvollständig, M2 folgt erst danach.

### M1-Fortsetzung: dauerhaftes Auftragsjournal — 2026-11-04

- `RobotweaxBridge::journal`: getrennte, exklusiv geöffnete SQLite-WAL-Journale
  mit FULL-Sync, Peer-/Rollenbindung und festen Datensätzen. Sender persistiert
  LOCAL_QUEUED vor Send, Empfänger ACCEPTED vor Antwort und DISPATCHING vor Handler.
- Typisierter SetMeasurementRate-/STATUS-Codec mit stabilen Enumwerten,
  Descriptor-Schemahash und kanonischem Payloadhash; QUERY bleibt leer.
  Session prüft Richtung, Session/Epoch/Domain, Route, Sequenz und Startbudget.
- Neustart: ACCEPTED wird REJECTED/CONTEXT_LOST, DISPATCHING wird UNKNOWN;
  Sender ohne Endbeleg wird UNKNOWN und fragt zuerst ab. Kein automatischer Resend.
  Duplikate verlängern keine Frist, Konflikte ändern keinen vorhandenen Auftrag.
- VFS begrenzt Hauptdatei/WAL/SHM/Rollback auf zusammen 64 MiB logische Längen,
  10.000 Einträge; reservierter Ergebnisraum, keine Evictions. Write-/Sync-Fehler
  sperren auch Reads bis zur Wiederöffnung und Recovery. SQLite-Abhängigkeit 3.45+.
- Fünf SIGKILL-Grenzen prüfen vor/nach Admission, Dispatch und Ergebnis-Commit.
  Kapazitäts-, echte SQLite-VFS-FULL- und injizierte Write-/Sync-Fehler bestanden.
  Keine physische Stromausfall- oder Datenträgerqualifikation.
- Native IPv4/IPv6-Harness: ein Messratenwechsel, Ergebnisnachricht absichtlich
  verloren, CONTROL-Reconnect, QUERY nach 5-s-Budgetablauf, persistiertes SUCCEEDED
  ohne erneute Wirkung. Beide Endpunkte laufen synchron in einem Harness-Prozess;
  Crashtests verwenden separate Kindprozesse. Noch keine ROS-/Geräteanbindung.
- `python3 tools/run_m1.py --native`: Debug 12/12, ASan+UBSan 12/12,
  vollständiger installierter SRT-Build 54/54. [Evidenz](evidence/m1-journal-2026-11-04/README.md)
  enthält Logs, Befehle, Quellhashes und erhaltenen ersten Compile-Fehllauf.
  Kein Commit/Push; Intrinsic unverändert.
- M1 bleibt offen: Produktions-Socket-/epoll-Owner, begrenzter Callback-Ingress,
  beaufsichtigter Journal-/Handler-Worker mit asynchronem Session-/Frische-Fencing,
  ERROR-Wire-Abbildung und integrierter Shutdown-Nachweis binnen fünf Sekunden.

### M1-Fortsetzung: threaded Transport-Owner — 2026-11-05

- `RobotweaxBridge::transport` als eigener installierter-SRT-Target. Ein Thread
  besitzt Sockets, epoll, Session, Queues, Budget und getrennte Reconnectpläne.
  Numerische IPv4/IPv6-Endpunkte, qualifizierte Profile/Buffer/Crypto, nonblocking,
  Linger null; Listener-Sessions und Caller-Binding-IDs werden zufällig erzeugt.
- Feste Try-Lock-Mailboxes: CONTROL 64 FIFO, SENSOR acht latest-only Routenplätze.
  Externe Payloads werden kopiert, ursprünglicher Ingress bleibt erhalten.
  CONTROL-Readiness pausiert vor voller Empfangsmailbox; keine stillen Drops.
- Session-/Kanalgenerationen verwerfen veraltete Arbeit und Workerresultate.
  Automatische Probes starten während Synchronisierung und erneuern Frische;
  unabhängige zufällige Jitterseeds verhindern identische Retryfolgen.
- Native IPv4/IPv6-Tests betreiben zwei echte Owner ohne manuelle Session-/SRT-
  Fortschaltung. SENSOR, QUERY/STATUS, 80 Queries gegen 64er-Mailbox, Ablauf beim
  Poll, >5 s Clock-Erneuerung, kompletter Reconnect, alte Tokens, permanente
  Peerablehnung und vier konkurrierende Produzenten sind abgedeckt.
- Stop bei Verkehr und ausstehenden Verbindungen liegt in den Tests unter fünf
  Sekunden. Noch kein Nachweis für blockierte Journal-/Handler-Worker.
- `python3 tools/run_m1.py --native`: Debug 12/12, ASan+UBSan 12/12,
  Root 56/56 sowie Transport unter ASan+UBSan 2/2 bestanden.
  [Evidenz](evidence/m1-transport-2026-11-05/README.md) enthält die tatsächlichen
  Ergebnisse und bewahrt Compile-/Handshake-Fehlversuche. Kein Commit/Push.
- M1 bleibt offen: begrenzter Journal-/Handler-Worker mit durable Send-Tickets,
  Freigabe vor/nach Dispatch-Commit, ERROR/BUSY/CONFLICT-Wire-Abbildung und
  vollständiger Lifecycle-Qualifikation. Transport empfängt COMMAND, führt aber
  nichts aus; eine COMMAND-Submit-API gibt es ohne diesen Vertrag noch nicht.

### M1-Fortsetzung: Journal-Prozess und durable Send-Tickets — 2026-11-05

- Linux/glibc-Target `RobotweaxBridge::worker` und `robotweax-journal-worker`.
  posix_spawn nach laufenden Transportthreads, private feste 2.048-Byte-IPC-Frames,
  maximal 64 ausstehende Requests. Ein externer Koordinator pollt Antworten;
  Netzwerk-Owner und Parent führen kein SQLite-I/O aus.
- Child benutzt seinen aktuellen Monotonic-Zeitpunkt bei Operationsstart; keine
  vom Parent eingefrorene Zeit kann IPC-Wartezeit aus dem Budget entfernen.
- Nur neu committed LOCAL_QUEUED erzeugt ein einmaliges Sender-Ticket.
  Duplikate, GET, Empfängeradmission, Ablauf und Write/Sync-Fehler tun dies nicht.
  Transport prüft Peer/Epoch/Route/Budget/Kontext, reserviert acht Ingressplätze
  für QUERY/STATUS und verwirft bekannte tote/abgelaufene Tickets vor Send.
- 64 Owner-Check-Slots liefern asynchrone Session-/Frischebeobachtungen vor/nach
  Dispatch-Commit. Sie sind ausdrücklich keine Handler-Startfreigabe.
- Worker-Stop: sofortiger Ticketwiderruf, maximal 2 s Grace, dann SIGKILL;
  einmalige 4-s-Joinfrist. shutdown_timeout behauptet keinen vollständigen Join.
  Tests mit SIGSTOP an fünf Commitgrenzen prüfen Recovery und Stop unter 5 s.
- Native IPv4/IPv6-Integration mit zwei Ownern und getrennten Sender-/Empfänger-
  Prozessen: committed COMMAND-Ticket, dauerhafte ACCEPTED-Rückantwort, begrenzte
  Checks, Ablauf nach Dispatch-Commit, Sessionverlust und UNKNOWN nach Recovery.
  Pausierter Journalprozess blockiert QUERY-Verkehr nicht. Kein neuer Handlerstart.
- Debug 13/13, ASan+UBSan 13/13, Root 59/59, Transport-/Worker-Sanitizer 4/4
  und minimaler macOS-Build 4/4 bestanden.
  Gates und Logs: [Evidenz](evidence/m1-worker-2026-11-05/README.md).
  Reproduktion `python3 tools/run_m1.py --native`; kein Commit/Push, Intrinsic unverändert.
- M1 bleibt offen: automatischer Koordinator samt Sessionverlust-/Query-first-
  Ablauf, final gegen Widerruf linearisierte Startfreigabe, beaufsichtigter Handler,
  ERROR/BUSY/CONFLICT-Wire-Abbildung und vollständiger Bridge-Lifecycle.

### M1-Fortsetzung: automatischer Endpoint und Start-Fences — 2026-11-05

- `RobotweaxBridge::endpoint`: eigener Koordinatorthread mit 64 Inputs, 64 Events,
  64 verfolgten IDs und serieller Command-Pipeline. Durable Admission/Sends,
  ACCEPTED, DISPATCHING, Endstatus, Kontextverlust und Query-first laufen automatisch.
- Frisch committed DISPATCHING mintet ein einmaliges DispatchTicket. Owner koppelt
  es an aktuelle Session-/Frischeprüfung; Child konsumiert einen Shared-Memory-
  Fence per CAS. Widerruf vor Start verhindert Wirkung; RUNNING darf abschließen.
- Sealed memfd mit 64 Slots, 64-Bit-lock-free Atomics, Slotgenerationen, ID-/Hash-
  Bindung, konservativen Deadlines. IPC intern v2, Netzwerkvertrag unverändert.
  Worker-Stop widerruft auch Grants; fehlgeschlagene RUNNING-Slots werden nicht recycelt.
- Grant-Deadline begrenzt durch Command-Budget UND Clock-Qualifikationsgrenze
  (Probe-Alter/Driftbreite). Der Child prüft sie unabhängig vom I/O-Tick; spätere
  Clockprobes verlängern keinen vorhandenen Grant.
- CONTROL-Kontext bindet SID/CONTROL-Generation; SENSOR bindet zusätzlich seine
  Generation. SENSOR-Wechsel allein verwirft keine Steuerarbeit. COMMAND bleibt
  unabhängig von SENSOR-Binding verfügbar.
- Explizit aktivierter simulierter Rate-Handler im Child, absolute Rate mit
  Generationstest und Result-Commit. Zustand initial 200 Hz/Generation 0, nach
  Workerrestart flüchtig zurückgesetzt; Journal bleibt historische Wahrheit.
- Supervisor-/Coordinator-Timeout und gemeinsame Stopsequenz schließen Admission,
  widerrufen ungestartete Arbeit und reapen den Child. Tests unter 5 s, auch mit
  SIGSTOP-Handler, voller Callback-Mailbox und vier Produzenten. Offene lokale
  Benachrichtigungen werden ohne erfundenen Geräte-Endstatus ausgeliefert.
- Debug 14/14, ASan+UBSan 14/14, Root 64/64 und kombinierte Native-Sanitizer 8/8
  bestanden. Neue Race-, Grant-, Endpoint-, Restart-/Query-first- und Shutdown-Evidenz:
  [Koordination](evidence/m1-coordination-2026-11-05/README.md).
  Reproduktion `python3 tools/run_m1.py --native`; kein Commit/Push.
- M1 bleibt offen: allgemeine ERROR/BUSY/CONFLICT/NOT_FOUND-Wire-Antworten und
  abschließende Acceptance-Evidenz. M2 ROS-Node/CDR/Simulator und M4 Intrinsic unverändert später.

### M1-Abschluss: ERROR-Vertrag und installiertes SDK — 2026-11-05

- Separates `errors_v1.proto`: Code, COMMAND-/QUERY-Referenzsequenz, begrenzter
  Backoff. Bestehender Rate-Command-Descriptorhash bleibt unverändert. ERROR ist
  kein Journalstatus und kein Beweis für Ausführung oder Nichtausführung.
- Session/Route/ID/Direction/Epoch/Domain/Replays werden geprüft; Owner korreliert
  gegen 64 Recent-Send-ID/Route-Einträge. ERROR beantwortet kein ERROR.
- Receiver liefert BUSY/CAPACITY/CONFLICT/NOT_FOUND; ausgewählte Frische-/Body-
  Gates liefern Diagnostik. Speicherfehler bleiben fail-closed ohne Antwortgarantie.
- Sender behält Journalwahrheit, meldet peer_error ohne Entry und pausiert Query
  für diese ID/Sitzung. Explizite Query oder Reconnect setzt Reconciliation fort.
  Kein blindes Resend; Endstatus gewinnt gegen späte Fehler. Fremdes STORAGE
  vergiftet nicht das eigene Journal. Vor Admission ist ERROR kein ID-Tombstone.
- Install-/Exportregeln für RobotweaxBridge-CMake-Targets, Worker und Header.
  Voller Linux-SDK-Consumer nach Prefix-Relocation mit echten Sessions/Command/
  Status/Duplikatsperre; Required-Component-Negativfall und ROS/zweiter-SRT-Linkcheck.
  Standalone Minimal-Core samt installiertem Consumer auf macOS arm64 ohne SRT,
  Protobuf/OpenSSL/SQLite/ROS geprüft.
- Debug 15/15, ASan+UBSan 15/15, Root 67/67, Native-Sanitizer 10/10 sowie
  Linux-SDK-Relocation/Consumer/Component-Negativfall bestanden. Host-Minimal-Core
  4/4 plus installierter relocatable Consumer ebenfalls bestanden.
  [Abschluss-Evidenz](evidence/m1-errors-sdk-2026-11-05/README.md) dokumentiert
  tatsächliche Gate-Ergebnisse, unveränderte Providerpins und Install-Artefakte.
  Reproduktion `python3 tools/run_m1.py --native`; kein Commit/Push.
- M1 qualifiziert den ROS-freien Core auf der dokumentierten Linux-amd64-Baseline.
  Kein physischer Geräte-/Netzwerkleistungsnachweis, keine allgemeine Handlerplattform.
  Simulierte Gerätegeneration bleibt nach Workerrestart flüchtig; UNKNOWN wird nie
  automatisch neu ausgeführt. M2/M3/M4 folgen gemäß Architektur.

Der Entwickler ergänzt nach jeder Stufe diesen Abschnitt um tatsächlichen
Commit, Umgebung, ausgeführte Befehle, Ergebnisse, Evidenzpfade, offene Fehler
und den nächsten konkreten Schritt. Bestehende Fehlläufe bleiben erhalten.

M2 ist fertig, wenn ein frischer Entwickler mit den dokumentierten Befehlen
den vollständigen Simulatorlauf reproduzieren kann, alle relevanten Gates
bestanden sind und unbekannte Auftragsergebnisse korrekt sichtbar bleiben.
M3 ist fertig mit einer auswertbaren Vergleichsmatrix, auch wenn diese keinen
SRT-Leistungsvorteil zeigt. M4 erfordert einen tatsächlichen Intrinsic-Lauf.

**Nächster Schritt nach M1 (in M2 umgesetzt):** M2-ROS-Jazzy-Demonstrator auf dem installierten
SDK aufbauen: zwei Nodes in isolierten ROS-Domänen, Imu/JointState mit CDR-/Typ-
Hash-/Größen-/QoS-Gates, ExecuteCommand/GetCommandStatus und echter simulierter
Messratenwechsel samt Generation und Ergebnisbeleg. Lifecycle/Callbacks bleiben
vom SRT-/Journal-I/O getrennt. Intrinsic bleibt M4 im separaten Repository.


### M2 abgeschlossen — ROS Jazzy, 2026-11-05

- Drei ROS-Pakete unter `ros2/`: feste Messages/Services, typisierter Adapter und
  getrennter Sensor-/Messraten-Simulator. colcon baut gegen das installierte SDK.
- Der ROS-freie SDK-Child-Einstieg `RobotweaxBridge::worker_runtime` erlaubt einen
  explizit aktivierten externen Rate-Backend. Der ROS-Worker verwendet den lokalen
  Geräte-Service nach atomarer Startfreigabe. Parent/Child müssen zusammen neu
  gebaut werden: privates IPC jetzt 3, unverändert Wire 1.
- Größen-/UTF-8-/Dimensions-/Typ-Hash-/CDR-Gates und echte lokale QoS-Prüfung
  (Best Effort/Volatile/KeepLast(1)). Fast-RTPS veröffentlicht History-Depth nicht
  im Discovery-Graph; die lokale tatsächliche RMW-QoS wird separat geprüft.
  Leere CDR-Vektoren erfordern getrennte Writer-/gemeldete Größenberechnung;
  der gesamte Serialisierungspuffer wird vorher genullt.
- Publikation prüft direkt vor ROS-Publish Session, Sensor-Generation,
  Publication-Epoch, Clock-Qualifikation und Deadline. ROS-Callbacks führen keine
  SRT-/SQLite-I/O aus; Netzwerk, Koordinator und Geräte-/Journal-Worker sind getrennt.
- Abschlusslauf `.local/m2/20261105T102439657240Z` mit
  `python3 tools/run_m2.py`; vorgelagerter `--build-image`-Lauf ebenfalls bestanden: drei Pakete gebaut, sechs Codec-GTests
  bestanden (colcon zählt zusätzlich den CTest-Wrapper), reale SRT-Verbindung
  zwischen zwei Container-IP-Adressen, DDS lokal und Domänen 41/42 getrennt.
- 626 Imu/350 JointState remote, null direkter DDS-Bypass, ungültige Inputs
  verworfen. Bestätigter Wechsel 200→100 Hz; Generation-Konflikt ohne Wirkung;
  verlorene Antwort nach Wechsel auf 75 Hz ergibt UNKNOWN/effect_uncertain.
  Worker-SIGKILL nach tatsächlichem Wechsel auf 50 Hz/Generation 3: Neustart mit
  neuem SID, QUERY liefert UNKNOWN/context_lost, keine Wiederholung. Vier COMMAND-
  Frames, drei Effekte trotz wiederholter Execute-Aufrufe.
- 2,0011 s Bridge-Unterbrechung; keine alte/doppelte Nutzlast nach Wiederanlauf.
  Saubere Stopps maximal 0,3198 s, Child-Prozesse geerntet. Temporäre Container,
  Netzwerk und Passphrase entfernt; andere Netze unverändert.
- SDK-Regressionslauf `.local/m1/20261105T100528666291Z`: 15 Debug, 15 ASan/UBSan,
  67 native, 10 native ASan/UBSan und relocateter Consumer bestanden. Alle
  archivierten Quellhashes stimmen mit dem aktuellen Code überein.
- Abnahme: `baselines/m2-acceptance.json`,
  `evidence/m2-ros-jazzy-2026-11-05/ACCEPTANCE.md`. Frühere Versuche inklusive
  Fehlläufen bleiben im dortigen `attempts/`-Verzeichnis. M1-Abnahme unverändert.
- Kein Commit/Push: neues Repository weiterhin ohne Commit, Dateien lokal
  untracked. Parent-SRT und Intrinsic-Repository nicht verändert.

**Nächster Schritt:** M3 nach gesonderter Fortsetzung: N0–N5 in isolierter
Kernel-Netzumgebung, Anwendungsalter/Clock-Abdeckung, CPU/RSS/Overhead und
CONTROL-Latenzen erfassen und eine vergleichbare DDS-Baseline bauen. Keine
SRT-Überlegenheit aus M2 ableiten. Der Simulator hält Gerätehistorie nur flüchtig;
physische Geräte, Power-Cut-Qualifikation, lokale DDS-Authentisierung und M4
Intrinsic sind nicht abgenommen. Die ursprüngliche Übernahme bis M2 ist erfüllt.

### M3 begonnen — isolierter Netz-Harness, 2026-11-05

- PR #1 auf ausdrücklichen Nutzerwunsch gemergt: Main-Commit
  `32c53b27839182ec45c448694c60fe1691466118`. Weiterentwicklung auf
  `dev/m3-network-qualification`.
- `tools/run_m3.py` baut ein eigenes SDK-/ROS-Präfix, erzeugt ein internes
  Docker-Netz und neue Endpunkt-Container mit NET_ADMIN; keine Host-qdisc.
  N0/N1/N2/N4/N5 werden als SRT-Entwicklungsläufe unterstützt. Kernel-Readbacks
  prüfen Seeds, Queuegrenzen und Rate. Alte `tc`-Version ohne Seed ersetzt durch
  hash-geprüftes iproute2 6.17.0 im gepinnten ROS-Basisimage.
- ROS-Diagnose ergänzt begrenzte 1-ms-Histogramme konservativer Altersobergrenzen,
  Maximum und separate Sample-Admission-Zähler für Stale/Unknown-Age. Clock-
  Intervallbreite ist konfigurierbar (M2 weiterhin 50 ms, M3 explizit 200 ms bei
  unverändertem 250-ms-SENSOR-Budget). Wire 1 und privates IPC 3 unverändert.
- Stetiger Test hält Sollrate 200 Hz; absolute 200-Hz-Aufträge alle 2 s ändern
  die Generation. UNKNOWN pausiert weitere Aufträge statt eine Generation zu
  raten. Nicht abgeschlossene Aufträge werden getrennt von Latenzperzentilen
  gezählt. Ressourcenbeobachter und rotierte, auf Vollständigkeit geprüfte
  Ethernet-PCAPs zählen DATA/Parität/SRT-Controls getrennt. Kein DDS-Bypass.
- Fünfminütiges N0: `.local/m3/20261105T130451724258Z`, 300,009 s, 150 bestätigte
  Aufträge und genau 150 Effekte; 27.569 Imu/13.709 JointState beobachtet.
  Altersobergrenze IMU p99 15 ms/Max 17,62 ms, Gelenke p99 28 ms/Max 32,65 ms.
  Gleichzeitig fehlen 26.742 IMU im beobachteten Quellzähler-Span von 54.311.
  Capture vor/nach WAN passt; Senke meldet keine Rejections/Ersetzungen. Verlust
  vor WAN (lokaler DDS-Ingress bzw. Latest-only-/Send-Pump-Kadenz) muss vor
  Durchsatzqualifikation genauer zugeordnet werden. 200 Hz sind konfiguriert,
  kein belegtes Erreichen der Sollrate in dieser emulierten Umgebung.
- N1/N2/N4/N5-Smokes bestanden, nur Seedbasis 1701. N4 ist derzeit mittiges
  Kernel-Outage, keine Admission-/Dispatch-/Ergebnis-Commit-Barriere. N5-Prototyp
  mit 256-Paket-Kindqueue hatte Stale/Unknown-Drops und einen offenen Auftrag;
  korrigierte 16-Paket-Kindqueue bestätigte alle acht Aufträge. TBF allein begrenzt
  einen ersetzten Netem-Child nicht auf die angegebene Bytezahl. Paritäts-/DATA-
  Frame-Byte-Verhältnis tatsächlich etwa 0,60 bei kleinen Messages, nicht aus
  einem nominellen 4:1-Paketschema als 0,25 angenommen.
- SDK-Regressionslauf `.local/m1/20261105T124908573510Z`: 15 Debug, 15 ASan/UBSan,
  67 native, 10 native ASan/UBSan und installierter Consumer bestanden.
  Originale M2-Demo `.local/m2/20261105T131111749554Z` ebenfalls bestanden.
  Sieben ROS-GTests plus Wrapper, sechs Python-Harness-Tests bestanden.
- Evidenz/Fehlversuche: `evidence/m3-network-harness-2026-11-05/`; Plan und
  tatsächlich verwendetes Image: `baselines/m3-plan.json`. Roh-PCAPs/JSONL und
  Journale bleiben ignoriert lokal; Artefakthashes liegen in der Evidenz.

**M3 bleibt offen:** N0-Lücken zuordnen und Quellrate/Zeitschnitt/Diagnose-Tail
vollständig zählen; DDS Best Effort und Reliable mit demselben Journalvertrag
implementieren; N3 DATA-/FEC-selektive deterministische Verluste und N4-Barrieren
bauen; vollständige Dauer-/Seed-Matrix ausführen. Keine Leistungsüberlegenheit
behaupten. M4 unverändert später; Parent-SRT nicht verändert.

### M3 N0-Sensorlücken: Hauptursache behoben — 2026-11-05

- 30-s-Attribution mit Quell-Diagnose: 5.461 IMU-/1.481 Joint-Ingress-Callbacks,
  nur zwei BUSY-Abgaben, aber 2.633 Ersetzungen in der Sender-Mailbox. Im
  beobachteten IMU-Span fehlen 2.650 Samples. Der 10-ms-Owner-Wait reduziert
  eine 200-Hz-Quelle im Latest-only-Slot auf ungefähr 100 Hz.
- Native 200-Hz-Regression reproduziert den alten Fehler (100 admitted,
  48 delivered). Aktive Caller fordern jetzt 1 ms Epoll-Timeout an, Listener und
  nicht aktive Caller weiter 10 ms (keine Scheduler-Laufzeitgarantie). Kein Busy-Spin, keine Queue-Vergrößerung,
  keine gelockerten Clock-/Session-/Bandbreiten-/250-ms-Altersgates. Der gepinnte
  SRT-Provider pollt System-Wake-Deskriptoren selbst nur alle 10 ms; der Parent-
  SRT-Code und das qualifizierte Archiv wurden nicht verändert.
- Neue ROS-Diagnose: Ingress pro Route und BUSY/obsolete-Abgaben. Der M3-Observer
  bewahrt Quell-/Senken-/Simulator-Snapshots vor Stop. `gap_attribution` zeigt die
  Stufen, ohne unterschiedlich getimte kumulative Zähler exakt zu bilanzieren.
- Neuer Fünfminutenlauf `.local/m3/20261105T140142459719Z` bestanden:
  IMU 52.793 erhalten, 741/53.534 im beobachteten Quellspan fehlen (1,38% statt
  49,24%); Joint 29/14.576 fehlen (0,20% statt 6,27%). 150 Aufträge bestätigt,
  genau 150 Effekte. Quelle zuletzt 48 BUSY und vier Mailbox-Ersetzungen;
  Senke ohne Admission-Rejection/Stale/Unknown/Ersetzung. Restlücken bleiben offen.
- CPU-Beobachtung auf derselben emulierten Linux-amd64-Baseline: Quelle etwa
  17,35→22,39%, Senke 7,75→10,87% eines VM-Kerns bei erheblich mehr zugestellten
  Daten. Keine kontrollierte Hardware-/DDS-Leistungsvergleichsaussage ableiten.
- SDK-Vollregression `.local/m1/20261105T135638164666Z`: 15 Debug, 15 ASan/UBSan,
  67 native, 10 native ASan/UBSan und Consumer bestanden. Erster San-Lauf blieb
  an einer alten BUSY-Testannahme hängen, nicht an einem Sanitizer-Speicherfehler.
  Reconnect-Negativtests wiederholen nur BUSY und verlangen den ersten anderen
  Rückgabewert OBSOLETE; QUEUED alter Arbeit bleibt Fehler.
- Originale M2-Demo `.local/m2/20261105T135416286568Z` bestanden. Sieben ROS- und
  sieben Python-Tests bestanden. N5-Smoke unter höherer angebotener Last: sechs
  von sieben Aufträgen vor Cutoff bestätigt, sieben Effekte, ein Ergebnis explizit
  offen/zensoriert; keine falsche Erfolgsaussage und kein blindes Replay.
- Evidenz inklusive fehlgeschlagener Regression und Vorher/Nachher-Runs:
  `evidence/m3-sensor-cadence-2026-11-05/`. Source-/Artefakthashes erhalten;
  neue vollständige N0-/SDK-/M2-Manifeste stimmen mit aktuellem Code überein.

**Weiter offen:** verbleibende Rate-/Outbound-Queue-Verluste, exakter Diagnose-
Tail und erreichte Quellrate; danach DDS-Baseline mit gleichem Journalvertrag,
N3-Selektor, N4-Auftragsphasen und volle Seed-/Dauermatrix. M3 bleibt in Arbeit;
Wire 1, privates IPC 3, M4 unverändert. Draft-PR #2 wird mit diesem Fix fortgeführt.

### M3 exakte Sensorfenster und Quellphase — 2026-11-05

- Sensor-Stufenzähler, Pending-Slots und Owner-Epoch per lokalem read-only
  `/bridge/get_metrics`; `/robot/set_publishing` pausiert mit Callback-Fence.
  Frische SRT-Session vor Messbeginn entfernt Warmup-SAMPLE-/FEC-Historie.
  Stabile leere Checkpoints, unveränderte Epochen und sechs Nullresiduen sind
  Pflicht. Fenster-Histogramme stimmen mit Publikationspopulation überein.
- Sender wartet bis zu nahen Pacing-Terminen unter 1 ms, ohne Busy-Spin. Simulator
  erhält Zeitphase, vermeidet Catch-up-Bursts und Phasenreset bei gleicher Rate.
  Strict pacing, Latest-only, Queue-/250-ms-Grenzen und Kryptografie unverändert.
- N0 `.local/m3/20261105T153616391199Z`: 300,097 s, Ist 199,959/49,997 Hz,
  75.011 produziert, 72.372 beobachtet; 2.639 fehlen, alle zugeordnet: 2.542
  Outbound-Ersetzungen, 91 Admission, drei DDS-Ingress, je eine Ingress- und
  Empfangsersetzung sowie ein DDS-Observer-Verlust. Kein SRT-Akzeptanz/Empfang-Gap,
  aber kein Beweis für physisch verlustfreies WAN. 150 bestätigt/150 Effekte.
- N4-Smoke `20261105T154538668977Z`: sieben bestätigt/ sieben Effekte. N5-Smoke
  `20261105T154456488682Z`: zwei bestätigt/zwei Effekte, ein Auftrag offen;
  Bilanz-Pass ist keine Auftragsabnahme. Ergebnisse werden bis acht Sekunden nach
  Cutoff abgefragt und pro Zeile markiert; gepoolte Latenzen enthalten Drain.
- SDK `.local/m1/20261105T145359704756Z`: 15/15/67/10 Tests und Consumer bestanden.
  M2 `.local/m2/20261105T154053788107Z` bestanden; sieben Codec-/vier Schedule-
  GTests, elf Python-Tests. Finale Source-Hashes geprüft. Ein vorheriger M2-Lauf
  scheiterte an Image-Pin-Preflight; spätere Inspects und unveränderter Retry
  bestanden. Ursache unbekannt, Assertion nicht gelockert; Evidenz erhalten.
- Evidenz `evidence/m3-window-accounting-2026-11-05/` bewahrt finale Manifeste,
  Entwicklungsläufe, Tests, Artefakthashes und Grenzen. CPU/Wire umfasst weiterhin
  Gesamtbeobachtung; N0 überlappte teilweise mit M2 in derselben VM. Keine
  kontrollierte CPU- oder Überlegenheitsaussage. Frühere Marker-Spans bei ~178 Hz
  sind nicht direkt mit dem neuen 200-Hz-Fenster vergleichbar.

**Nächster Schritt:** DDS Best Effort + Reliable mit gleichem Journalvertrag und
Messfenster implementieren; CPU/Wire zeitlich angleichen, N3-DATA/FEC-Selektor,
N4-Auftragsphasen und volle Seed-/Dauermatrix. Outbound-Ersetzungen bei echter
200-Hz-Last und N5-Auftragsabschluss weiter qualifizieren. M3 bleibt in Arbeit,
Draft-PR #2 bleibt offen. Parent-SRT, Wire 1, privates IPC 3 und M4 unverändert.

### M3 DDS-Sensorpfad implementiert — 2026-11-05

- `tools/run_m3_dds.py` und separater DDS-Driver betreiben direkte typisierte
  Best-Effort/Volatile/KeepLast(1)-Sensoren in internem Docker-Netz, Domäne 60,
  explizite statische Peers. Multicast allein lieferte in diesem Lab keine
  Discovery; Timeout ist erhalten. Kein SRT-Prozess, keine Host-qdisc/Ports.
- Source-Fences und stabile Observer-Snapshots bilanzieren tatsächlich erzeugte,
  empfangene, akzeptierte, stale/invalid/clock-rejected Samples. Fehlend vor
  Callback umfasst Middleware/Kernel/Netz/History, keinen isolierten WAN-Verlust.
  Discovery prüft Best Effort/Volatile; History/Depth kann UNKNOWN sein.
- N0 30 s `.local/m3-dds/20261105T161851009485Z`: 6.023 IMU + 1.507 Joints erzeugt
  und alle empfangen, Ist 199,891/50,014 Hz. Gemeldeter Mindest-Offset-Schritt
  1.281.694 ns disqualifiziert Altersmetriken; 3.152 folgende Samples am Clock-
  Gate verworfen. Ursache nicht belegt. Count-Pass ist keine Altersabnahme.
- N1-Smoke `.local/m3-dds/20261105T161943936259Z`: 3.022/756 erzeugt, 2.079/746
  empfangen/akzeptiert; 943/10 vor Callback fehlen. Lokale Shared-VM-Alterschecks
  bestanden, aber weder konservative SRT-Clock-Grenze noch gleicher Zeitursprung:
  DDS nutzt Simulator-Header, SRT Bridge-Ingress. Kein Leistungsvergleich.
- Ungeklammerte Clock-Reads hatten Scheduling als Sprung fehlklassifiziert;
  geklammerte Intervalle trennen Read-Unsicherheit, Drift und gemeldete Schritte.
  Ein Fünfminutenversuch scheiterte am ursprünglichen harten Clock-Gate und
  bewahrte keine finalen Zähler: daraus keine Sample-Zahlen ableiten. Der finale
  Runner bewahrt Zähler und begrenzte Sprungdiagnose, markiert Alter separat.
- DDS-Capture zählt IPv4-Fragment-Frames separat ohne RTPS-Payload-Zuordnung.
  SRT bleibt standardmäßig strikt; Reparse des alten vollen N0 ergibt identisch
  156.443 Frames je Endpunkt und identische Summary-Felder. Beide finalen DDS-
  Captures vollständig und ohne Kernel-Capture-Drops. 19 Python-Tests bestanden;
  installierter Driver/Helper bytegleich und Import/Help bestanden. Keine SDK-
  oder ROS-C++-Änderung, außer Installation der neuen Python-Tools.
- Evidenz: `evidence/m3-dds-sensors-2026-11-05/`. Finale Läufe wiederverwenden
  Simulator-Binary explizit, Hash erhalten; alle 124 Inventar-Sourcehashes passen.
  Fehlversuche und Rohcapture-Hashes erhalten, PCAPs bleiben ignoriert lokal.

**Weiter:** vollständig journalisierten Reliable-DDS-Auftragskoordinator bauen,
mit dauerhaftem Sender-Admission vor Send, frischer Session/Clock-Autorisierung
vor DISPATCHING/Handler-Start, identischem Journal/Handler, QUERY/UNKNOWN und
keinem Replay alter Absicht nach Reconnect/Crash. Direkter Apply-Service-Aufruf
ist kein Ersatz. Sensor-Runner sendet keine Aufträge und nutzt keine DDS-Krypto;
Command-/Security-/Age-/CPU-/Wire-Vergleich und voller Seed-/Dauerlauf fehlen.
N2/N5 sind im neuen Runner implementiert, hier noch nicht ausgeführt; N3 und N4-
Auftragsphasen weiterhin offen. PR #2 bleibt Draft, M3 nicht abgenommen.

### M3 Reliable-DDS-Auftragsjournal implementiert — 2026-11-05

- `dds_command_node` + `tools/run_m3_dds_commands.py`: feste Reliable/Volatile/
  KeepLast(64)-Frames, pro Endpunkt eigener Journal-Thread, Route 100, Budget
  5.000 ms. SDK-`CommandJournal` unverändert; `RosRateBackend` in geteilten Header
  verschoben und identisch vom bisherigen SRT-Worker und DDS genutzt.
- Neue Sender-Admission vor einzigem COMMAND; Duplikat/Recovery nur GET/QUERY.
  Empfänger committet Admission/DISPATCHING, prüft vor atomarem Start unter dem
  Session-Mutex Live-Lease, Epochen, Deadline. Kein Disk-/Handler-Aufruf unter
  diesem Mutex. Bereits beanspruchter Start kann bei späterer Revokation Effekte
  haben; fehlendes Resultat bleibt UNKNOWN. SRT-Ticket-/IPC-Fences unverändert.
- Common-VM-only: lokaler Boot-/Time-Namespace-Digest muss auf beiden Seiten
  passen. Acknowledged Session aus Prozess-/Link-Nonces, Sequenz-/Frischechecks,
  1,5-s-Lease; Ablauf ändert lokale Link-Nonce. 64 retired Peer-Nonces verhindern
  Rollback; Kapazität erschöpft → Fail-Closed. Keine DDS-Krypto-/Cross-Host-
  Authentisierungs-/Clock-Abnahme. Keine vorgetäuschten SRT-Security-Flags.
- Final `.local/m3-dds-commands/20261105T175009991487Z` bestanden: ID 1 100 Hz
  SUCCEEDED, Duplikat ohne neuen Send/Effekt, andere Payload desselben IDs meldet
  lokalen Konflikt. ID 2 75 Hz bewirkt Effekt, verspätete Antwort → UNKNOWN.
  ID 3 50 Hz bewirkt Effekt, Receiver SIGKILL und Sender SIGKILL vor Reconciliation;
  nach Reopen QUERY → UNKNOWN/context_lost, kein altes COMMAND. Nach expliziter
  Device-Reconciliation und Reset der Fault-Verzögerung neue ID 4 200 Hz SUCCEEDED.
  Insgesamt vier Absichten/vier Effekte; drei COMMANDs vor Sender-Crash, danach
  ein QUERY und nur das neue COMMAND ID 4. Zwei UNKNOWN haben kein gültiges Resultat.
- Read-only SQLite quick_check nach Cleanup auf beiden Journals bestanden:
  identische vier IDs, Payload-Hashes, Revision 3, Status-/Result-Felder. Captures
  vollständig: Robot 5.107 / Operator 5.081 Frames, keine unzugeordneten Frames
  oder Kernel-Capture-Drops. Sender meldet nach Restart einen Callback-Admission-
  Drop, Typ unbekannt; nicht als WAN-Verlust oder garantiertes Admission auslegen.
  Handler/Journal können ausgehende HELLOs verzögern und konservativ Lease drehen.
- Sieben neue Session-GTests + sieben Codec + vier Schedule bestanden (18 echte,
  21 inklusive Wrapper). 19 Python-Tests bestanden. Originales vollständiges M2
  `.local/m2/20261105T175011079038Z` nach Handler-Extraktion bestanden. Finale
  DDS-/M2-Source-Inventare 132/81 Dateien passen. SDK-Source/Wire 1/IPC 3 unverändert.
- Evidenz `evidence/m3-dds-commands-2026-11-05/` inklusive Journal-Inspektion,
  Artefakthashes und früherem Fault-Test, der UNKNOWN korrekt lieferte, weil die
  Testverzögerung für neue Arbeit noch aktiv war. Test setzt sie jetzt explizit
  zurück. Roh-Journale/PCAPs bleiben lokal ignoriert. Auftragsresultate stammen
  aus DDS-Status; Dateien tragen Teststeuerung und Geräte-Diagnosen.

**Nächster Schritt:** diesen journalisierten Koordinator mit stetiger 200/50-Hz-
DDS-Sensorlast und absoluten 200-Hz-Absichten alle 2 s zusammenführen. Danach
N0/N1/N2/N4/N5 mit denselben Fenstern, CPU-/Wire-Scope und Ergebnis-Drain wie SRT
qualifizieren; Clock-Ursprung/-Grenzen und Kryptografie vergleichbar machen.
N3-DATA/FEC-Selektor, N4-Admission/Dispatch/Result-Commit-Barrieren und volle
Seed-/Dauermatrix offen. M3 bleibt in Arbeit, PR #2 Draft; keine M4-Änderung.

### M3 stetige DDS-Sensor-/Auftragslast zusammengeführt — 2026-11-05

- `tools/run_m3_dds.py --commands`: Quelle 200/50 Hz, absolute 200-Hz-Aufträge
  alle 2 s. Ein Pending, keine Catch-up-Bursts, UNKNOWN/Pending blockiert weitere
  Absichten. Freie Slots fragen Execute trotz NOT_READY-Diagnose an; explizite
  Non-Admissions werden gezählt. Sensor-only ohne Flag bleibt erhalten.
- Vor Beginn beide Journal-Koordinatoren bereit, keine Auftragshistorie/Effekte.
  Sensor-Fences unverändert; Cutoff stoppt neue Aufträge, Ergebnisbeobachtung
  maximal bis Cutoff+8 s, danach eingefroren. Separate letzte Device-Fence für
  Effekte/Generation; Sensorzähler dürfen nicht mehr steigen. Owner-Epochen
  müssen gleich bleiben. Auftragsdiagnosen behalten 100-ms-Snapshot-Scope.
- Erster langer Lauf `20261105T181542377101Z`: nur zwei bestätigt/ein offener
  Auftrag, Sender/Empfänger mit 30/18 Callback-Drops. Code konnte schon empfangene
  Reliable-Frames bei Try-Lock-Contention verlieren. Kurze Validierungs-/Kopier-
  abschnitte serialisieren jetzt, ohne Disk/Handler/Netz unter Mutex. Inbox bleibt
  64; voller Puffer zählt Drop. Lokale Service-Admission bleibt Try-Lock/BUSY.
  Neuer Parallelproduzenten-Test prüft 64 Aufnahmen ohne Contention-Verlust.
  Keine Queue-, Lease-, Clock- oder Deadline-Lockerung und kein Intent-Replay.
- N1-Capture deckte gültiges 4-Byte-Endfragment auf: es besitzt keinen UDP-Header.
  Parser prüft IP-/Fragment-Länge und MF-Ausrichtung, verlangt UDP-Header nur wo
  vorhanden. Regression getestet; alte SRT-N0-Summaries weiter identisch. Alte
  Manifeste unverändert; separate Reanalyse dokumentiert den Fix.
- Finales N0 `.local/m3-dds-combined/20261105T183834692545Z`: 300,127 s, Ist
  199,978/50,002 Hz, 75.026 erzeugt/75.025 empfangen, ein IMU fehlt vor Callback.
  150/150 bestätigt und 150 Effekte, keine Inbox-Drops. Beide geschlossenen
  Journale quick_check ok, dieselben 150 Payload-Hashes/Revisionen 3/SUCCEEDED,
  Rate 200 und Generationen 1–150. Alter nach Clock-Schritt unqualifiziert:
  54.313 IMU/13.580 Joint-Callbacks clock-rejected; empfangene Callbacks, kein
  isoliertes Netzverlustmaß.
- Finale Smokes, jeweils 15 s und Seed 1701:
  N1 `20261105T184311488522Z`: 7/8 bestätigt, eine Non-Admission, sieben Effekte.
  N2 `20261105T184014775290Z`: 1/2 bestätigt, ein Pending, sechs Slots blockiert.
  N4 `20261105T184051558249Z`: 4/5 bestätigt, ein Pending, drei Slots blockiert;
  mittiges Kernel-Outage, keine präzisen Auftragsphasen-Barrieren.
  N5 `20261105T184126432851Z`: fehlgeschlagen nach 45 s Sender-Ready-Wartezeit im
  Cold-Start unter dem unveränderten 512-kbit/128K-Konkurrenz-Profil; kein Messfenster.
  Nicht als vollständige Auftrags-/M3-Abnahme auslegen, keine Nullwerte erfinden.
- Korrigierter C++-Build `20261105T182432483577Z`: 19 echte ROS-GTests, 22 mit
  Wrappern bestanden. 27 Python-Tests bestanden. Finale Sensor-only-Regresssion
  `.local/m3-dds/20261105T184339550820Z` und DDS-Fault-Acceptance
  `.local/m3-dds-commands/20261105T184405437225Z` bestanden. Finale Läufe verwenden
  dieses aufgezeichnete Binary wieder; alle 136 Sourcehashes passen, installierte
  Python-Dateien bytegleich. SDK/SRT-Source und Wire 1/IPC 3 unverändert.
- Evidenz `evidence/m3-dds-combined-2026-11-05/`: auch Fehlversuche, Parser-Reanalyse,
  Journalprüfung und Rohartefakthashes. N0 lief zeitweise parallel zu Entwicklungs-
  fixtures; keine kontrollierte CPU-/Hardware-Aussage, keine Überlegenheit.

**Weiter:** DDS-Ready-/Completion-Grenzen unter N1/N2/N5 untersuchen, ohne die
Sicherheitsgates oder No-Replay zu lockern. Altersursprung/-Qualifikation und
Kryptografie vergleichbar machen; CPU/Wire an dieselben Fenster koppeln. Danach
volle Seed-/Dauermatrix, N3-DATA/FEC-Selektor, N4-Admission/Dispatch/Result-Commit-
Barrieren. M3 bleibt in Arbeit, PR #2 Draft, Intrinsic/M4 unverändert.


### M3 DDS-Readiness und Lifecycle nachgebessert — 2026-11-05

- Nach Lease-Ablauf fehlte die erneute Zielsuche: beide Enden konnten HELLOs an
  pensionierte Peer-Links senden. Jetzt zunächst leeres Discovery-Ziel, dann
  weiterhin gegenseitige Bestätigung der aktuellen Nonces; alte Links bleiben
  retired. Simultane und einseitige Abläufe durch deterministische GTests geprüft.
- HELLO auf separater BestEffort/Volatile/KeepLast(1)-Spur mit eigenem 100-ms-
  Thread. Reliable/Volatile/KeepLast(64) für COMMAND/QUERY/STATUS/ERROR bleibt.
  Strenge Replay-Cursor pro Spur verhindern, dass neue HELLOs ältere gültige
  Controls verwerfen. Tatsächliche lokale QoS beim Start geprüft. Beide DDS-
  Enden gemeinsam neu bauen (neues owner_ready-Feld), SDK-Wire 1/IPC 3 gleich.
- Journal-/ROS-Handler-Eligibility ist Teil der Bereitschaft und wird im HELLO
  gemeldet; lokale Start-Prüfung bleibt. Diagnosen für Matches, HELLOs, Ablehnung,
  Lease-Abläufe und Epochen ergänzt. Kein Lock über Journal, Handler oder Netz.
- Shutdown-Repeats fanden einen intermittierenden >5-s-Timeout. Pre-Shutdown
  stoppt/ joint Threads vor Middleware-Shutdown; verschachtelter Handler-Context
  gehört jetzt der Node und wird außerhalb des gejointen Workers zerstört.
  Drei aufeinanderfolgende finale Fault-Läufe bestehen inklusive 5-s-Gate,
  Duplikat/Konflikt, verzögerter Antwort UNKNOWN, Receiver-/Sender-SIGKILL,
  Reopen/QUERY ohne altes COMMAND und neuer Absicht nach Device-Reconciliation.
  Beim blockierten Handler bleiben beide Lease-Zähler 0 → 0. Vorherige Timeouts
  bleiben Evidenz; kein Debugger-Stack beweist einen bestimmten Middleware-Lock.
- Testharness wartet auf kumulative Diagnosen vor Send-Assertions. Atomare
  Phase-Dateien tolerieren kurz fehlende Datei beim Lesen, kein exists/open-Race;
  kaputtes JSON bleibt Fehler. Phasen-ID steigt im Speicher. Dateien sind kein
  Ersatz für DDS-Auftragsresultate. 23 echte ROS-GTests/26 mit Wrappern und
  30 Python-Tests bestanden; vollständiges originales M2 erneut gebaut/bestanden.
- Finaler N1-Smoke 8/8 bestätigt. N2 (60 s) 17/18 bestätigt, ein offen/17 Effekte,
  zwölf Slots blockiert; beide Enden am Ende ready, keine Lease-Abläufe. N4-Smoke
  4/5 bestätigt/ein offen/vier Effekte, beide Enden nach je einem Lease-Ablauf
  wieder ready. Kein Replay der offenen Absichten. Früherer N2-Entwicklungslauf
  schaffte 28/28; variable Completion bleibt sichtbar, keine Vollabnahme.
- Explizites `--startup control-first`: Sensorquelle bleibt bis Ready aus,
  Nullproduktion geprüft, dann Warmup und gleiche Fences. Impairment und N5-
  Konkurrent schon aktiv. Finaler N5-Smoke zwei bestätigt/zwei Effekte, sechs
  Slots blockiert. Kein Nachweis für Beitritt bei bereits laufender Telemetrie.
  Default bleibt simultaneous. `--dds-profile udp1200` ist zweite explizite
  Variante; keine IP-Fragmente im Entwicklungscapture, N5-Start trotzdem gescheitert.
  Default bleibt system. Keine Queue-/Lease-/Frische-/Deadline-Lockerung.
- Evidenz `evidence/m3-dds-readiness-2026-11-05/`: finale Manifeste/Sourceprüfung,
  vorherige Fehlversuche, gemischte Completion, Paketfeld-Analyse, Rohartefakthashes.
  Roh-PCAPs/Journale lokal; ältere Evidenz unverändert. Zwei M2-Aufrufe scheiterten
  vor Build am unveränderten Image-ID-Gate; Read-only-Rechecks passen, unveränderte
  vollständige Wiederholungen bestanden. Ursache unbewiesen, Gate bleibt streng.

- Finales fünfminütiges N0 `20261105T201220121826Z`: 150/150 bestätigt, 150 Effekte,
  Ist 199,976/50,002 Hz; 75.025 produziert/75.022 empfangen, drei IMU vor Callback
  fehlen. Lokale Alterschecks bestanden, keine Cross-Host-Aussage. Beide Journale
  quick_check ok, identische 150 SUCCEEDED/Revision-3-Records und Generationen
  1–150. Inbox-Drops/Lease-Abläufe jeweils null. Finale elf Manifeste (inklusive
  N5-Fehler) passen: DDS 138/M2 86 Source-Dateien, installierte Python-Dateien
  bytegleich. Binary-Build `201016201590Z`, Fault-Repeats `201144179119Z` und
  `201202123026Z`; M2 `201220118978Z`. Keine kontrollierte CPU-/Hardware-Messung.

**Weiter:** offene DDS-Aufträge trotz bestehender Readiness unter N2 und belasteten
simultaneous-N5-Start untersuchen; keine Absichten blind erneut senden. Clock-/
Crypto-Gleichheit und gemeinsame CPU-/Wire-Fenster qualifizieren, danach volle
Seed-/Dauermatrix, N3-DATA/FEC-Selektor und N4-Auftragsphasen-Barrieren. M3 bleibt
in Arbeit, PR #2 Draft, SRT/SDK unverändert, Intrinsic/M4 weiterhin unberührt.


### M3 offene DDS-Aufträge auf Paketfrische zurückgeführt — 2026-11-05

- Frühere N2-Captures/geschlossene Journale read-only analysiert: ID 18 lokal
  LOCAL_QUEUED/Revision 0, kein Empfängereintrag; erster beobachteter COMMAND
  relativ zum lokalen HELLO-Zeitoffset etwa 2,13 s alt, danach NOT_FOUND-ERRORs.
  Das isoliert keinen Netzanteil. Originale Evidenz und Rohartefakthashes erhalten.
- Neue Session-Validierungsdiagnosen mit erstem Ablehnungsgrund: accepted,
  session, peer, clock, sequence, invalid_time, stale. Letzter stale COMMAND
  erhält ID/Send-/Ingresszeit. accepted ist weder Journal-Admission noch Start.
  Receipt-gematchte NOT_FOUND-Antworten und maximale Reliable-Publish-Aufrufdauer
  getrennt gezählt. Feste Counter/Snapshots, kein unbegrenztes Event-Logging.
- Workload speichert letzte lokale Status-/Fehlerbeobachtung auch beim offenen
  Intent. found bezieht sich auf lokales Journal; NOT_FOUND kann vom Peer gecacht
  sein. budget_elapsed meint 5 s seit lokalem Client-Aufruf, keine autoritative
  Empfänger-Expiration. Timeout/NOT_FOUND erzeugen keinen Terminalzustand und
  erlauben kein Replay. Der einzelne offene Auftrag blockiert weiter neue Slots.
- Drei finale N2-Probes je 60 s: Seed 1701 2/3 bestätigt, ein offen/zwei Effekte;
  Seed 2903 28/28 bestätigt/28 Effekte; Seed 4211 11/12 bestätigt, ein offen/elf
  Effekte. Bei 1701/4211 je ein COMMAND direkt am Callback mit 2.212,649 bzw.
  2.474,505 ms Alter verworfen, noch vor der 5-s-Startdeadline. Stale-ID entspricht
  offenem Intent; kein Empfängereintrag, später 247/171 gematchte NOT_FOUNDs.
  Beide Enden bleiben ready. Maximale Sender-Publish-Aufrufe unter 1 ms; kein
  Beleg für blockierenden Publish als Ursache dieser beiden Fälle. Middleware-
  Repair/Queue/Transport/Executor noch nicht einzeln isoliert. Kein 600-s-Gate.
- N0 30 s: 15/15 bestätigt/15 Effekte, keine stale Commands. N4-Smoke 4/5/ein
  offen, beide Enden wieder ready; Kontextablehnungen während Outage, kein
  stale-COMMAND-Inkrement. N5 simultaneous erneut vor Fenster gescheitert:
  beide Enden ohne Matches/empfangene HELLOs. Discovery bleibt offen.
- Vollständige DDS-Fault-Acceptance nach Build `20261105T203710218043Z` bestanden,
  einschließlich Duplikat/Konflikt, verlorener Antwort UNKNOWN, Receiver-/Sender-
  SIGKILL, Reopen/QUERY ohne Intent-Replay, neuer Absicht nach Reconciliation und
  5-s-Shutdown. 24 echte ROS-GTests/27 mit Wrappern und 32 Python-Tests bestanden.
  Deterministischer Test prüft jeden Rejection-Grund, exakte Stale-Grenze, lebende
  HELLOs und unveränderten Replay-Cursor nach Ablehnung. Beobachtungstests erzeugen
  keinen Terminal-/Result-/Nichtausführungsnachweis aus NOT_FOUND oder Timeout.
- Evidenz `evidence/m3-dds-completion-2026-11-05/`: sieben finale Source-Inventare
  und Binaryhashes passen, installierte Python-Dateien bytegleich. SDK/SRT/Wire 1/
  IPC 3 unverändert. Die volle M2-/5-min-N0-Evidenz bleibt historisch bei 940b4cb;
  diese Diagnose-Stufe wiederholt sie nicht. Keine Clock-/Crypto-/CPU-/Wire-Parität.

**Weiter:** belastbare empfangsseitige Reconciliation für nie admittierte Absichten
spezifizieren/prüfen; bloßer Timeout oder NOT_FOUND reicht nicht. Keine alte
Absicht erneut senden, keine Frische-/Start-Gates lockern. N5-Discovery, dann
vergleichbare Clock-/Crypto-/CPU-/Wire-Fenster und volle Matrix. PR #2 bleibt Draft,
M3 offen, Intrinsic/M4 unverändert.

### M3 DDS-Protokoll v2: empfangsseitige Expiry-Versiegelung — 2026-11-05

- `SEAL_EXPIRED` ist strikt nicht ausführend. Der Sender kann es nur für
  LOCAL_QUEUED/Revision 0 ohne bestätigte Receiver-Admission in ursprünglichem
  Owner/Prozess und derselben live Session senden, strikt nach gespeicherter
  5-s-Deadline. Nach Prozess-/Session-Wechsel bleiben alte Absichten QUERY-only.
  Alle DDS-Frames einschließlich HELLO verlangen Protokollversion 2; beide Enden
  neu bauen, kein Downgrade. Keine SDK-Wire-/IPC-/SRT-Änderung.
- Neuer ROS-Helper nutzt ausschließlich die öffentliche, unveränderte SDK-
  Journal-API. Existierender Record wird unverändert geliefert (auch ACCEPTED,
  DISPATCHING, SUCCEEDED, UNKNOWN); widersprüchliche Metadaten sind Konflikte.
  Nur fehlende ID nach Deadline erzeugt per vorhandener FULL-synchroner Admission
  EXPIRED/START_DEADLINE, Revision 1, ohne Dispatch/Resultat. Commit vor STATUS.
  Kein Handlerpfad; späteres COMMAND findet das ID-/Hash-Tombstone und startet
  nicht. Journal-Records werden in der Session nicht eviziert. Context-Verlust
  während Commit kann nichts ausführen; unbekannte Historie in neuem Kontext
  wird nicht als Expiry ausgegeben. Bestehendes Tombstone bleibt per QUERY lesbar.
- Separate Seal-Sent/Received/Inserted/Existing/Rejected-Zähler. Vorhandener
  Record ist keine neue Expiry. Ausführbares COMMAND wird nicht erneut publiziert;
  Reliable-DDS-Paketretransmission bleibt erlaubt. Timeout/NOT_FOUND allein sind
  weiterhin kein Terminalresultat. Erst bestätigter Receiver-Status beendet die
  Unsicherheit; Lab-Cadence darf danach neue ID ohne Generationserhöhung anbieten.
- Drei N2-Probes je 60 s: 1701 24 SUCCEEDED/24 Intents; 2903 28 SUCCEEDED plus
  eine EXPIRED/29; 4211 24 SUCCEEDED plus eine EXPIRED/25. Alle ohne offene Intents.
  Beide Expiry-IDs auf beiden Seiten Revision 1, identische Hashes/Generation,
  keine Dispatch-Zeit/kein Resultat; Receiver-Admission strikt nach Deadline.
  Bei 4211 verfällt ID 20, neue geplante ID 21 gelingt mit expected generation 19
  und result generation 20. Insgesamt 25 COMMAND-Publikationen/25 neue Intents,
  nur 24 Starts/Effekte. Bei 1701 liefert Seal echten schon committeten Erfolg;
  keinerlei Überschreiben nach Deadline. Kein deterministischer Paket-Replay-
  Vergleich mit alten Seeds und kein 600-s-Abnahmegate.
- Fünfminütiges N0 `20261105T205705247794Z`: 150/150 SUCCEEDED/150 Effekte,
  keine Seals. Ist 199,984/50,001 Hz; 75.024 produziert/75.002 empfangen, 20 IMU-
  und zwei Joint-Gaps vor Callback. Lokale Shared-VM-Alterschecks bestanden,
  keine isolierte WAN-Verlust-/Cross-Host-/Hardware-Aussage. Beide Journale stimmen
  in allen 150 Resultaten überein, quick_check bestanden.
- N4-Smoke bleibt 4/5 SUCCEEDED/ein offen, beide Enden nach Outage wieder ready;
  keine Seals über den Context-Wechsel. N5 control-first zwei SUCCEEDED/zwei
  Effekte, 31 Seals auf vorhandene Records, kein falsches EXPIRED, sechs Slots
  blockiert. N5 simultaneous erneut fehlgeschlagen vor Messfenster; Discovery offen.
- Acht neue tatsächliche SDK-Journal-GTests: Deadline-Grenze, Metadaten/Context,
  Tombstone/Duplikat/später Dispatch, vorhandene Zustände, Konflikte, Sender-
  Eligibility, verlorener Reply mit Owner-Reopen/QUERY, Speicherfehler. Insgesamt
  32 echte ROS-GTests/36 mit Wrappern und 33 Python-Tests bestanden. DDS-Fault-
  Acceptance einschließlich Receiver-/Sender-SIGKILL/UNKNOWN/No-Replay und volle
  originale M2-Neubau-/Runtime-Regression bestanden.
- Evidenz `evidence/m3-dds-expiry-seal-2026-11-05/`: neun finale Source-Inventare
  passen (DDS 140/M2 88), Binaryhash identisch, installierte Python-Dateien
  bytegleich. C++-Build `205428937697Z` hat ausschließlich spätere nicht kompilierte
  Änderungen an zwei Runner-Metadaten und Host-Testdatei; alle kompilierten Inputs
  passen. Finale Fault-/M2-Läufe `205705247608Z`/`205705247870Z`. SDK-Archivhashes
  gegen b8e198d identisch, Core/Proto und SRT-Quelle unverändert. Roh-PCAPs/Journale
  lokal, Hashes/Größen erhalten. Frühere Evidenz unverändert.

**Weiter:** Kontext-/Owner-wechselnde Unsicherheit bleibt explizit offen; keinen
Abwesenheitsnachweis aus einem neuen leeren Journal ableiten. N5-Discovery und
SRT-Parität der neuen Reconciliation-Semantik/-Kosten qualifizieren, danach
Clock-/Crypto-/CPU-/Wire-Gleichheit und volle Matrix. M3 offen, PR #2 Draft,
Intrinsic/M4 unverändert.

### M3 explizites DDS-Sensor-Pacing für N5 — 2026-11-05

- Neue optionale `--dds-profile paced-sensors` in Combined- und Fault-Runner.
  Default bleibt system. Keine ROS-/Core-/SDK-/SRT-/Protokolländerung; unveränderte
  kompilierte Inputs/Binaries seit 02d40e6. Keine Gates gelockert. Normale
  Nicht-skip-Builds bauen die separate Native-Probe automatisch; Preflight bei
  jeder paced-Ausführung, auch bei dokumentierter Binary-Wiederverwendung.
- XML: gleiche UDPv4/SHM-1200-Paketisierung wie vorheriger negativer Versuch,
  nur `/robot/imu` und `/robot/joint_states` asynchron auf gemeinsamem Controller
  1600 Byte/50 ms pro Simulator-Participant. Kein Ethernet-/globales Budget oder
  TC-Prioritätsbypass. Source bleibt 200/50 Hz, Sensor-QoS BE/Volatile/KeepLast(1),
  Controls Reliable/Volatile/KeepLast(64) synchron auf Default-Controller.
  RMW-XML-Opt-in nur für diese Variante; PREALLOCATED_WITH_REALLOC und DataSharing
  OFF explizit erhalten, SHM-Transport weiter aktiv.
- Standalone-C++-Probe nutzt öffentliche RMW/Fast-DDS-Handles für reale Controller-
  und Writer-QoS. Positive Prüfung und Build-Rezept bestanden. Ohne XML-Opt-in
  verweigert Provider die Writer-Erzeugung. Probe läuft vor Laborerzeugung in
  eigenem network-none-Container, ohne Discovery-Warmup gemessener Peers.
  Sie wird nicht in Bridge/Simulator gelinkt; Fast-DDS-spezifisches Lab-Werkzeug.
- N5-Runner prüft jetzt lebenden Konkurrenten während Szenario-Polls sowie UDP,
  Ziel 128.000 bit/s, 1024 Byte und plausibles gesamtes tatsächliches Angebot.
  Cleanup-SIGINT akzeptiert; anderer Fehler/fehlende Last scheitert. Kein Beleg
  fenstergenauer Zustellung. TBF 512 kbit/s/Netem 16 und Konkurrenz bleiben vor
  Source-/Koordinatorstart aktiv; kein control-first-Publikationsstopp.
- Fünfminütiges N5 simultaneous/paced `20261105T214042516097Z`: 150/150 bestätigt,
  150 Effekte, keine Lease-Abläufe/Inbox-Drops/Seals, beide Enden ready. Source
  Ist 199,993/50,002 Hz, 60.019 IMU/15.006 Joints produziert, 11.752/7.376 Callbacks.
  Alle 19.128 empfangenen Samples bestehen lokale Alterschecks. 55.897 fehlen
  vor Callback inklusive beabsichtigter Middleware-Pacing-/Ersetzungsanteile;
  kein isolierter WAN-Verlust. Beide geschlossenen Journale quick_check ok,
  identische 150 SUCCEEDED/Revision-3-Records, Resultgenerationen 1–150.
  Konkurrenz gesamt 128.009,2 bit/s, 1250 lebende Prozess-Polls.
- Drei paced-N5-Smokes, Seeds 1701/2903/4211, je 8/8 bestätigt/acht Effekte.
  Frische System- und UDP1200-N5-Runs scheitern vor Messfenster trotz validierter
  Konkurrenz. Pacing ist expliziter Baseline-Kandidat, kein Default-Fix und kein
  verlustloses Ergebnis. N0 system, N0 paced, sensor-only paced und paced-N0-
  Fault-Acceptance mit Duplikat/Konflikt/UNKNOWN/SIGKILL/QUERY/No-Replay/5-s-Shutdown
  bestanden; blockierter Handler lässt Leases unverändert. 35 Python-Tests bestanden.
  Die 32 ROS-GTests/volle M2-Regression bei 02d40e6 bleiben historische Evidenz,
  nicht als hier erneut ausgeführt ausgeben.
- Evidenz `evidence/m3-dds-paced-sensors-2026-11-05/`: zehn finale Source-Inventare
  passen (143 Dateien), installierte Python-Dateien bytegleich, unveränderte
  Bridge-/Simulator-Binaries und Native-Probe-Build-/Sourcehashes geprüft.
  Erster Smoke vor strenger Konkurrenzprüfung separat unter development erhalten.
  Roh-PCAPs/Journale lokal, bereinigte Resultate/Hashes/Provider-QoS gespeichert.
  Async-Fences frieren Publish-Aufrufe ein; Restdaten bleiben durch bestehende
  Quieszenz-/Sequenzprüfungen beobachtet, kein behaupteter physischer Wire-Flush.

**Weiter:** getunte DDS-Pacing-/Reconciliation-Semantik und Kosten gegenüber SRT
angleichen; DDS-Emissionsstufen, Clock-/Crypto-/CPU-/Wire-Fenster und volle Matrix
qualifizieren. System-N5-Discovery und Context-wechselnde Unsicherheit bleiben
explizit offen. M3 in Arbeit, PR #2 Draft, Intrinsic/M4 unverändert.


## Fortsetzung 2026-11-06: gemeinsame Endpoint-Messfenster

- Beide Runner nutzen gemeinsamen Linux-Prozessbaum-Sampler, nominal 250 ms,
  inklusive Observer/Sampler. Gleiche Source-enabled- und Resume-through-drain-
  Phasen, ohne Startup/Shutdown. Innere/äußere CPU-Tickdeltas ohne Interpolation;
  RSS-Summe nur beobachtet, mögliche Shared-Page-Doppelzählung, kein PSS/Peak.
  Fehler/Identitätswechsel/Regression/reaped-child-CPU/Lücken verwerfen CPU.
  Ungesehene kurzlebige Kinder nicht abgedeckt. Alte SRT-Ressourcen bleiben
  Whole-run mit altem Scope und dürfen nicht direkt damit verglichen werden.
- Konditionale PCAP-Zeitfenster: gemeinsame Realtime/Monotonic-Hülle beider Enden,
  <=1000 ppm, keine versteckten Steps, <=1-s-Kalibrierlücken, <=1-ms-Read/Steps.
  Inside/Boundary/Outside inklusive Timestamp-Quantisierung. Keine Fensterbytes
  bei verworfener Kalibrierung; Whole-capture-Gates bleiben davor erforderlich.
- 44 Python-Tests und Demo-Install bestanden. Fünf finale Live-Entwicklungsläufe:
  SRT N0 30 s, DDS system N0 30 s, DDS paced N0 30 s, paced N5 60 s/30 bestätigte
  Commands, sensor-only system N0 15 s. Alle funktional bestanden und alle CPU-
  Fenster beider Enden qualifiziert. Alle Wire-Mappings wegen beobachteter Drift
  über 1000 ppm verworfen, daher keine qualifizierten Wire-Fensterresultate.
  Modell nicht lockern. Ursache noch nicht diagnostiziert.
- Vier alte SRT/DDS-Whole-captures neu ausgewertet: alle bisherigen Felder exakt
  identisch. Fünf Source-Inventare je 146 Dateien aktuell; installierte Scripts
  bytegleich. 56 kompilierte Quelldateien unverändert, Command-/Simulator-Binaries
  identisch zur historischen 02d40e6-Evidenz. Keine neuen ROS-GTest-/M2-Claims.
- Evidenz: `evidence/m3-window-measurement-2026-11-06/`, inklusive Raw-Hashes,
  Prozess-/Clock-Samples, Drift-Verwerfungen und Messscope. Zwei frühere Smokes
  nur Development, vor strengerem Clock-Modell. PCAPs/Journale bleiben lokal.

**Nächster Schritt:** Clock-Mapping ohne Modell-Lockerung qualifizieren; danach
kontrollierte CPU-/Wire-Kosten und getunte DDS-/SRT-Semantik vergleichen. Volle
Matrix/Emission-Stages/Crypto/Cross-session-Unsicherheit bleiben offen. M3 in
Arbeit, PR #2 Draft, Intrinsic/M4 unverändert.


## Fortsetzung 2026-11-06: Clock-Diagnose und unabhängige Kalibrierung

- Neue standalone Read-only-Probe `tools/clock_probe/main.cpp` plus
  `tools/m3_clock_probe.py`: Python, libc und direkte clock_gettime-Syscalls,
  RAW/BOOTTIME-Diagnose und adjtimex(modes=0). 95 s/910 Samples in network-none-
  Container mit cap-drop ALL. Native Realtime-Offsets ändern sich mindestens
  108/137 us über ca. 107/100 ms; RAW/BOOTTIME ohne Modellverletzung. Python sieht
  die zweite Änderung. Exit 2 ist korrektes negatives Diagnoseresultat.
  TIME_ERROR/STA_UNSYNC (5/64), freq/offset 0. Verursachender Agent nicht belegt;
  kein Nachweis eines Kernel-Bugs, alle Aufrufe im emulierten Linux-Kontext.
- 250-ms-Prozess-Sampling kann kurze Steps übersehen. Dedizierte Clock-Dateien
  nun unabhängig bei Scenario-Polls, mindestens 25 ms Abstand, maximal erlaubte
  Lücke 100 ms. CPU/RSS-Scans unverändert nominal 250 ms. Beide aktuellen Runner
  verlangen Clock-Dateien ohne stillen Legacy-Fallback. Historische Reanalyse
  bleibt als legacy-process-clock gekennzeichnet. 1000-ppm-Modell unverändert;
  auch feinere endliche Samples beweisen keine Abwesenheit versteckter Steps.
- 51 Python-Tests und Demo-Install bestanden. Neue Regression zeigt synthetischen
  150-us-Step: grobe Serie akzeptiert, feinere Serie verwirft. Zusätzlich echter
  finaler SRT-N0-Lauf zeigt in beiden Phasen/beiden Enden grobe Akzeptanz gegen
  dedizierte Drift-Verwerfung. Alte Entwicklungs-Smokes nicht als qualifizierte
  aktuelle Wire-Kosten ausgeben. Native Probe-Verwerfung lag vor dem ersten
  Development-SRT-Sourcefenster, kein behauptetes überlappendes Gegenbeispiel.
- Finale Live-Läufe: SRT N0 30 s/15 bestätigt, DDS system N0 30 s/15 bestätigt,
  DDS paced N5 60 s/30 bestätigt. Alle funktional bestanden, CPU-Fenster beider
  Enden qualifiziert, Wire-Fenster sämtlich verworfen. 149 Source-Dateien je
  Manifest passen; installierte Python-Dateien bytegleich; 56 Produktions-
  Quelldateien und Command-/Simulator-Binaries unverändert. Keine neue ROS-GTest-
  oder volle M2-Ausführung. Drei vorherige Development-Reruns separat erhalten.
- Evidenz `evidence/m3-clock-diagnosis-2026-11-06/`: Probe-Samples/Provenienz,
  dedizierte/Legacy-Kalibrierungen, Clock-/Prozess-Samples und Raw-Hashes.
  Historische Evidenz unverändert, PCAPs/Journale weiter lokal.

**Weiter:** stabile geeignete Linux-Clock-Umgebung oder verifizierte monotone
Packet-Timestamp-Erfassung entwickeln, ohne Driftmodell/Unsicherheit zu lockern.
Danach kontrollierte CPU-/Wire-Kosten und getunte DDS-/SRT-Semantik vergleichen.
M3 bleibt in Arbeit, PR #2 Draft, Intrinsic/M4 unverändert.


## Fortsetzung 2026-11-06: optionaler Kernel-Monotonic-Packet-Observer

- `--monotonic-capture` in SRT-/DDS-Runner: eigener passiver AF_PACKET-Socketfilter
  mit bpf_ktime_get_ns, skb-Länge, Interface/Richtung und 128-Byte-Prefix. Keine
  Realtime-Konvertierung. Gemeinsame vorhandene Source-/Fenced-Phasen [start,end).
  Eigene Ergebnisse `monotonic_captures`; Realtime-PCAP-Gates unverändert.
- Standalone g++/libbpf-Tool erzeugt verifiergeprüfte BPF-Instruktionen direkt,
  ohne clang/BTF/neues Image. CAP_BPF nur auf eigenen Opt-in-Endpunkten;
  Default-Caps unverändert. Kein Host-/Privileged-/tc-/XDP-/Clock-Eingriff.
  Zero Time-Namespace-Offsets zwingend; vorhandener gemeinsamer Boot-/Clock-Proof.
- 16-MiB-Ring, Datei unter 128 MiB, atomare Seen-/Submitted-/Reserve-/Copy-Zähler,
  Socket-Close/Drain/stabile Footer-Zähler plus Coverage-/Records-Gates.
  Fehler verwerfen Resultate. Präfixparser IPv4 UDP, DDS-IPv4-Fragmente getrennt;
  bekannte IPv6-Nicht-UDP-Ketten begrenzt prüfen/ignorieren, IPv6-UDP/unsupported
  verwerfen. Kein behaupteter physischer Wire-/Delivery-/Population-Nachweis.
  Kernel-Observer-Arbeit kann Endpoint-CPU belastet werden; Messvariante explizit.
- 58 Python-Tests bestanden. Isoliert 40 Datagramme/80 Loopback-Observations:
  Längen stimmen, sämtliche Kernelstamps innerhalb Userspace-Send/Receive-
  Monotonic-Brackets. Gezielter 4-KiB-Overflow: 2.000 Seen, 25 Submitted,
  1.975 Reserve-Fehler, erwarteter Exit 2/Analyzer-Reject. Ohne CAP_BPF kein Ready.
- Vier finale Source-153-Dateien-Inventare passen: SRT N0 Smoke15s/8 bestätigt,
  DDS N0 Smoke15s/8 bestätigt, paced N5 30s/15 bestätigt, Default-Sensor Smoke15s
  ohne Observer/BPF-Cap. Alle funktional bestanden; alle Opt-in-Phasen beider
  Enden CPU-/Monotonic-Capture-qualifiziert, kein Recorderverlust. Installierte
  Scripts bytegleich; 56 Produktionsquellen und Command-/Simulator-Binaries
  unverändert. Keine neue ROS-GTest-/volle-M2-Ausführung.
- Evidenz `evidence/m3-monotonic-capture-2026-11-06/`: Roh-Hashes, native Provenienz,
  Namespace-/Capability-Proofs, Counter/Phasen, synthetische Timestamp-Brackets.
  Frühe IPv6-Parserfehler und längere Development-Runs vor CPU-Scope-Textkorrektur
  separat erhalten. Roh-PCAPs/Prefixes/Journale lokal. Whole-capture-Korroboration
  ist wegen verschiedener Socket-Lebensdauer keine Gleichheits-/Loss-Garantie.

**Weiter:** längere Läufe/Seeds, Observer-Overhead und Tap-/Offload-Scope
qualifizieren; danach kontrollierter SRT-/DDS-Kostenvergleich bei angeglichener
Pacing-/Reconciliation-/Age-/Crypto-Semantik. M3 in Arbeit, PR #2 Draft,
Intrinsic/M4 unverändert.


## Fortsetzung 2026-11-06: Cgroup-Scope und präregistrierte Observer-Studie

- Read-only cgroup-v2-Counter im bestehenden 250-ms-Endpoint-Sampler: Root-/
  Domain-/Self-PID-Prüfung, Namespace-/Device-/Inode-Identität, CPU-/Memory-Limits,
  CPU-Mikrosekunden, charged Memory und Memory-Events. Neue unabhängige
  `container_cgroup`-Phasen neben Prozess-CPU. Capture/Competitor enthalten,
  außerhalb der Gruppe abgerechnete Host-/Kernelarbeit nicht garantiert erfasst.
  Inner/outer beobachtete Deltas ohne Interpolation, keine CPU-Konfidenzintervalle.
  Charged Memory mit Cache/Kernel, kein RSS/PSS/harter Peak. Fehler/Änderungen
  verwerfen Ressourcenqualifikation, Ausführungsgates unverändert.
- `tools/m3_observer_study.py` schreibt Plan/Quellen vor erstem Kind: SRT N0
  off/on/on/off und DDS system N0 on/off/off/on, jeweils viermal 45 s/Seed1701;
  danach paced N5/Monotonic jeweils 300 s für 1701/2903/4211. Sequentiell, frische
  Endpoints, keine Retries/Host-Tuning. Pärchen verlangen passende Konfiguration/
  qualifizierte Counter; negative Differenzen erhalten, Commandcounts/Effects
  getrennt geprüft und Sensorpopulationen gespeichert. Vorhandene Builds als
  explizite Development-Wiederverwendung; normaler separater M3-Build Voraussetzung.
- 68 Python-Tests und Demo-Install bestanden. Alle elf Plan-Läufe ohne Retry
  bestanden. 44 Cgroup-Fenster aus projizierten Original-Brackets exakt nachgerechnet,
  alle 44 engeren Prozess-CPU-Fenster ebenfalls qualifiziert. Sieben Opt-in-Läufe
  mit 28 qualifizierten Monotonic-Endpunkt-/Phasenfenstern, kein Recorderverlust.
  Lokale Throttle-/Memory-Events null; kein Nachweis ungestörter VM-/Ancestor-CPU.
- Drei Fünfminuten-N5-Läufe bestätigen je 150/150 Commands/150 Effekte, insgesamt
  450. Produced/Callbacks: Seed1701 75.032/19.079, Seed2903 75.018/19.236,
  Seed4211 75.031/19.286. 200/50-Hz-Produktion bleibt erhalten; fehlende Callback-
  Population enthält bewusstes Pacing/Replacement und andere Stufen, kein isolierter
  WAN-Loss. Keine N5-Randomloss-/Jitter-Konfiguration: Seeds markieren hier frische
  Wiederholungen. System-N5-Cold-Discovery damit nicht behoben.
- Acht N0-Paarläufe je 23 bestätigt/23 Effekte. CPU-Differenzen haben wechselnde
  Vorzeichen, keine isolierte Observer-Overheadzahl ableiten. Beobachtete Charged-
  Memory-Maxima on-minus-off ca. 19–23 MiB/Endpunkt; kein physischer Footprint.
  Erster SRT-Off-Lauf IMU 198,182 statt ca. 200 Hz, Callbackpopulationen variieren;
  keinen Lauf post hoc zum Glätten verwerfen. Tabellen/alle Paare erhalten.
- Alle 22 geschlossenen Journale quick_check ok, passende IDs/Hashes/Ergebnisse:
  insgesamt 634 SUCCEEDED/Revision-3-Records pro Seite, Generationen lückenlos.
  Read-only-Audit ändert Haupt-DB-Hashes nicht; keine zusätzliche Crash-Fault-Quali.
- Evidenz `evidence/m3-observer-study-2026-11-06/`: Plan/Studie, projizierte
  Cgroup-Samples, vollständige Run-Manifeste, Scope-/Capability-/Namespace-Proofs,
  Raw-Hashes und Journal-Audits. Initialer Cgroup-Smoke nur Development. Elf
  Inventare je 156 aktuelle Source-Dateien, installierte Scripts bytegleich;
  56 Produktionsquellen und Command-/Simulator-/Native-Capture-Binaries unverändert.
  Keine neuen ROS-GTests/volle M2 behaupten; Roh-PCAPs/Prefixes/Journale lokal.

**Weiter:** kontrollierte/geeignete Ressourcen-Umgebung und Tap-/Offload-Scope
qualifizieren; längere SRT-/DDS-Läufe/weitere Impairment-Profile, volle Matrix und
N3-/N4-Spezialgates. Pacing/Reconciliation/Age/Crypto-Semantik bleibt vor einem
Transportkostenvergleich anzugleichen. M3 in Arbeit, PR #2 Draft,
Intrinsic/M4 unverändert.


## Fortsetzung 2026-11-06: Tap-/Offload-Probes und Capture-Artefakt v2

- Kontrollierte synthetische UDP-Probes mit frischen eigenen Endpoint-Paaren:
  normales UDP, 100% Egress-netem-Drop, 200-ms-Delay, gezielter Ingress-Drop,
  UDP_SEGMENT ohne/mit netem und shaping-only 512 kbit/s. Kein ROS/SRT-App-Peer,
  kein Konkurrent im Shaping-Probe; kein voller N5-Nachweis dadurch. Je Probe
  positives Restoration-Control im selben offenen Observer zwingend.
- Laufzeitbeleg: 16 normale Datagramme an beiden Taps/Empfänger. Egress-Drop:
  16 gezielte UDP-Matches vor Root, null Tap-/App-Beobachtungen; globale Rootdrops
  enthalten zusätzliche, nicht nach Protokoll zugeordnete Inkremente. Delay: Sender-Tap inklusive Queue-Delay,
  finale Spanne 200,02–206,94 ms (Klassifikationsschwelle 150 ms, kein Präzisionsbound).
  Ingress-Drop: 16 an beiden Taps, 16 gezielte Drops, null App-Receipts.
  Historisches generisches `egress is pre-qdisc`-Label war für dieses Fixture
  falsch. Neue Scope-Texte neutral, alte Artefakte unverändert mit Korrektur lesen.
- UDP_SEGMENT in beiden Fällen: eine 9.642-Byte-SKB-Observation pro Seite,
  gso_segs=8/gso_size=1200, acht 1.200-Byte-Datagramme an der App. Keine physische
  Frame-/Datagrammzählung aus SKB-Anzahl ableiten. Native Capture-Artefakt v2 mit
  168-Byte-Records/GSO-/VLAN-/MTU-Metadaten, 128-Byte-Prefix bleibt. Reader unterstützt
  v1/152 Byte mit unbekannten Offloads; neue Runner verlangen v2. SDK-Wire/IPC
  unverändert. Eigenständige GET-only-Ethtool-Probe speichert Feature-/MTU-Vorher/
  Nachher, kein SET/keine neuen Privilegien; aktive Features allein beweisen Nutzung
  nicht. `frame_interpretation` unabhängig von gültiger SKB-Observation und weiter
  kein Physical-/Checksum-/Padding-/FCS-/Delivery-Nachweis.
- Capture-Datengap entdeckt: Buffered-PCAP schrieb 16 statt 17 bekannter Beobachtungen,
  letztes Control fehlte. Runner jetzt Immediate-Mode, Client zuerst stoppen,
  kurze Inflight-Drainphase. Captured/File/Kerneldrop-Gates strikt. Filtercounter
  können auch bei exakt passenden bekannten Tap-Populationen abweichen; Ursache/
  Einheit nicht vollständig geklärt. Daher separates Population-Reconciliation-Flag,
  keine falsche universelle Gleichheitsinvariante. Unreconciled verwirft Realtime-
  PCAP-Fenster, nicht unabhängige native Observer-Counter. Bekannte-Probe-Tupel in
  finalen Fällen zwischen Native/PCAP exakt identisch.
- 74 Python-Tests bestanden, native Builds mit -Werror. V2-Loopback 40 Datagramme/
  80 korrekte Stamps/Längen; forcierter 4-KiB-Overflow 2.000 Seen/23 Stored/
  1.977 Reserve-Fehler, erwarteter Exit 2. Sieben kontrollierte Fälle bestanden.
  Vier finale Live-Läufe: SRT/DDS N0 Smoke je 8 bestätigt, paced N5 30s/15 bestätigt,
  Default-Sensor Smoke ohne BPF-Observer. Alle Opt-in-Phasen qualifiziert, keine
  Recorderfehler/GSO/VLAN/Over-MTU-SKBs in gemessener UDP-Population; PCAP-Counter
  hier reconciled. Feature-Snapshots stimmen. 159 aktuelle Quellen in Probe und
  vier Manifesten; installierte Python-Dateien bytegleich, 56 Produktionsquellen
  und Command-/Simulator-Binaries unverändert. Native Observer/Feature-Binaries neu.
- Vier alte Classic-Captures numerisch/Klassen unverändert (nur Scope korrigiert),
  vier v1-Endpunkt-/Phasenfenster identisch mit Offload-Metadaten unbekannt/
  Frameinterpretation unqualifiziert. Rohdaten/alte Evidenz nicht umschreiben.
  Neue Evidenz `evidence/m3-tap-offload-2026-11-06/` mit Feature-/Flow-/TC-Proofs,
  Counter-Gegenbeispielen und separaten Development-Iterationen. Volle Docker-
  Inspect-Logs nicht publiziert, nur Capability-/Namespace-Projektion. Roh-PCAPs/
  Prefixes lokal mit Hashes. Keine neuen ROS-GTests/volle M2-Ausführung behaupten.

**Weiter:** V2-/Immediate-Observer-Kosten neu qualifizieren; die vorige V1-/Buffered-
Studie gilt dafür nicht direkt. Weitere Device-/Offload-Pfade, kontrollierte
Ressourcen, verbleibende Profile/Dauern und N3-/N4-Gates. Pacing/Reconciliation/
Age/Crypto vor Transportkostenvergleich angleichen. M3 in Arbeit, PR #2 Draft,
Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-06: V2-Observer und kurze N1/N2-Probes

- Erste V2-/Immediate-Studie am achten N0-Lauf wegen echter PCAP-Kerneldrops
  (315 Robot/322 Operator) gestoppt. Commands/Effekte und Native Recorder dort
  bestanden. Fehlgeschlagener Plan und acht Manifeste separat archiviert;
  kein Ersatzlauf im alten Plan, keine Lockerung des Zero-Drop-Gates.
- Read-only setsockopt-Diagnose: libpcap 1.10.4 Immediate/TPACKET_V2 mit aktiven
  Offloads und voller Snapshot-Länge hat beim 4.096-KiB-Request nur 64 Slots,
  8 MiB tatsächlich alloziert. Neuer gemeinsamer 32.768-KiB-Request: 512 Slots,
  64 MiB alloziert. Kontrollierter Reader-Stopp bei 400 Datagrammen: alt 336
  Drops je Seite; neu alle 400 plus Recovery-Control, null Drops. Native/App
  vollständig. Kein Offload-SET, kein Preload in normalen Läufen. Ein früher
  OS-Signalnummern-Fehlversuch bleibt ausgeschlossenes Development.
- Neuer eingefrorener Plan: acht N0-On/Off-Läufe je 45 s, vier SRT/DDS-N1/N2-
  Probes je 60 s/Seed 1701, kein langes N5 in diesem Plan. Alle zwölf bestanden,
  PCAP-Kerneldrops null, Native Reserve-/Copy-Verluste null. 299 SUCCEEDED/
  Effekte, keine unaufgelösten Intents; 24 geschlossene Journale integral und
  terminal identisch. DDS N2: 25 statt 30 Versuche, fünf übersprungene Slots;
  max. Invocation-bis-Terminalbeobachtung 10.870,99 ms, kein Execution-Latency-
  Nachweis. Keine TTL-/Lease-/Admission-/Replay-Änderung.
- Studie bindet Immediate/Buffer/Snapshot/V2/Boot-ID sowie acht ausgewählte
  installierte Binär-/SDK-Hashes. 159 Quellen je Manifest gleich, installierte
  Python-Scripts bytegleich, 56 Produktionsquellen und Command-/Simulator-
  Binaries unverändert. 75 Host-Python-Tests bestanden; 48 Cgroup-Phasen aus
  archivierten Projektionen exakt reproduziert. CPU-Differenzen mit wechselndem
  Vorzeichen: keine isolierte Overhead-Schätzung. Charged-Memory-Maxima On-minus-
  Off ca. 20,56–24,19 MiB, kein RSS/PSS oder physischer Footprint.
- Evidenz: `evidence/m3-v2-observer-impairments-2026-11-06/` inklusive fehlgeschlagener
  Studie, Ring-Diagnose, Manifeste, Counter-Projektionen, Hashes und Journal-Audits.
  Roh-PCAPs/Prefixes/Journale bleiben lokal; keine vollständigen Inspect-/Env-Dumps.
  Keine neuen ROS-GTests/volle M2-Ausführung behaupten.

**Weiter:** volle N1/N2-Dauern und drei Seeds, V2/langes N5, kontrollierte Ressourcen,
weitere Device-/Offload-Pfade und N3-/N4-Spezialgates. DDS N2 zeigt weiter große
Terminalbeobachtungs-Latenz trotz erfolgreicher Effekte; nicht als Echtzeitgarantie
lesen. Pacing/Reconciliation/Age/Crypto vor Transportkostenvergleich angleichen.
M3 in Arbeit, PR #2 Draft, Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-06: DDS-Status-Timeline und begrenzte Poll-Historie

- Historischen N2-Intent 15 korreliert: Receiver-Finish-Zeitstempel 83,47 ms nach
  Aufruf, danach 10.655,11 ms bis Sender-Resultbeobachtung und weitere 132,41 ms
  bis Driver. Zeitstempel vor Journal-Mutation/Commit, kein fsync-/Handlerstart-
  Nachweis. Empfangene SUCCEEDED-STATUS am Tap schon nach 157,52 ms; vorherige
  Control-Sequenz 55 erstmals nach 10.735,75 ms. 51 Stale-Control-Rejections im
  Sender. Reliable-Ordering/Retransmission-Blockade mit anschließender Freshness-
  Ablehnung ist damit konsistent, aber keine per-Frame-Callback-Ursache bewiesen.
- Offline Generated-CDR-Fingerprint-Probe: 516 gegen Journale validierte
  Beobachtungen, je eindeutiger Native-Längen-/128-Byte-Prefix-Match. Kein
  generischer RTPS-Parser/Reassembler/Population-Vollständigkeitsnachweis;
  Serialisierungs-Roundtrip-Differenzoffsets explizit, keine volle Bytegleichheit
  behaupten. Native-Monotonic-Stamps, keine PCAP-Realtime-Konvertierung. Rohdaten
  lokal, Decoder-/Image-/Generated-Type-Provenienz und Hashes archiviert.
- DDS-Driver speichert erste 32/letzte 32 Status-Service-Polls je Intent, Zähler
  für ausgelassene Mitte. Keine Terminalerfindung aus Budgetablauf/NOT_FOUND.
  Neue Read-only-Timeline unter tools/m3_dds_result_timeline.py verlangt geschlossene
  checkpointed Journale, Common-VM/Zero-Offsets, Hash-/Kontext-Konsistenz und
  passende aktuelle Owner. Unknown/fehlende/recovered Records ohne Zerlegung.
- Drei eingefrorene neue N2-System-DDS-Läufe je 60 s/Seeds 1701, 2903, 4211:
  84 Versuche, 82 SUCCEEDED/Effekte, zwei Receiver-EXPIRED Revision 1 ohne Dispatch,
  keine unaufgelösten Intents. Pro Seed Erfolg/Expiry/Skipped: 27/1/2, 30/0/0,
  25/1/4. Max. Terminalbeobachtung 5.413/1.448/8.459 ms. Beide Expiries mit einem
  Stale-COMMAND am Receiver; Poll-Historien vollständig (27/42), spätere neue IDs
  erfolgreich. Kein generationsändernder Effekt für die Expiries.
- PCAP-Kerneldrops und Native Reserve-/Copy-Verluste null; sechs Journale integral
  und terminal identisch. 161 Quellen während aller drei Läufe unverändert,
  acht installierte Binär-/SDK-Hashes sowie installierte Python-Scripts konstant.
  Danach nur Offline-Analyzer/Test um Current-Owner-Guard ergänzt: eingefrorene
  Versionen erhalten, finale Reanalyse aller Timelines identisch. 56 Produktions-
  C++/Header/Proto-Quellen unverändert, keine neuen ROS-GTests/volle M2-Ausführung.
  Demo-Python-Paket normal installiert, 83 finale Host-Python-Tests bestanden.
- Evidenz: evidence/m3-dds-status-timeline-2026-11-06/ mit Histories, getrennten
  Success-/Expiry-Ergebnissen, Source-/Owner-Guard-Provenienz und Raw-Hashes.
  Keine vollständigen Inspect-/Env-Dumps. Deadline/Lease/Freshness/QoS/SDK/Wire/
  IPC/Atomic-Start/Sealing/No-Replay unverändert, Intrinsic/M4 unverändert.

**Weiter:** volle 600-s-N1/N2-Matrix mit drei Seeds, V2/langes N5 und kontrollierte
Ressourcen, andere Device-/Offload-Pfade sowie N3-/N4-Spezialgates. Lange STATUS-
Beobachtung und andere SRT-/DDS-Semantik/Security verhindern Transportkosten- oder
Echtzeit-Überlegenheitsbehauptungen. M3 in Arbeit, PR #2 bleibt Draft.

## Fortsetzung 2026-11-06: Default DDS N2 je 600 s/drei Seeds

- Eingefrorener Plan vor erstem Lauf: System-DDS, N2, Seeds 1701/2903/4211,
  je 600 s, frische sequentielle eigene Container, Native Observer v2 aktiv,
  Immediate/Full-Snapshot/32.768-KiB-PCAP-Request. Keine Retries/Ersatzläufe,
  kein Rebuild/Policy-Wechsel. Netem-Readbacks und konkrete TC-Argumente erhalten.
- Alle drei Source-Fenster vollständig (600,141/600,126/600,138 s), Execution- und
  Capture-Gates bestanden. Pro Seed Versuche/Erfolge/Effekte/Expiry/Not-admitted/
  Skipped: 282/277/277/5/0/18, 285/281/281/4/0/15, 276/272/272/3/1/24.
  Insgesamt 843 Versuche, 830 SUCCEEDED/Effekte, zwölf Receiver-EXPIRED Revision 1
  ohne Dispatch, ein BUSY vor Queue-Aufnahme, 57 übersprungene Slots. Keine
  UNKNOWN/unaufgelösten Intents, keine automatischen Wiederholungen.
- Seed 4211 Intent 268: Submission BUSY=1, kein Journal-Record an beiden Seiten,
  Sender überträgt nur 275 der 276 Versuche. Explizite Admission-Antwort und
  Abwesenheit getrennt halten; aus generischem NOT_FOUND keine Nichtausführung
  ableiten. Späterer neuer Intent behält erwartete Generation. Sechs Journale
  integral/terminal identisch; Generation-Chains ergeben 277/281/272. Dispatches
  und atomare Startclaims entsprechen Effekten; zwölf Expiries erhöhen Generation
  nicht. Max. Terminalbeobachtung je Seed 8.463,640/5.610,490/5.895,465 ms.
- Sensor-Altersqualifikation: Seed 1701 **fehlgeschlagen** (sechs Clock-Steps,
  max. 6,206431 ms, max. Offset-Abweichung 9,055105 ms). 25.435 IMU-/13.445 Joint-
  Callbacks clock-rejected. Histogramme nicht als qualifizierte Gesamtverteilung
  lesen. Seeds 2903/4211 Shared-VM-Age-Estimates qualifiziert; trotzdem sämtliche
  Realtime-PCAP-Fenster wegen strengerem Clockmodell unterdrückt. Native Kernel-
  Monotonic-Counter separat qualifiziert, kein Physical-/Delivery-Nachweis.
- Alle PCAP-Kerneldrops/native Reserve-/Copy-Verluste null, zwölf Cgroup-Phasen
  aus archivierten Projektionen exakt reproduziert. 161 Sources in drei Manifesten
  und acht installierte Binär-/SDK-Hashes sowie installierte Python-Bytes konstant.
  Seed 2903 Robot-PCAP zusätzlich Filterpopulation unreconciled: 170.340 gefiltert
  vs. 170.338 Captured/File, null Kerneldrops; keine Ursache/Vollständigkeit daraus
  ableiten. Realtime-Fenster ohnehin unterdrückt, Native-Gates separat.
  56 Produktions-C++/Header/Proto-Quellen unverändert seit eb46aba. Ein gemeinsamer
  VM-Boot in dieser Kohorte. Vorige 83 Host-Python-Tests unverändert; keine neuen
  ROS-GTests/volle M2-Ausführung behaupten. Diese Fortsetzung ändert keine Runtime-
  Quellen, nur Evidenz/Planungsdokumentation. Intrinsic/M4 unverändert.
- Evidenz: evidence/m3-dds-n2-full-2026-11-06/ mit Plan, drei Manifesten, per-State-
  Latenzen, Admission-/Generationsbelegen, Clock-/Sensorpopulationen, Journal-Audits,
  Raw-Hashes und Cgroup-Projektionen. Keine vollen Inspect-/Env-Dumps; Roh-PCAPs,
  Prefixes, Journale und Clocks lokal. Keine kausale Ressourcen-/Transportüberlegenheit.

**Weiter:** DDS-N2-Dauer/Seed-Ausführung erledigt, **N2-Altersgate weiter offen**.
Volle SRT-N2- und beide N1-Matrizen, V2/langes N5, deterministisches N3, N4-Phasen,
andere Devices/Offloads, kontrollierte Ressourcen und Semantik-/Security-Parität.
M3 in Arbeit, PR #2 bleibt Draft; keine Echtzeit-/Lossless-/Hardwarefreigabe.

## Fortsetzung 2026-11-06: SRT N2 je 600 s/drei Seeds

- Eingefrorener Plan vor erstem Lauf: SRT N2, Seeds 1701/2903/4211, je 600 s,
  frische sequentielle eigene Endpoint-Paare. Bestehende Crypto-/Profile-/Deadline-/
  Lease-/Journal-/Atomic-Start-/No-Replay-Policy, Native v2 und Immediate/Full-
  Snapshot/32.768-KiB-PCAP unverändert. Keine Rebuilds, Retries oder Ersatzläufe.
- Alle drei vollständigen Source-Fenster (600,149477/600,101959/600,140695 s)
  bestanden. Je Seed 300 SUCCEEDED/Effekte, insgesamt 900; null EXPIRED/FAILED/
  REJECTED/UNKNOWN/unaufgelöste/not-admitted/übersprungene Intents. Max. lokale
  Invocation-bis-Terminalbeobachtung 1.106,214/1.309,764/1.110,049 ms; keine
  Ausführungs-/Netzlaufzeitgrenze daraus ableiten. Sechs geschlossene Journale
  integral, je Intent an beiden Seiten Revision 3/Result/Hash/Generation identisch.
  Generation-Chains und Device-Effekte je 300, keine neue Intent-Wiederholung.
- Alle sechs Conservation-Residuals je Source-Fenster null und exakt nachgerechnet.
  Produced/Published/Observer je Seed: 150.036/64.233/64.176,
  150.026/64.037/63.980, 150.036/64.183/64.125. Sämtliche lokalen Verlust-/Replace-/
  Reject-Populationen behalten; Accept-to-Receiver-Gap nicht als isolierter WAN-
  Verlust oder FEC-Nutzen auslegen. Nicht alle produzierten Samples werden zugestellt.
- Source-fenced Publication-Age-Upper-Maxima (auf 1 ms aufgerundet) IMU/Joints:
  143/168, 144/164, 141/163 ms; unter unverändertem 250-ms-Gate. Origin ist Bridge-
  Ingress, kein physisches Sampling-to-Delivery und keine DDS-Header-Age-Parität.
  Diagnostics-Hold-Dauern enthalten Startup/Tails/Gaps, keine exakte Window-Uptime.
- PCAP-Kerneldrops und Native Reserve-/Copy-Verluste null. Sechs PCAP-Populationen
  hier reconciled, kein universeller Completeness-/Physical-Delivery-Nachweis.
  Alle Realtime-PCAP-Fenster wegen Clock-Qualifikation unterdrückt; Native-Monotonic
  separat qualifiziert. Zwölf Cgroup-Phasen aus archivierten Projektionen exakt
  reproduziert. 161 Quellen und acht ausgewählte installierte Binär-/SDK-Hashes
  sowie installierte Python-Bytes konstant; 56 Produktionsquellen unverändert seit
  fd23de6. Ein VM-Boot in der Kohorte. Keine Runtime-Quelländerung; vorherige 83
  Host-Python-Tests unverändert, keine neuen ROS-GTests/volle M2-Ausführung behaupten.
- Evidenz: evidence/m3-srt-n2-full-2026-11-06/ mit Plan, Manifesten, Journal-/Generation-
  Belegen, Source-/Age-/Loss-Tabellen, PCAP-Populationen, Cgroup-Projektionen und
  Raw-Hashes. Roh-PCAPs/Prefixes/Journale/Clocks lokal; keine vollen Inspect-/Env-Dumps.
  Intrinsic/M4 unverändert. Kein kontrollierter Ressourcen-/Transportvorteil behauptet.

**Weiter:** volle N2-Dauer/Seed-Ausführung für SRT und System-DDS dokumentiert;
DDS-N2-Altersgate und Realtime-PCAP-Clockqualifikation bleiben offen. Volle N1-
Matrizen, V2/langes N5, deterministisches N3, N4-Command-Phasen, andere Devices/
Offloads, kontrollierte Ressourcen und Age-/Pacing-/Reconciliation-/Security-Parität.
M3 in Arbeit, PR #2 bleibt Draft.

## Fortsetzung 2026-11-06: Capture-Retention und SRT N1 je 600 s/drei Seeds

- Vor erster N1-Ausführung Retention-Preflight: SRT N2 hatte je Endpoint
  125.447.816..125.572.581 Byte bei nominell 128.000.000 Byte rotierender Kapazität.
  Normale SRT-/DDS-M3-Runner nutzen nun gemeinsam 16 statt 8 Dateien à 16 MB,
  nominell 256.000.000 Byte. Rotation (Dateigröße/Anzahl/nominelle Bytes) im Manifest
  und Vergleichsguard gebunden. Kein fehlgeschlagener N1-Lauf/Retry versteckt;
  Kernelbuffer/Immediate/Snapshot/Offloads/Gates unverändert. Kein unbegrenzter
  Volumennachweis; Tcpdump-Dateischwellen können um einen Record überschritten werden.
- Separater UDP-Volumenprobe mit 1-MB-Schwellen: zwei Dateien behalten je Seite
  1.206 von 2.001 bekannten Records, obwohl Footer 2.001 captured/null Kerneldrops
  meldet. Bestehendes Captured/File-Gate lehnt korrekt ab. Vier Dateien behalten
  alle 2.001 mit exakter Native-ID-/Längen-Gleichheit, null Drops; App in beiden
  Fällen vollständig und Recovery-Control vorhanden. Kein Kernelverlust daraus
  ableiten; kontrollierter Capture-Mechanismus-Test, keine Transportabnahme.
- Eingefrorener SRT-N1-Plan: Seeds 1701/2903/4211 je 600 s, frische sequentielle
  Endpunkte, keine Rebuilds/Retries/Ersatzläufe/Policy-Änderungen. Alle drei Source-
  Fenster vollständig (600,093151/600,153512/600,141223 s). Je 300 SUCCEEDED/Effekte,
  insgesamt 900; null Expired/Failed/Rejected/UNKNOWN/unaufgelöste/not-admitted/
  übersprungene Intents. Max. lokale Terminalbeobachtung 923,544/264,239/467,177 ms.
  Keine Ausführungs-/Netzlaufzeitgrenze daraus ableiten.
- Sechs Journale integral/terminal identisch, Revision 3/Hash/Result/Generation
  pro Intent passend; Device-Generationen/Effekte je 300. Drei Source-Zusammenfassungen
  exakt reproduziert, alle sechs Conservation-Residuals je Fenster null. Produced/
  Published/Observer je Seed: 149.484/110.267/110.064, 150.038/111.112/111.047,
  150.036/111.381/111.300. Erste IMU-Quellrate 199,107 Hz, andere ca. 200 Hz;
  Ratenvariation/Verluste behalten, nicht normalisieren oder als WAN-Loss/FEC-Nutzen
  isoliert auslegen. Nicht alle produzierten Samples werden zugestellt.
- Source-fenced Publication-Age-Upper-Maxima IMU/Joints: 87/119, 63/83, 63/85 ms,
  unter unverändertem 250-ms-Gate. Origin Bridge-Ingress, keine DDS-Header-/Physical-
  Sensor-Age-Parität. PCAP-Kerneldrops und Native Reserve-/Copy-Verluste null;
  sechs PCAP-Populationen reconciled, kein universeller Completeness-Nachweis.
  Alle Realtime-PCAP-Fenster wegen Clock-Qualifikation unterdrückt, Native separat.
  Zwölf Cgroup-Phasen aus Projektionen exakt reproduziert.
- 161 Quellen während drei Läufen konstant; gegenüber d2912fc nur Capture-Helper,
  zwei Haupt-Runner und ein Guard-Test geändert. Acht installierte Binär-/SDK-
  Hashes und installierte Python-Bytes konstant; 56 Produktions-C++/Header/Proto-
  Quellen unverändert. 83 Host-Python-Tests bestanden, Retention-Mischkonfiguration
  negativ abgedeckt. Keine neuen ROS-GTests/volle M2-Ausführung behaupten.
  Keine SDK-/Wire-/IPC-/Deadline-/Lease-/Atomic-Start-/Replay-Policy-Änderung.
- Evidenz: evidence/m3-srt-n1-full-2026-11-06/ mit separatem Retention-Preflight/
  Probe, Plan, Manifesten, vollständigen Source-/Loss-/Age- und Terminalpopulationen,
  Journal-/Generationsbelegen, Cgroup-Projektionen und Raw-Hashes. Roh-PCAPs/
  Prefixes/Journale/Clocks lokal; keine vollen Inspect-/Env-Dumps. Intrinsic/M4
  unverändert; keine kausale Ressourcen-/Transportüberlegenheit behauptet.

**Weiter:** volle System-DDS-N1-Matrix; DDS-N2-Altersgate/Realtime-PCAP-Clockqualifikation,
V2/langes N5, deterministisches N3, N4-Command-Phasen, andere Devices/Offloads,
kontrollierte Ressourcen und Age-/Pacing-/Reconciliation-/Security-Parität bleiben
separat offen. SRT N1/N2 und DDS N2 sind als volle Dauer/Seed-Ausführung dokumentiert.
M3 in Arbeit, PR #2 bleibt Draft.

## Fortsetzung 2026-11-06: System-DDS N1 und N1/N2-Ausführungsmatrix

- Eingefrorener Default/System-DDS-N1-Plan: Seeds 1701/2903/4211, je 600 s,
  frische sequentielle eigene Endpunkte, Native v2/Immediate/Full-Snapshot/
  32.768-KiB-Kernelbuffer und 16×16-MB-Retention wie e3c5c70. Keine Rebuilds,
  Runtime-/Policy-/Capture-Änderungen, Retries oder Ersatzläufe.
- Alle drei Source-Fenster vollständig (600,115900/600,118402/600,132039 s).
  Pro Seed Attempts/SUCCEEDED/Effekte/Expired/Skipped: 297/296/296/1/3,
  297/296/296/1/3, 298/298/298/0/2. Insgesamt 892 Versuche, 890 Erfolge/Effekte,
  zwei Receiver-EXPIRED Revision 1 ohne Dispatch und acht übersprungene Slots.
  Keine UNKNOWN/unaufgelösten/not-admitted/rejected/failed Intents. Max. lokale
  Terminalbeobachtung 5.350,575/5.316,245/2.473,593 ms, kein Handler-/Netzlaufzeitbound.
- Sechs geschlossene Journale integral und terminal/immutable identisch, ohne
  fehlende/abweichende Records. Device-Generationen/Effekte 296/296/298; Expiry
  erhöht Generation nicht, spätere neue Intents folgen dem gleichen erwarteten
  Stand. Finale Timelines aus Original-Owner-Journalen exakt reproduziert;
  keine DDS-Timingzerlegung für fehlende/unklare/Recovered-Records erfinden.
- Alter: Seed 1701 **unqualifiziert**, vier beobachtete Clock-Steps, max.
  25,965389 ms und max. Offset-Abweichung 34,616970 ms. 17.809 IMU-/6.403 Joint-
  Callbacks clock-rejected (24.212 gesamt). Seeds 2903/4211 Shared-VM-Age-Estimates
  qualifiziert. Vollständige Histogramme/Clock-Reject-/Missing-Populationen erhalten;
  keine Gesamtaltersgrenze aus günstigem Teilset ableiten. N1-Altersgate bleibt offen.
- Produced/Received je Seed 150.010/112.123, 150.024/112.928, 150.026/111.710;
  Source-Raten und Callback-Defizite separat halten, kein isolierter WAN-Loss oder
  Transportvorteil. Sämtliche Realtime-PCAP-Fenster wegen Clock-Qualifikation
  unterdrückt. Native-Monotonic-Coverage separat qualifiziert. Alle PCAP-Kerneldrops/
  Native Reserve-/Copy-Verluste null, sechs PCAP-Populationen reconciled; kein
  universeller Completeness-/Physical-Delivery-Nachweis. Zwölf Cgroup-Phasen aus
  Projektionen exakt reproduziert.
- 161 Quellen entsprechen während aller Läufe und final e3c5c70. Acht ausgewählte
  installierte Binär-/SDK-Hashes und installierte Python-Bytes konstant; 56
  Produktions-C++/Header/Proto-Quellen unverändert. Ein VM-Boot in dieser Kohorte.
  Vorige 83 Host-Tests unverändert, keine neuen ROS-GTests/volle M2-Ausführung
  behaupten. Diese Fortsetzung ändert nur Evidenz/Planungsdokumentation.
- Evidenz: evidence/m3-dds-n1-full-2026-11-06/ mit Plan, Manifesten, Journal-/Generation-
  Audits, Original-Owner-Timelines, Source-/Age-/Clock-Populationen, Capture-Metadaten,
  Cgroup-Projektionen und Raw-Hashes. Roh-PCAPs/Prefixes/Journale/Clocks lokal;
  keine vollen Inspect-/Env-Dumps. Intrinsic/M4 unverändert.
- execution-matrix.json in dieser Evidenz fasst SRT N1/N2 und System-DDS N1/N2
  zusammen: alle vier Kohorten mit drei Seeds/je mindestens 600 s ausgeführt.
  Nur die Dauer/Seed-Ausführung ist damit abgeschlossen. Capture-Retention,
  Altersorigins/Modelle, Crypto, Pacing und Hostbedingungen unterscheiden sich;
  keine kausale Kosten-/Überlegenheitsbehauptung aus getrennten Kohorten.

**Weiter:** V2/langes N5, deterministisches N3 (DATA/FEC getrennt), N4-Command-Phasen,
DDS-N1/N2-Altersgates und Realtime-PCAP-Clockqualifikation, weitere Devices/Offloads,
kontrollierte Ressourcen und Age-/Pacing-/Reconciliation-/Security-Parität.
N1/N2-Dauer/Seed-Ausführung komplett dokumentiert; M3 weiterhin in Arbeit,
PR #2 Draft. Keine implizite Hardware-/Echtzeit-/Lossless-Freigabe.

## Fortsetzung 2026-11-06: N5 mit aktueller Capture-Konfiguration

- Separate, vor Start eingefrorene paced-DDS-N5-Kohorte: Seeds 1701/2903/4211
  je 300 s, simultaner Start, private frische sequentielle Endpunkte. 512-kbit/s-
  Root-TBF je Richtung, Burst 4096, Limit-Request 32768, Child-Netem-Queue 16;
  kein stochastischer Delay/Loss, Seeds nur Wiederholungslabels. Pinned JSON zeigt
  TBF Rate/Burst/normalisierte Latenz (448000), kein erfundenes Limit-Readback.
- DDS-Kandidat explizit paced-sensors: nur Sensorwriter asynchron/KeepLast(1),
  gemeinsamer 1600-Controller-Bytes/50-ms-Budget, 1200-Byte UDP/SHM. Control unverändert.
  Native Provider-Preflight vor jedem Lab in network-none, dessen Binärhash als
  neunter ausgewählter Hash eingefroren. XML/161 Sources/Install-Scripts konstant.
  Quellen dieser Kohorte entsprechen 1bf9bfe vor dem späteren SRT-Tooling-Patch.
- Alle drei paced-DDS-Läufe bestanden: je 150 SUCCEEDED/Effekte, gesamt 450;
  null Expired/UNKNOWN/unresolved/not-admitted/Skipped. Source/Callback je Seed
  75031/19216, 75027/19073, 75026/19188. Absichtliches Middleware-Pacing und andere
  Stufen nicht als isolierten WAN-Loss deuten. Alle Shared-VM-Age-Estimates
  qualifiziert, alle Realtime-PCAP-Fenster weiterhin unterdrückt. Sechs Journale
  stimmen überein, zwölf Cgroup-Fenster exakt reproduziert. Recorderverluste null.
- Iperf-Whole-Run-Offer ca. 128000,016/128019,300/128002,557 bit/s; Liveness-Polls
  positiv. Intervall/Setup/Total-Projektionen und Raw-Hashes erhalten, keine
  matched-window Delivery-/Loss-Garantie. Default/System-DDS-N5-Discovery bleibt offen.
- SRT-Runner fehlten diese Competitor-Gates. Patch 80c5590 ergänzt Poll-Liveness
  und denselben Offered-Load-Validator. 83 Host-Tests bestanden. Separater Negativtest
  beendet ausschließlich den Client im eigenen Robot-Container nach echtem
  Measurement-Marker: erwartetes failed/competitor-exited beobachtet. Zusätzlicher
  Capture-Analysefehler wegen absichtlich fehlender Endpoint-Fenster; keine positive
  N5-/Capture-/Journal-Abnahme aus diesem unterbrochenen Development-Fall behaupten.
- Danach separater SRT-N5-Plan, Quellen bei 80c5590 eingefroren. Seed 1701 bestanden:
  131 SUCCEEDED/Effekte, 19 Skipped, null unresolved. Seed 2903 **fehlgeschlagen**:
  PCAP-Kerneldrops Robot 2672/Operator 2637. Application-Fenster endet mit 104
  bestätigten Effekten, 105 Versuchen, 45 Skipped und einem offenen Intent 105.
  Seed 4211 wegen Fail-fast nicht ausgeführt, kein Ersatzlauf/Retry/Gate-Waiver.
- Intent 105: Senderjournal UNKNOWN/reconcile-required, Revision 0, ungültiges
  Result; Receiver ohne Eintrag. 104 gemeinsame Erfolgsrecords stimmen überein,
  final beobachtete Generation/Effekte 104. NOT_FOUND/Abwesenheit nicht als
  Nichtausführung/Expiry/Erfolg auslegen. Reconcile-required bleibt
  unsicher, obwohl die Verbindung später wieder ready ist; kein automatischer Replay.
  Begin-/End-Session-IDs und Generationen sind identisch; daraus keinen belegten
  Session-ID-Wechsel oder eindeutige UNKNOWN-Ursache behaupten.
- Native UDP/PCAP-Multiset-Vergleich identifiziert exakt alle 2672/2637 fehlenden
  Records eindeutig in drei späten Zeitclustern; große Cluster ca. 2,7/3,1 s.
  Native Reserve-/Copy-Verluste null und beide Phasen unabhängig qualifiziert.
  Das rettet keine fehlgeschlagene PCAP-/Gesamtabnahme. Sampler-Gaps beweisen keine
  globale Pause; keine eindeutige Scheduler-/Storage-Ursache behaupten. Acht
  Cgroup-Fenster und beide Source-Summaries der ausgeführten SRT-Fälle reproduziert,
  fehlgeschlagenes App-Counter-Result nicht als vollständige Qualifikation verkaufen.
- Evidenz getrennt: evidence/m3-dds-paced-n5-v2-2026-11-06/ und
  evidence/m3-srt-n5-v2-2026-11-06/ inkl. Development-Negativfall, unverändertem
  fehlgeschlagenem Plan, Raw-Hashes, Closed-Journal-Audit und Capture-Gap-Analyse.
  Keine Runtime-C++-/SDK-/Wire-/IPC-/Deadline-/Lease-/Replay-Policy-Änderung,
  keine neuen ROS-GTests/volle M2-Ausführung; Intrinsic/M4 unverändert.

**Weiter:** SRT-N5-Recorderverlust untersuchen/qualifizierbare Aufnahme sicherstellen;
Intent-105-Unsicherheit beibehalten und Kontextwechsel-/Lastverhalten gezielt
qualifizieren. N3 deterministische DATA/FEC-Verluste, N4-Command-Phasen, Default-DDS-
N5-Discovery, bestehende Age-/Realtime-Clock-Gaps und kontrollierte Semantik-/Security-/
Ressourcenparität offen. M3 nicht abgeschlossen, PR #2 bleibt Draft.

## Fortsetzung 2026-11-06: Recorder-/Command-Diagnostik

- Optional `run_m3.py --recorder-diagnostics`: begrenzte 100-ms-/proc-Beobachtungen
  von tcpdump mit PID/Startzeit, State, Scheduler-/Context-Switch-/verfügbaren
  I/O-Zählern und monotonen Read-Brackets. Default aus, 75000-Sample-Grenze;
  fehlende/gesperrte Felder explizit, keine Completeness-/Ursachenbehauptung.
- Network-none/Loopback-Kontrollen: Baseline 2076 Datagrams/Receipts/PCAP-Records,
  null Drops. Bekannte ca. 1,5-s-SIGSTOP-Pause: 2116 Receipts, 1310 PCAP-Records,
  Kernel-Dropzähler 1612, 14 T-State-Samples; Zero-Drop-Gate verwirft und Recovery-
  Marker nach SIGCONT erfasst. Loopback-Filterzähler doppelt, keine Datagramm-/
  Frame-Äquivalenz oder Erklärung des früheren N5-Verlusts ableiten.
- Separates N5-Development bei 013927f, 60 s: beide PCAPs ohne Drops, zwei
  bestätigte Effekte, dritter Intent unresolved/Sender UNKNOWN, Receiver ohne
  Record, 27 Skipped. Harness-passed erlaubt Development-Uncertainty und ist keine
  N5-Command-Abnahme. Unsicherheit damit auch ohne Recorderverlust beobachtet;
  keine eindeutige Transition/Ursache, kein Replay/Expiry/Erfolg erfunden.
- SRT-Driver ab 56b7b8a nutzt bestehenden bounded Status-History-Helper: erste
  32/letzte 32 Polls, Omission-Zähler, State/Reason/Revision/Found und Local-/Peer-
  Errors. Admission/Cadence/Terminalklassifikation unverändert. Separates 30-s-
  N5-Development: 12 Erfolge/Effekte, drei Skipped, null unresolved, null PCAP-Drops;
  86 Statuspolls von LOCAL_QUEUED bis SUCCEEDED erhalten. Kein Ersatz für die
  fehlgeschlagene Frozen-Kohorte oder deren nicht ausgeführten dritten Seed.
- Echte N5-Endpunkte verweigern /proc-I/O-Counter nach tcpdump-Privilege-Drop
  (PermissionError), wchan=0 nicht als verfügbare Waitsite interpretieren. Kein
  zusätzliches Capability/anderer tcpdump-User in N5. Loopback-Kontrolle mit
  explizitem -Z root ist nur eine Diagnosekontrolle, deren I/O-Sicht nicht auf N5
  übertragen. Scheduler/States/Samplegaps verfügbar; ein D-State-Sample beweist
  keine Storage-Ursache. Gegenüber früheren Kohorten zusätzlicher Observer-Workload.
- 88 Host-Python-Tests bestanden; ROS/SRT-Development validiert Adapter. Keine
  neuen ROS-GTests/volle M2-Ausführung; acht ausgewählte installierte Dateien
  nach Läufen unverändert zur früheren N5-Freeze geprüft. Keine Production-C++-,
  SDK-/Wire-/Deadline-/Lease-/Replay-Änderung. Evidenz mit unveränderten Manifesten,
  Sample-Replay, Read-only-Journal-Audits/Raw-Hashes:
  evidence/m3-recorder-diagnostics-2026-11-06/. Rohdaten bleiben lokal.

**Weiter:** Command-Invalidation-/Transport-Handoff-Grenzen gezielt instrumentieren,
Live-/Shutdown-/Recovery-Transitions unterscheidbar machen; Recorderverluste mit
opt-in Beobachtungen korrelieren, falls erneut beobachtet. Original-Intent 105
bleibt unsicher; SRT-N5-Gesamtqualifikation, Default-DDS-N5, N3/N4 und bestehende
Age-/Clock-/Security-/Ressourcengates offen. M3 in Arbeit, PR #2 Draft; M4 unverändert.

## Fortsetzung 2026-11-06: Command-Handoff-Ursache beobachtet und behoben

- 381dfa8 ergänzt opt-in `--command-diagnostics` / ROS-Parameter
  `command_diagnostics`: fester 256-Event-Trace, Producer schreiben mit Try-lock
  ohne Wait/I/O/Callbacks, Loss-Zähler explizit. ROS-Pump drainiert JSON; nach
  Endpoint-Join finale Attempted/Dropped-Bilanz. Events für Coordinator-Invalidation
  (Sessionwechsel vs. Abandoned-Submit), Admission/Handoff, Transportdrops,
  SDK-Acceptance und Lifecycle. Aktuelle und gespeicherte Owner-Epochen bei
  UNKNOWN separat. Kein Wire-/Worker-IPC-Formatwechsel; Default aus.
- Separates vorab fixiertes 90-s-N5-Development (Seed 2903) bei 381dfa8:
  zehn Erfolge/Effekte, ein offener Intent 11, 34 Skipped, null PCAP-Drops.
  Trace: Envelope-Erstellung für 11 verwirft `clock_unqualified` vor SDK-Handoff.
  Letzter Driverpoll bleibt LOCAL_QUEUED; späterer Teardown-Sessionwechsel fordert
  Invalidation an, geschlossenes Journal danach UNKNOWN/reconcile-required.
  Keine nachträgliche Expiry/Erfolg/Nichtausführung oder Replay erfinden.
- Originalmanifest bleibt failed: erster Tracevalidator erwartete fälschlich
  exakt zwei Bridge-Logs. Tatsächlicher Setup-Linkreset erzeugt drei Inkarnationen;
  alle drei Traces integral, 43/4/4 Events, null Drops. Reanalyse getrennt, kein
  Umetikettieren des ursprünglichen Manifests. Validator ab 899a6eb prüft jede
  Inkarnation und beide Rollen, statt die legitime Setup-Inkarnation abzulehnen.
- 899a6eb hält noch nicht ans SDK übergebene Commands bei softem Clock-Ausfall in
  einem reservierten Ingress-Slot. Dieser zählt innerhalb der bestehenden 64/
  56-Grenzen, FIFO bleibt erhalten. Original-Proof/Origin/Deadline unverändert;
  pro Versuch Liveness/Context/Deadline prüfen. Probe-/Socket-Owner laufen weiter.
  Expiry/Revocation/Context-Loss/andere Envelopefehler weiterhin fail closed;
  kein neuer Admit, keine Budgetverlängerung und kein SDK-Command-Replay.
- Kontrollierter nativer Regressionstest mit 150-ms-Probe-Lifetime schlägt mit
  altem Transport erwartungsgemäß fehl (Command discarded statt Clock-Wait).
  Fix auf IPv4/IPv6: Deferred/Ingress-Charge, One-shot-Ticket, genau ein späterer
  SDK-Handoff mit Original-Origin/5000-ms-Budget. Zweites gehaltenes Command wird
  nach Worker-Revocation verworfen und auch nach Clock-Erholung nicht gesendet.
- Separate neue 90-s-N5-Development-Ausführung bei 899a6eb: 32 Erfolge/Effekte,
  13 Skipped, null unresolved/UNKNOWN/PCAP-Drops. Zwei Clock-Deferrals, beide
  Intents erfolgreich; SDK-Accepts 32. Traces 108/4/4 Events, null diagnostische
  Drops; 32 gemeinsame Journalrecords stimmen überein, Generation/Effekte 32.
  Geänderte kompilierte Runtime plus Trace/Recorder-Observer; keine kausale
  Leistungs-/Kostenvergleichsbehauptung und kein Ersatz für frühere Abnahme.
- Finale neue Builds: 68 SDK-/Native-CTests, 36 ROS-reported (32 GTests plus
  Wrapper) und 92 Host-Python-Tests bestanden. Kein neuer voller M2-Acceptance-
  Lauf behauptet. Consumer wegen öffentlicher Config-Layout-Erweiterung neu gebaut.
- Historische Intents 105 und 3: Immutable/read-only Journal-Owner-Checks stimmen
  mit jeweiligem Operator-Checkpoint überein, belegen aber keine eindeutige alte
  Transition. SRT-Checkpointlabels sender/receiver sind Sensor-Richtung; Command-
  Sender ist Operator/Sensor-Receiver. Historische Unsicherheit bleibt erhalten.
- Evidenz: evidence/m3-command-handoff-2026-11-06/ mit unveränderten Manifesten,
  Freeze/Binding, Original-Trace-Logs, Reanalyse, Journal-/Source-/Raw-Hashes,
  Expected-Failure/positiven Tests. Roh-PCAP/Prefixes/Journale/Clocks lokal;
  keine kompletten Inspect-/Env-Dumps/Secrets.

**Weiter:** Neue Runtime in eigenständiger langer SRT-N5-Kohorte qualifizieren;
Original-Recorderverlust und alte UNKNOWNs bleiben offen. Danach N3/N4 und
bestehende Default-DDS-N5-/Age-/Clock-/Security-/Ressourcengates. M3 weiterhin in
Arbeit, PR #2 Draft; Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-06: Lange N5-Kohorte und unabhängige Trace-Lanes

- Neue eingefrorene Kohorte ffd4fb2 / Command-Fix 899a6eb: drei geplante 300-s-
  SRT-N5-Fälle, Labels 1701/2903/4211, Command-/Recorder-Diagnostics und native
  V2-Aufnahme explizit an. 168 Quellen, acht ausgewählte installierte Dateien
  und installierte Scriptbytes bis Kohortenende konstant. Frische private Labs,
  keine Retries/Ersatzfälle/Tuningänderungen. N5 ohne stochastischen Loss/Delay;
  Labels keine unabhängigen Random-Loss-Samples.
- 1701 bestanden: 115 SUCCEEDED/Effekte, 35 Skipped, keine Expiry/Uncertainty/
  Nonadmission, keine PCAP-Drops. Traces 359/4/4 Records vollständig. Vier
  Clock-Deferrals, alle entsprechenden Intents erfolgreich. Max. gemessener
  Publikations-Age-Upper-Bucket 187 ms innerhalb 250-ms-Gate.
- 2903 **fehlgeschlagen** wegen Diagnostic Completeness: Operatortrace 397 von
  398 Attempts, Dropped=1, Sequenz 235 fehlt; keine Rekonstruktion. Dennoch
  Application-Fenster vollständig: 129 SUCCEEDED/Effekte, 21 Skipped, keine
  Expiry/Uncertainty/Nonadmission, null PCAP-Drops; ein Clock-Deferred-Intent
  erfolgreich. Robot-Traces vollständig, je vier Records. Max. Age-Bucket 227 ms.
- 4211 wegen Fail-fast nicht ausgeführt. 244 bestätigte Effekte, vier geschlossene
  Journale identisch inkl. Result-Rate/Generation, acht Cgroup-Fenster und beide
  Source-Summaries exakt reproduziert. Source/Published/Observer: 75032/26236/26236
  und 75033/27637/27637. PCAP Captured/Filter/File je Endpoint 108712 / 109964,
  Kerneldrops und native Reserve-/Copy-Verluste null. Realtime-PCAP-Fenster bleiben
  clockbedingt unterdrückt. Keine Performance-/Physical-Delivery-Inferenz.
- Archivierung erhält beide gemeldeten image_platform_id-Werte: einmal Manifest-
  Digest, einmal Config-artig. Immutable Config.Image-Referenz und aufgezeichnete
  Container.Image-Werte sind in beiden Fällen identisch, Boot ebenfalls. Keine
  Rohfelder überschrieben/kanonische Config-ID erfunden; Ressourcenkosten nicht
  unter Annahme identischer Roh-Platform-ID-Felder vergleichen. Inspect-/Env-Dumps
  bleiben lokal, im Archiv nur selektierte Isolation-/Image-/Clock-Projektionen.
- Alter Tracebuffer verlor bei Full ODER Mutex-Contention; kombinierter Zähler
  belegt keinen eindeutigen Mechanismus. dc4131c entfernt den Contention-Pfad:
  zwei feste SPSC-Lanes, jeweils 128 Records, total weiterhin 256. Je Owner genau
  ein Producer, ein externer Consumer, Producerwechsel nur nach Join; Acquire/
  Release-Indizes sichern Slots. Kein Producer-Mutex/Retry/Callback/I/O. Full-
  Drops weiterhin explizit und Diagnostic-Gate unverändert strikt. Andere
  Reservationsverteilung = neuer Observermodus, braucht eigene volle Kohorte.
- Validiert: fünf fokussierte SDK-/Native-Tests (Trace/Overflow/Reservation,
  IPv4/IPv6 Endpoint-Recovery und Clock-Deferral/Revocation), ergänzender Test
  0a1c1b0 mit 2000 garantiert interleaved Observations bei maximal einem offenen
  Event je Lane und null Loss; 36 ROS-reported Tests und 92 Hosttests bestanden.
  Voriger voller SDK-Lauf 68 Tests gehört zum Kohortenruntime; kein erneuter
  voller 68-Test-/M2-Acceptance-Lauf nach Trace-Patch behauptet. Consumer neu gebaut.
- Getrennter 15-s-N0-Smoke des neuen Tracebuffers: acht Erfolge/Effekte, Traces
  34/4/4 vollständig, null Trace-/PCAP-Drops. Keine N5-Qualifikation daraus.
  Wire/Worker-IPC/Journal-/Command-/Deadline-/Lease-/Replay-Policy unverändert.
- Evidenz: evidence/m3-srt-n5-fixed-2026-11-06/, Originalplan/-manifeste unverändert,
  Raw-/Source-/Binary-Hashes, read-only Journale, Capture-/Trace-Reanalysen,
  Cgroup-Projektionen, separater trace-buffer-fix/ mit Smoke/Tests/Freeze.

**Weiter:** Neue vollständige N5-Kohorte für den unabhängigen Tracebuffer einfrieren.
Bisherige Kohorte bleibt failed, dritter Fall unexecuted; nichts ersetzen/waiven.
N3/N4, Default-DDS-N5 und Age-/Clock-/Security-/Ressourcengates weiter offen.
Historische Recorderverluste und UNKNOWNs erhalten; M3 in Arbeit, PR #2 Draft,
Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-06: SPSC-N5 mit live beobachteter Unsicherheit

- Neue vorab eingefrorene Kohorte 649b4ce: Labels 1701/2903/4211 je 300 s,
  unabhängige SPSC-Lanes, beide Diagnostik-Observer und native V2-Aufnahme aktiv.
  168 Quellen, acht ausgewählte Dateien, installierte Scriptbytes, immutable
  Image-Referenz und gemeinsame VM-/Time-Namespace-Proof vorab fixiert.
- Erster Fall **failed am Command-Outcomes-Gate**, weitere zwei nicht ausgeführt.
  Originaler Harness bleibt development-passed (dort unresolved erlaubt),
  Originalkohorte failed; keine Umklassifikation/Retry/Ersatzfälle.
- 15 Versuche: 14 SUCCEEDED/Effekte, Intent 15 unresolved, 135 Skipped,
  keine Nonadmission. Senderjournal 15 UNKNOWN/reconcile-required, Revision 0,
  ungültiges Result; Receiver ohne Record. 14 gemeinsame Erfolge identisch inkl.
  Result-Rate/Generation, Device Generation/Effekte 14. Kein Nichtausführungs-
  beweis/Expiry/Erfolg/Replay aus NOT_FOUND oder Abwesenheit erfinden.
- Trace: SDK-Accept 15 bei ca. 34,039 s, Robot Sessionchange/Invalidation ca.
  37,517/37,519 s; Operator bei 42,470 s, Completion 42,478 s. Erstes beobachtetes
  UNKNOWN 43,305 s mit passender Entry-/Current-Owner-Epoche. Live-Kontextverlust
  innerhalb des Messfensters, nicht nur Teardown. Bestehende Events erklären
  den initiierenden Socket-/Session-Close noch nicht; keine eindeutige Ursache.
- Alle Traces vollständig: Operator 1496, Robot 4/7, Dropped überall 0. Beide
  PCAPs Captured/Filter/File exakt 150432, null Kernel-/Native Reserve-/Copy-Loss.
  Sechs Source-Bilanzen und vier Cgroup-Fenster reproduziert. Produced 74987,
  Published 11864, Observer 11863; Stage-Defizite nicht isolierter WAN-Loss.
  Max. gemessener Age-Upper-Bucket 238 ms innerhalb 250, Realtime-PCAP-Fenster
  weiter clockbedingt unqualifiziert. Keine Kosten-/Performance-/Physical-Inferenz.
- fd0107e ergänzt opt-in Cause-Events: session_action (30) mit SessionError und
  Close-Control/Close-Sensor/Flush-Bits 1/2/4; link_lost (31) mit Channel 0/1
  sowie Socketstate/Security-Timeout/Epoll-/Provider-/Decode-Ursache. Transport-
  Stopping trägt TransportFault. Nur schließende Actions, kein Sensor-Error-Flood.
  Alte Traces lesbar; Detailfeld erweitert Layout, Consumer neu gebaut. Kapazität
  weiterhin 256 Records, 128 je Owner; keine Producer-I/O/Callbacks/Policyentscheidung.
  Wire/IPC/Journal-/Deadline-/Lease-/Start-Fence-/Replay-Policy unverändert.
- Fünf fokussierte SDK-/Native-Tests bestanden, inkl. kontrolliertem Peer-Close
  auf IPv4/IPv6 mit Link-Cause und Session-Close vor Receiver-Teardown; 36 ROS-
  reported Tests und 93 Hosttests bestanden. Kein neuer voller 68-Test-/M2-Lauf
  behauptet. Separater 15-s-N0-Smoke: acht Effekte/Erfolge, Traces 42/5/5 integral,
  neue Cause-Felder ausgeübt, null Trace-/PCAP-Verlust. Keine N5-Qualifikation.
- Evidenz evidence/m3-srt-n5-spsc-2026-11-06/ mit unveränderten Plänen/Manifesten,
  Incident-Zeitpunkten, Read-only-Journalen, Source-/Binary-/Raw-Hashes, nativer
  Reanalyse und Cgroup-Projektionen; spätere cause-trace/ Tests/Freeze/Smoke
  getrennt. Rohcaptures/Prefixes/Journale/Clocks lokal, keine kompletten Inspect-/
  Env-Dumps oder Credentials publiziert.

**Weiter:** Live-N5-Reset mit Cause-Events gezielt reproduzieren und Initiator
qualifizieren, bevor erneut eine vollständige Kohorte versucht wird. Alte
UNKNOWNs/Recorderverluste erhalten. N3/N4, Default-DDS-N5 und Age-/Clock-/Security-/
Ressourcengates offen; M3 in Arbeit, PR #2 Draft; Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-06: Einmaliger Cause-Repro und Admission-Loss-Test

- Vorab festgelegter einzelner 300-s-N5-Diagnoselauf (Label 1701) bei 4a49595,
  getestete Cause-Event-Runtime fd0107e, native V2-Aufnahme und beide Observer an.
  Source-/acht ausgewählte Binärinventare vor/nach Lauf konstant. Keine Wiederholung,
  Ersatzfälle oder Tuning. Ergebnis **kein aktiver Reset beobachtet**; nicht als
  Erklärung früherer Fehler oder komplette N5-/M3-Kohorte auslegen.
- 133 Attempts/SUCCEEDED/Effekte, 17 Skipped, null unresolved/UNKNOWN/nonadmission;
  Traces 417/5/5 integral und null Trace-/PCAP-Verlust. Setup-/Teardown-Close-
  Events erhalten, aber vom aktiven Command-Fenster getrennt klassifiziert.
  133 gemeinsame Journalrecords stimmen in Immutable-/Statusfeldern inkl. Result-
  Rate/Generation überein, read-only/immutable mit Hashkontrolle.
- Produced/Published/Observer 75041/2327/2327, Defizite explizit und nicht isolierter
  WAN-Loss. Max. Publikations-Age-Upper-Buckets IMU 162 / Joint 159 ms innerhalb
  250-ms-Modellgate. Source-Summary und vier Cgroup-Fenster exakt reproduziert,
  sämtliche Realtime-PCAP-Fenster weiter clockbedingt unterdrückt. Keine Kosten-/
  Performance-/Physical-Delivery-Behauptung aus diesem Einzellauf.
- 32ccfc6 ergänzt ausschließlich einen nativen Admission-before-commit-Peer-Loss-
  Regressionstest: Transportempfang/Receiver-Journalbarriere abwarten, Receiver
  stoppen und neue Epoch/Session verbinden. UNKNOWN/reconcile-required Revision 0
  ohne gültiges Result bleibt trotz Peer-NOT_FOUND und nach ursprünglichem
  5000-ms-Budget erhalten; genau ein SDK-Handoff, kein Replay/Effekt. Kontrollierte
  Barriere liefert bekanntes Faultmodell, keinen Initiatorbeweis für den alten
  spontanen N5-Reset. Bestehender Worker-Hook, keine neue Produktionsschnittstelle.
- Beide Command-Endpoint-CTests IPv4/IPv6 bestanden, jeweils 195 Checks inkl.
  neuer Admission-Loss-Szene und bestehender Normal-/Result-Recovery-/Running-
  UNKNOWN-/Timeout-/Shutdown-Szenen. Kein neuer kompletter SDK-/ROS-/Host-Testlauf
  behauptet; Produktionscode/Binärinventare unverändert, nur Testquelle geändert.
  Admission-Phasen-Faultcoverage, keine komplette N4-/ROS-/Hardware-Abnahme.
- Evidenz evidence/m3-n5-close-cause-2026-11-06/ mit unveränderten Plänen/Manifesten,
  aktivem Cause-Fenster (leer), ursprünglichen Trace-Logs, ausgewählten Journal-
  Vergleichsfeldern, Cgroup-Replay und Raw-Hashes sowie separatem Native-Testlog.
  Rohcaptures/Prefixes/Journale/Clocks lokal; keine Inspect-/Env-Dumps/Secrets.

**Weiter:** Prospektiv begrenzten Diagnose-/Faultplan zur Unterscheidung Provider-
Verlust vs. lokale Session-/Clock-Entscheidung verwenden; Initiator bleibt offen.
Keine günstigen Läufe anstelle gescheiterter Kohorten einsetzen. Historische
UNKNOWNs/Recorderverluste erhalten; vollständiges N5/M3, N3/N4, Default-DDS-N5 und
Age-/Clock-/Security-/Ressourcengates offen. PR #2 Draft; Intrinsic/M4 unverändert.

## Fortsetzung 2026-11-06: Flow-isolierte CONTROL-Stille und gerichteter Fault

- Keine weitere Zufallswiederholung: Native V2-Rohdaten des gescheiterten SPSC-N5-
  Falls read-only analysiert. Neuer Tooling-/Testcommit be70a6a:
  tools/m3_control_liveness.py prüft Capture-/Clock-Proof, Version/Interface/
  Counter/Hash und trennt UDP-4-Tuple plus SRT-Destination-Socket-ID. Keine
  Payload-Entschlüsselung; ID 0 nicht etablierte Connection-Identität, Routing-
  Identifier keine Authentizitätsgarantie. GSO/VLAN/über-MTU/kurze CONTROL-Header
  werden verworfen, Fenstergrenzen/Zensierung explizit.
- Alter operator→robot-Flow zuletzt an Robot bei 32,509061932 s beobachtet,
  Robot SessionChange 37,517303435 s: 5,008241503 s beobachtete Stille.
  Reverse-Flow zuletzt an Operator 37,468471351 s, SessionChange 42,469670811 s:
  5,001199460 s. Voll beobachteter operator→robot-Interarrival-Gap ca. 5,127 s
  an beiden Hooks. Neue Handshakes/Reconnect-IDs nicht dazugezählt. Native-Hashes
  identisch zum alten Archiv, keine Rekonstruktion/Umklassifikation.
- Passend zum Default-Peer-Idle 5000 ms im gepinnten Provider 52be7c86… . Relevante
  Source-Dateien stimmen bytegenau mit Pin überein. Kein historischer Per-Socket-
  Readback, keine eindeutig belegte interne Idle-Branch-/Initiatorursache.
- Qdisc-Root-Delta über ganzen Lauf: Robot 1755730, Operator 331. Child-Counter
  überlappen und werden nicht summiert; keine Flow-/Zeitfenster-Loss-Zuordnung.
  Tap im qualifizierten Fixture hinter geprüftem Egress-Qdisc: SDK-Scheduling,
  Socket-/Queue-Verhalten und Pre-Hook-Qdisc-Loss bleiben offen, nicht pauschal
  WAN- oder Providerfehler behaupten.
- Neuer nativer Loopback-UDP-Gate-Test: CONTROL-Handshake bidirektional, danach
  nur listener→caller-Reply-Datagrams droppen; SENSOR direkt, beide Runtimeowner
  bis Fault aktiv. Provider-Control-Loss vor Session-Close ohne lokale Protocol-/
  Clock-Close-Ursache, Reverse-Forwarding bleibt positiv, Trace-Drops null.
  IPv4/IPv6 nach jeweils beobachteten 5004 ms; 631/619 Replies gedroppt, 213/208
  Reverse-Datagrams forwarded. Timeouts/Produktionscode/Dependency unverändert,
  keine globalen Netzwerk-/Qdisc-Eingriffe. Bewiesener kontrollierter Mechanismus,
  keine Gleichsetzung mit dem historischen Initiator/Pre-Hook-Ort.
- Beide Transport-Owner-CTests bestanden inkl. bisheriger Lifecycle/Cadence/
  Reconnect-Szenen (beobachtet 462/459 Checks); 98 Host-Python-Tests bestanden.
  Kein neuer voller SDK-/ROS-/M2-Lauf behauptet. Nur Analyse-/Testquellen geändert.
- Evidenz evidence/m3-control-silence-2026-11-06/ mit beidseitigen Flow-Fenstern,
  selektierten Altflows, Quellen-/Rohhash-Prüfung, Native-/Python-Testlogs und
  Grenzen. Keine PCAP-Payloads/Secrets/Inspect-/Env-Dumps publiziert.

**Weiter:** Unter vorab begrenztem Diagnoseplan Provider-TX-/ACK-/Queue-Beobachtungen
mit Operator-Egress korrelieren; Scheduling vs. Socket/Qdisc unterscheiden, bevor
Verhalten geändert wird. Historischer Initiator und vollständige N5-/M3-Abnahme
bleiben offen; alte UNKNOWNs/Fehler erhalten, N3/N4/Default-DDS-N5/Age-/Clock-/
Security-/Resource-Gates unverändert. PR #2 Draft, Intrinsic/M4 unberührt.

## Fortsetzung 2026-11-06: Begrenzte CONTROL-Providerdiagnostik

- Neue optionale `TransportConfig::provider_diagnostics`, ROS-Parameter und
  Runner-Flag `--provider-diagnostics`, Default aus. CONTROL alle nominell 100 ms
  und vor Close im Drop-Pfad; `srt_bstats(...,0)` ohne Counter-Clear, tatsächliches
  Peer-Idle-Readback, Read-Brackets, Owner/Generation/Socket, Verfügbarkeit/Fehler,
  kumulative DATA/ACK/NAK/Bytes plus Buffer/Flight/RTT-Gauges. Separater SPSC-Puffer
  128 Records, Lifetimebudget 75000; Verlust/Exhaustion explizit und Runnerfehler.
  ROS serialisiert außerhalb des Owners, Finalstatus nach Join. Public Config
  geändert, SDK und alle ROS-Consumer rebuilt. Kein Policy-/Timeout-/Pin-Change.
- Parser hält beide Read-Brackets pro Delta, trennt Socketidentitäten und
  unavailable Samples, prüft Accounting und meldet mögliche 32-bit-Sättigung.
  SDK-Locks/Bookkeeping beeinflussen Timing; kein Nonblocking-/Zero-Overhead-
  Versprechen. Counter erfassen nicht Keepalive/Handshake/ACKACK, beweisen weder
  UDP-Stille noch Delivery. RTT 0 kann fehlender Estimate sein.
- 105 Hosttests, voller SDK-CTest 69/69 und ROS 36 reported Tests bestanden.
  Native gerichtete CONTROL-Stille mit Diagnostik IPv4/IPv6: 5005/5003 ms,
  tatsächliches Idle-Readback 5000 ms, 788/781 Checks; Counterwachstum trotz
  bekannter Gate-Drops und flacher Caller-DATA-RX nach Settling nachgewiesen.
- Prospektiver Plan, genau ein N0-Smoke und ein N5-90-s/Seed-1701-Lauf; keine
  Random-Retry. Quellstand 0ace537 (SDK/ROS eedf5d3), Sources/Install-Matches und
  acht Runtimehashes vorher/nachher gleich. N0 8 Erfolge/Effekte, keine UNKNOWNs;
  Provider 271/23/226 vollständig. N5 39 Erfolge/Effekte, 6 Slots übersprungen,
  keine UNKNOWNs; Provider 974/24/959 und Commandtrace 135/5/5 vollständig,
  null Drops/Exhaustion. Kein aktiver CONTROL-Loss/Close reproduziert; daher nur
  Instrumentierungsvalidierung, keine historische Initiatorzuschreibung/Fix.
- N5 max beobachteter Startgap 113,283167 ms, Readspan 0,673250 ms, keine Bounds.
  PCAP 39550 Records/Filter je Endpoint, zero Kerneldrops; Native 39598/39603,
  zero Reserve-/Copyverluste bei separaten Populationen/Intervallen. Realtime-
  PCAP-Fenster weiter withheld. N5 Source/Published/Observer 22534/7173/7173;
  Sensordefizit erhalten, keine Performance-/Lossless-Behauptung.
- Evidenz evidence/m3-provider-diagnostics-2026-11-06/ mit Originalmanifesten,
  Diagnoselogs, Outcomes, Accounting, Testlogs, Prospektivplan und Rohhashes.
  Payloads/Prefixes/Journale/Clocks lokal, keine Secrets/Inspect-/Env-Dumps.

**Weiter:** Mit eingefrorener Diagnostik einen begrenzten Plan zur Trennung von
Provider-Scheduling/Socket-Send und Post-Qdisc-CONTROL verfolgen. Historischer
Initiator/UNKNOWNs, volle N5-/M3-Abnahme, N3/N4/Default-DDS-N5/Age-/Clock-/Security-/
Ressourcengates offen. Alte Fehlläufe unverändert; PR #2 Draft, Intrinsic/M4 unberührt.

## Fortsetzung 2026-11-06: CONTROL-only Egress-Faultharness, Versuch fehlgeschlagen

- Neuer opt-in Runner `--control-egress-fault operator|robot`, nur N0 >=45 s mit
  Command-/Provider-/Native-Diagnostik. Dedizierter tc-egress-u32/gact-Drop auf
  owned eth0, IPv4 UDP, Peer-/32 und CONTROL-Port 10080; SENSOR aus Selektor
  ausgeschlossen. Nach einem Drittel der Dauer, sechs Hostsekunden bis Restore;
  VM-Brackets um tc, Filtercounter und leeres Restore-Readback. Keine Default-/
  Policy-/SDK-/ROS-/Provideränderung. Kein N4-Phasen-/Historischer-Ursachenbeweis.
- Read-only-Analyzer für gepinntes Handle/Wire-ID-Mapping, alte Socket-/Tuple-
  Identität, vollständiges Native-v2/Common-Clock-Fenster und nur benachbarte
  verfügbare Providerdeltas mit beiden Reads komplett im aktiven VM-Intervall.
  Reverse-CONTROL/SENSOR/Restore separat. Host-getestet, live nicht validiert.
- Prospektiv genau ein 45-s-N0/Seed-1701-Versuch, b0e2204, alle 178 Sourcehashes
  passend; acht Runtimehashes vorher/nachher identisch zum vorigen Testbuild.
  Lokal .local/m3/20261106T203905001506Z. Filter erfolgreich installiert, aber
  `tc ... filter show ... pref 49152` lässt `pref` im JSON aus. Validator nahm
  fälschlich Pflichtfeld an: `unexpected CONTROL filter`, Abbruch vor verifiziertem
  Sechssekundenintervall/Restore. Initialcounter 0, kein Lifetimecounterbeweis.
- Originalmanifest FAILED erhalten, inklusive sekundärer fehlender Endpoint-
  Measurements und finaler Command-/Providerstatus. Keine Rekonstruktion/Rescue.
  Beide Container und Netzwerk erfolgreich entfernt. Kein zweiter Liveversuch.
- Parser akzeptiert fehlendes pref nur im festen scoped Query; explizit falsches
  pref/Protocol/Kind/Action/Counter weiter Fehler. Originalreadback als Fixture.
  Install-Readbackfehler entfernt Filter vor Raise, Finalstatsfehler ebenfalls
  im finally mit Restorecheck. Fehlerpfade getestet. 112 Hosttests vor Versuch,
  115 nach Fix bestanden, Syntaxchecks bestanden. Keine frischen SDK-/ROS-/M2-
  Tests behauptet; Runtime unverändert (vorherige 69 SDK/36 ROS gelten dafür).
- Evidenz evidence/m3-control-egress-fault-2026-11-06/ mit Plan, Originalmanifest,
  tc-/Fehler-/Diagnose-/Cleanup-Logs, Findings, Source-/Runtimeprovenienz und
  Rohhashes. Payloads/Prefixes/Journale/WALs/Clocks lokal, keine Secrets/Inspect/
  Env-Dumps. Kein erfolgreich validiertes Provider-vs-Egress-Signature behauptet.

**Weiter:** Korrigierten Harness unter frischem prospektiv begrenztem Plan live
validieren; alten Fehlversuch erhalten. Danach qualifiziertes Signature für N5-
Triangulation nutzen. Historischer Initiator, volle N5-/M3-Abnahme und sonstige
Gates offen; PR #2 Draft, Intrinsic/M4 unberührt.

## Fortsetzung 2026-11-06: Korrigierter CONTROL-Faultharness live validiert

- Frischer vorab commiteter Ein-Ausführungsplan cd54446, N0/45 s/Seed 1701,
  operator→robot CONTROL-only tc-Drop. Alter FAILED-Versuch unverändert. 115
  Hosttests/Syntaxchecks bestanden; Sourcehashes und acht Runtimehashes zum
  vorher getesteten SDK-/ROS-Build vorher/nachher gleich. Keine Runtime-/Policy-/
  Timeout-/Dependencyänderung, keine frischen SDK-/ROS-/M2-Tests behauptet.
- Lokal .local/m3/20261106T213402911275Z. Filter installiert/validiert/entfernt,
  leeres Restore-Readback. Finaler Pre-Remove-Counter 303 Drops/39356 Bytes,
  kein garantierter Lifetimecounter. Garantiert aktives VM-Intervall 6,410313587 s,
  angefordert sechs Hostsekunden. Keine Epoch-Subtraktion/Exaktdauerbehauptung.
- Bekannte Signature beobachtet: operator gleiche Socketidentität, 43 verfügbare
  benachbarte Readpaare komplett im Intervall: DATA-sent +137 inkl.135 Retransmits,
  ACK-sent +159; Post-Filter-CONTROL out 0, Robot alter CONTROL in 0. Reverse alter
  CONTROL am Operator 159, SENSOR-Source je Hook 1046 plus262 Parity, nach Remove
  im Drei-Sekundenfenster CONTROL out je92. Countertypen/Zeitgrenzen verschieden,
  keine Summierung von Retransmits auf DATA/keine exakte Dropgleichheit.
- Robot LinkLoss 5,001006502 s nach letztem alten incoming CONTROL, dann Close
  ohne SessionError. Operator-Loss ca.1,195 ms später. Anders als historische
  ca.fünf Sekunden Endpoint-Close-Abstand; kein Beweis desselben N5-Initiators.
  Bekannte Filterursache dieses Experiments, keine Rückwärtsattribution.
- Acht bestätigte Erfolge/Effekte, Intent9 UNKNOWN/reconcile-required Revision0
  ohne gültiges Result, 14 Slots übersprungen. Immutable geschlossene Journale:
  neun Sender-/acht Receiverrecords, acht Erfolge/Hashes/Kontexte/Resultate passen;
  Receiverdeadline konservativ früher, nicht Gleichheit unterstellt. Für9 genau
  ein SDK-Handoff, Receiverrecord fehlt, Peer-NOT_FOUND und UNKNOWN nach Budget
  erhalten. Keine Nonexecution/Expiry/Replay-/Result-Erfindung. Harness PASSED
  erlaubt UNKNOWN und bedeutet keine Qualification-Abnahme.
- Providerlogs643/22/604, Commandtrace371/5/10 vollständig, zero Drops/Exhaustion.
  Max Readspan2,519750 ms/Startgap114,167500 ms beobachtet, keine Bounds. PCAP
  23862 Records/Filter je Endpoint zero Kerneldrops, Native23879/23882 zero
  Reserve-/Copyverluste bei separaten Populationen. Realtimefenster withheld.
  Source/Published/Observer11291/10258/10248, alle Conservationbalances0.
- Evidenz evidence/m3-control-egress-validation-2026-11-06/ mit neuem Plan,
  Originalmanifest/Logs/Result, unabhängiger Provider-vs-Egress-/Flowanalyse,
  Journalvergleich, Inventaren/Testlog/Rohhashes. Payloads/Prefixes/Journale/
  Clocks lokal; keine Secrets/Inspect-/Env-Dumps. Historische Fehlläufe unverändert.

**Weiter:** Validierte Unterscheidung in separatem prospektiv begrenztem N5-
Diagnoseplan mit Providerdaten/Flowisolierung anwenden. Historischer Initiator,
UNKNOWNs, volle N5-/M3- und sonstige Gates offen. PR #2 Draft, Intrinsic/M4 unberührt.
